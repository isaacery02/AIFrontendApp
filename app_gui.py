# app_gui.py
import customtkinter
import threading
import time
from pathlib import Path
from openai import OpenAI, OpenAIError
import os
import json
from datetime import datetime
import tkinter as tk

# Import from modules
import config
import api_handler
from audio_player import AudioPlayer
from history_manager import load_history, save_history
from file_utils import cleanup_old_recordings
import file_utils

class ChatApp(customtkinter.CTk):
    def __init__(self, player: AudioPlayer): # Pass player instance
        super().__init__()

        self.player = player
        self.title("AI Chat & Speech")
        self.geometry("850x550") # Adjust size as needed

        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")

        # --- Configure main window's grid for the PanedWindow ---
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Create the PanedWindow ---
        self.paned_window = tk.PanedWindow(
            self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED,
            sashwidth=6, bg="gray25"
        )
        self.paned_window.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # --- Pane 1: History Section ---
        # Using intermediate tk.Frame container
        self.history_container = tk.Frame(self.paned_window)
        self.history_frame = customtkinter.CTkScrollableFrame(
            self.history_container, label_text="History", width=180
        )
        self.history_frame.grid_columnconfigure(0, weight=1)
        self.history_frame.pack(fill="both", expand=True)
        self.paned_window.add(self.history_container, stretch="never")

        # --- Pane 2: Main Content Area ---
        # Using intermediate tk.Frame container
        self.main_content_container = tk.Frame(self.paned_window)
        self.main_content_frame = customtkinter.CTkFrame(
            self.main_content_container, fg_color="transparent"
        )
        self.main_content_frame.pack(fill="both", expand=True)
        self.paned_window.add(self.main_content_container, stretch="always")

        # --- Configure Grid Layout *INSIDE* main_content_frame ---
        self.main_content_frame.grid_columnconfigure(0, weight=1) # Single column
        # Remove row 0 config for checkbox - rows are now: 0=Input, 1=Output, 2=ButtonFrame, 3=Status
        # self.main_content_frame.grid_rowconfigure(0, weight=0) # Speak Input Checkbox row <--- REMOVE
        self.main_content_frame.grid_rowconfigure(0, weight=1) # Input row weight (was 1)
        self.main_content_frame.grid_rowconfigure(1, weight=3) # Output row weight (was 2, larger)
        self.main_content_frame.grid_rowconfigure(2, weight=0) # Button frame row weight (was 3)
        self.main_content_frame.grid_rowconfigure(3, weight=0) # Status label row weight (was 4)

        # Input Textbox (Back to row 0)
        self.input_textbox = customtkinter.CTkTextbox(self.main_content_frame, height=100)
        self.input_textbox.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")
        self.input_textbox.insert("0.0", "Enter your text here...")
        self.input_textbox.bind("<Control-Return>", self.handle_ctrl_enter)

        # Output Textbox (Back to row 1)
        self.output_textbox = customtkinter.CTkTextbox(self.main_content_frame, state="disabled")
        self.output_textbox.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        # Button Frame (Parent is main_content_frame)
        self.button_frame = customtkinter.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.button_frame.grid(row=2, column=0, padx=10, pady=(5,0), sticky="ew")
        # Configure 2 columns, 3 rows (Gen/Stop, PlayHist/Empty, Checkboxes)
        self.button_frame.grid_columnconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure(1, weight=1)
        self.button_frame.grid_rowconfigure(0, weight=0) # Gen/Stop Buttons
        self.button_frame.grid_rowconfigure(1, weight=0) # Play History Button
        self.button_frame.grid_rowconfigure(2, weight=0) # Checkboxes

        # Generate / Stop Buttons (Row 0)
        self.submit_button = customtkinter.CTkButton(self.button_frame, text="Generate & Speak", command=self.start_processing_thread)
        self.submit_button.grid(row=0, column=0, padx=(0,5), pady=(5,2), sticky="ew")
        self.stop_button = customtkinter.CTkButton(self.button_frame, text="Stop Playback", command=self.stop_playback, state="disabled", fg_color="firebrick", hover_color="darkred")
        self.stop_button.grid(row=0, column=1, padx=(5,0), pady=(5,2), sticky="ew")

        # --- Add Play History Button (Row 1, Col 0) ---
        self.play_history_button = customtkinter.CTkButton(
            self.button_frame,
            text="Play Selected Audio",
            command=self.play_selected_history,
            state="disabled" # Initially disabled
        )
        self.play_history_button.grid(row=1, column=0, columnspan=2, padx=5, pady=(2,2), sticky="ew")
        # ---------------------------------------------

        # --- Checkboxes (Row 2) ---
        self.tts_enabled = True
        self.tts_checkbox = customtkinter.CTkCheckBox(self.button_frame, text="Enable Speech Output", command=self.toggle_tts)
        self.tts_checkbox.grid(row=2, column=0, padx=(5,10), pady=(2,5), sticky="w") # Row 2, Col 0
        self.tts_checkbox.select()

        self.speak_input_enabled = False
        self.speak_input_checkbox = customtkinter.CTkCheckBox(self.button_frame, text="Speak My Input", command=self.toggle_speak_input)
        self.speak_input_checkbox.grid(row=2, column=1, padx=(10,5), pady=(2,5), sticky="w") # Row 2, Col 1
        self.speak_input_checkbox.deselect()
        # ----------------------------------------

        # Status Label (Back to row 3 of main_content_frame)
        self.status_label = customtkinter.CTkLabel(self.main_content_frame, text="Status: Ready", anchor="w")
        self.status_label.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew") # Was row 4

        # --- Setup for processing ---
        self.responses_dir = config.RESPONSES_DIR
        self.max_recordings = config.MAX_RECORDINGS
        self.processing_thread = None
        self.is_playing = False
        self.history_file = config.HISTORY_FILE

        # --- Load History & Update Display ---
        self.load_history()
        self.update_history_display()

        # --- Set closing protocol ---
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --- Make sure load_history method exists or was replaced by direct call ---
    def load_history(self): # Example if you have this wrapper method
         self.history = load_history(self.history_file) # Uses history_manager function

    def handle_ctrl_enter(self, event):
        """Handles the Ctrl+Enter keyboard shortcut in the input textbox."""
        print("Ctrl+Enter detected, triggering generation...") # Optional debug print
        self.start_processing_thread() # Call the same function as the button
        return "break" # Prevents the default Enter key action (newline)
    
    def toggle_tts(self):
        """Updates the TTS enabled state based on the checkbox."""
        checkbox_value = self.tts_checkbox.get() # Returns 1 if checked, 0 if not
        self.tts_enabled = bool(checkbox_value)
        status = "enabled" if self.tts_enabled else "disabled"
        print(f"Text-to-Speech is now {status}")
        # Optional: Update status bar or button text if desired
        self.update_status(f"Speech output {status}") # Example status update

    # --- GUI Update Methods ---
    def update_status(self, message):
        """Safely updates the status label from any thread."""
        # Ensure this runs in the main thread if called from background
        if threading.current_thread() is not threading.main_thread():
             # If called from background, schedule it
             self.after(0, lambda: self.status_label.configure(text=f"Status: {message}"))
        else:
             # If called from main thread, update directly
             self.status_label.configure(text=f"Status: {message}")


    def update_output_textbox(self, text):
        """Safely updates the output textbox from any thread."""
        def _update():
            self.output_textbox.configure(state="normal")
            self.output_textbox.delete("0.0", "end")
            self.output_textbox.insert("0.0", text or "")
            self.output_textbox.configure(state="disabled")

        if threading.current_thread() is not threading.main_thread():
            self.after(0, _update)
        else:
            _update()

    def set_ui_state(self, processing: bool):
        """Enable/disable UI elements based on processing state."""
        submit_state = "disabled" if processing else "normal"
        input_state = "disabled" if processing else "normal"

        self.submit_button.configure(state=submit_state)
        self.input_textbox.configure(state=input_state)

    def set_stop_button_state(self, enabled: bool):
        """Safely enable/disable the stop button."""
        state = "normal" if enabled else "disabled"
        if threading.current_thread() is not threading.main_thread():
             self.after(0, lambda: self.stop_button.configure(state=state))
        else:
             self.stop_button.configure(state=state)


    # --- History Methods ---
    def update_history_display(self):
        """Clears and redraws the history frame."""
        for widget in self.history_frame.winfo_children():
            widget.destroy()
        if not isinstance(self.history, list):
             print("Warning: History data is not a list. Resetting history.")
             self.history = []

        for i, item in enumerate(self.history):
             # Handle both old (2-element) and new (3-element) history formats
             if isinstance(item, (list, tuple)) and len(item) >= 2:
                 prompt = item[0]
                 response = item[1]
                 # Get timestamp if available, otherwise None
                 timestamp = item[2] if len(item) > 2 else None

                 display_prompt = (prompt[:35] + '...') if len(prompt) > 38 else prompt
                 history_button = customtkinter.CTkButton(
                     self.history_frame, text=display_prompt.replace("\n", " "), anchor="w",
                     # Pass all three items to the command lambda
                     command=lambda p=prompt, r=response, ts=timestamp: self.load_history_item(p, r, ts)
                 )
                 history_button.grid(row=i, column=0, padx=5, pady=3, sticky="ew")
             else:
                 print(f"Warning: Skipping invalid history item at index {i}: {item}")

    def load_history_item(self, prompt, response, timestamp): # Added timestamp parameter
        """Loads selected history item text and enables playback button if audio exists."""
        if self.processing_thread and self.processing_thread.is_alive():
             self.update_status("Error: Cannot load history while processing.")
             return

        # Load text
        self.input_textbox.configure(state="normal")
        self.input_textbox.delete("0.0", "end")
        self.input_textbox.insert("0.0", prompt)
        self.update_output_textbox(response) # Safely updates output box

        # Store timestamp and manage Play button state
        self.selected_history_timestamp = None # Reset first
        self.play_history_button.configure(state="disabled") # Disable by default

        if timestamp:
            # Construct potential audio path
            audio_path = config.RESPONSES_DIR / f"response_{timestamp}.mp3"
            if audio_path.exists():
                self.selected_history_timestamp = timestamp # Store valid timestamp
                self.play_history_button.configure(state="normal") # Enable button
                self.update_status("Loaded item. Audio available.")
            else:
                 print(f"Audio file not found for timestamp {timestamp}")
                 self.update_status("Loaded item. Audio file missing.")
        else:
             self.update_status("Loaded item. No audio recorded for this entry.")

    def play_selected_history(self):
        """Finds and plays the audio file associated with the selected history item."""
        if not self.selected_history_timestamp:
            self.update_status("Error: No history item with audio selected.")
            return
        if self.processing_thread and self.processing_thread.is_alive():
            self.update_status("Error: Cannot play history while processing.")
            return
        if self.is_playing:
             self.update_status("Error: Already playing audio.")
             return

        audio_path = config.RESPONSES_DIR / f"response_{self.selected_history_timestamp}.mp3"

        if not audio_path.exists():
            self.update_status(f"Error: Audio file not found: {audio_path.name}")
            self.play_history_button.configure(state="disabled") # Disable button again
            self.selected_history_timestamp = None # Clear selection
            return

        # Disable button while preparing/playing
        self.play_history_button.configure(state="disabled")
        # Start playback in a background thread
        self._start_playback_thread(str(audio_path), "Playing history audio...")

    def _start_playback_thread(self, audio_path_str: str, status_playing: str):
        """Starts a daemon thread to play audio using _play_audio_blocking."""
        # Disable main processing button while history plays? Optional but maybe safer.
        # self.set_ui_state(processing=True) # Example if you want to lock main generate button too

        playback_thread = threading.Thread(
            target=self._execute_playback_and_reenable, # Target a wrapper
            args=(audio_path_str, status_playing),
            daemon=True
        )
        playback_thread.start()

    def _execute_playback_and_reenable(self, audio_path_str: str, status_playing: str):
        """Wrapper executed in thread: plays audio, then re-enables history button if needed."""
        playback_completed_naturally = False
        try:
            playback_completed_naturally = self._play_audio_blocking(audio_path_str, status_playing)
        finally:
            # This block runs even if playback failed or was stopped
            # Re-enable the play history button only if the timestamp still matches
            # (prevents race condition if user selects another item while playing)
            current_selected_ts = self.selected_history_timestamp # Read volatile var once
            if current_selected_ts and (config.RESPONSES_DIR / f"response_{current_selected_ts}.mp3").exists():
                 self.after(0, lambda: self.play_history_button.configure(state="normal"))
            else: # File deleted or selection cleared while playing
                 self.after(0, lambda: self.play_history_button.configure(state="disabled"))

            # Re-enable main generate button if it was disabled
            # self.after(0, lambda: self.set_ui_state(processing=False))

            # Set final status if needed
            current_status = self.status_label.cget("text")
            if "Error" not in current_status and "stopped" not in current_status and "finished" not in current_status:
                self.after(100, lambda: self.update_status("Ready"))

    # --- Core Logic and Threading ---
    def start_processing_thread(self):
        """Handles button click: gets text and starts the background thread."""
        user_prompt = self.input_textbox.get("0.0", "end-1c").strip()
        if not user_prompt or user_prompt == "Enter your text here...":
            self.update_status("Error: Please enter some text.")
            return
        if self.processing_thread and self.processing_thread.is_alive():
            self.update_status("Error: Processing already in progress.")
            return

        self.set_ui_state(processing=True)
        self.update_status("Processing...")
        self.update_output_textbox("") # Clear previous output

        # Start background processing
        self.processing_thread = threading.Thread(target=self.process_request_in_background, args=(user_prompt,), daemon=True)
        self.processing_thread.start()

    def stop_playback(self):
        """Stops audio playback using the AudioPlayer."""
        if self.is_playing:
            print("Stop playback requested.")
            self.player.stop() # Use player method
            self.is_playing = False # Set flag immediately
            self.update_status("Playback stopped.") # Update status immediately
            # Disable button immediately as well
            self.set_stop_button_state(enabled=False)

    def process_request_in_background(self, prompt):
        """
        Handles background processing.
        If 'Speak Input' is checked, generates TTS for the prompt, plays it, AND saves it persistently.
        Otherwise, gets AI response, displays it, adds to history, and optionally plays response TTS.
        """
        client = None
        generated_text = None
        playback_completed_naturally = True
        timestamp_for_history = None # Define outside the conditional blocks

        try:
            # --- Initialize Client ---
            client = OpenAI()
            if not client.api_key:
                raise ValueError("OpenAI API key missing.")

            # --- Path 1: Speak Input AND Save Audio Persistently ---
            if self.speak_input_enabled:
                self.update_status("Generating speech for input...")
                prompt_audio_path_str = None
                audio_generated = False

                # --- Generate Timestamp and Filename ---
                # Use the same timestamp/naming convention as responses
                timestamp_for_history = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = config.RESPONSES_DIR / f"response_{timestamp_for_history}.mp3" # Save in Responses dir
                print(f"DEBUG: Input TTS - Target output file: {output_filename}")

                try: # --- Generate Speech (TTS) ---
                    api_handler.generate_speech(
                        client, prompt, output_filename, # Use persistent filename
                        config.DEFAULT_TTS_MODEL, config.DEFAULT_TTS_VOICE
                    )
                    prompt_audio_path_str = str(output_filename)
                    audio_generated = True
                    print(f"DEBUG: Input TTS - API call succeeded for {prompt_audio_path_str}")
                except (ConnectionError, RuntimeError, Exception) as prompt_tts_error:
                    print(f"DEBUG: Input TTS - ERROR during generation: {prompt_tts_error}")
                    self.update_status(f"Error generating prompt audio: {prompt_tts_error}")
                    timestamp_for_history = None # Don't save timestamp if TTS failed

                # --- Play Audio (if generated successfully) ---
                if audio_generated and prompt_audio_path_str:
                    print("DEBUG: Input TTS - Generation succeeded. Proceeding to play.")
                    playback_completed_naturally = self._play_audio_blocking(
                        prompt_audio_path_str, status_playing="Speaking input..."
                    )
                    print(f"DEBUG: Input TTS - Playback finished. Completed naturally: {playback_completed_naturally}")
                    # --- DO NOT DELETE THE FILE ANYMORE ---
                    # try: Path(prompt_audio_path_str).unlink(missing_ok=True) # REMOVED
                elif not audio_generated:
                    print("DEBUG: Input TTS - Generation failed.")
                    # Update status below

                # --- Add History Entry (Always, but timestamp depends on TTS success) ---
                print(f"DEBUG: Adding input-only history. Timestamp: {timestamp_for_history}")
                placeholder_response = "(Input Spoken - No AI Response)" # Updated placeholder
                self.history.insert(0, (prompt, placeholder_response, timestamp_for_history)) # Use actual timestamp (or None if TTS failed)
                self.after(0, self.update_history_display)

                # --- Final Status Update ---
                if not audio_generated:
                    final_status = "Ready (Input audio generation failed)."
                elif playback_completed_naturally:
                    final_status = "Ready (Input spoken)."
                else: # Playback stopped by user
                    final_status = "Ready (Input speech stopped)."
                self.update_status(final_status)

                # --- Skip the rest of the AI interaction ---
                print("DEBUG: Input TTS path finished. Returning from thread.")
                return # Exit the thread function here

            # --- Path 2: Get AI Response and Optionally Speak Response ---
            else: # (self.speak_input_enabled is False)
                # --- Get Text Response ---
                self.update_status("Generating AI response...")
                generated_text = api_handler.get_chat_response(client, prompt, config.DEFAULT_CHAT_MODEL)
                self.after(0, lambda: self.update_output_textbox(generated_text))

                # --- Add to History (if text is valid) ---
                if generated_text and not generated_text.startswith(("(No text response", "Error:")):
                    timestamp_for_history = None # Reset for this path
                    if self.tts_enabled:
                        timestamp_for_history = datetime.now().strftime("%Y%m%d_%H%M%S")

                    # Add prompt, response, and timestamp (or None) to history
                    print(f"DEBUG: Saving history item: (prompt='{prompt[:20]}...', response='{generated_text[:20]}...', timestamp='{timestamp_for_history}')")
                    self.history.insert(0, (prompt, generated_text, timestamp_for_history))
                    self.after(0, self.update_history_display)

                    status_msg = "Response received. Generating audio..." if self.tts_enabled else "Response received (Speech disabled)."
                    self.update_status(status_msg)
                else:
                    self.update_status("Failed to get valid text response.")
                    return # Exit thread

                # --- Generate/Play Response Speech (if enabled) ---
                if self.tts_enabled and timestamp_for_history:
                    output_filename = config.RESPONSES_DIR / f"response_{timestamp_for_history}.mp3"
                    response_audio_path = None
                    response_audio_generated = False
                    try: # Generate TTS
                        print(f"DEBUG: Response TTS - Attempting generation for file: {output_filename}")
                        api_handler.generate_speech(client, generated_text, output_filename, config.DEFAULT_TTS_MODEL, config.DEFAULT_TTS_VOICE)
                        response_audio_path = str(output_filename)
                        response_audio_generated = True
                        print(f"DEBUG: Response TTS - API call succeeded for {output_filename}")
                    except (ConnectionError, RuntimeError, Exception) as response_tts_error:
                        print(f"DEBUG: Response TTS - ERROR during generation: {response_tts_error}")
                        self.update_status(f"Error generating response audio: {response_tts_error}")

                    if response_audio_generated: # Play Audio
                        print("DEBUG: Response TTS - Generation succeeded. Proceeding to play.")
                        playback_completed_naturally = self._play_audio_blocking(
                             response_audio_path, status_playing="Playing response..."
                        )
                        print(f"DEBUG: Response TTS - Playback finished. Completed naturally: {playback_completed_naturally}")

                        # Cleanup old recordings
                        print("DEBUG: Response TTS - Initiating cleanup.")
                        file_utils.cleanup_old_recordings(config.RESPONSES_DIR, config.MAX_RECORDINGS)

                        # Update final status
                        if playback_completed_naturally:
                              self.update_status("Ready")
                        # If stopped/error, status already set
                    else: # Audio generation failed
                        print("DEBUG: Response TTS - Generation failed. Setting status.")
                        self.update_status("Ready (Response audio generation failed).")

                elif self.tts_enabled and not timestamp_for_history: # Should not happen
                    print("DEBUG: Warning - TTS enabled but no timestamp captured.")
                    self.update_status("Ready (Internal history timestamp error).")
                else: # TTS disabled
                    print("DEBUG: Response TTS is disabled.")
                    self.update_status("Ready (Speech disabled).")


        except (ValueError, ConnectionError, RuntimeError, Exception) as e:
             error_msg_thread = f"Error: {e}"
             print(error_msg_thread)
             final_text = generated_text or f"Error: {e}"
             self.after(0, lambda: self.update_output_textbox(final_text))
             self.update_status(f"Error: {e}")
             self.is_playing = False

        finally:
            # --- Always Re-enable UI ---
            print("DEBUG: Background thread finally block reached. Re-enabling UI.")
            self.after(0, lambda: self.set_ui_state(processing=False))
            if self.is_playing: self.is_playing = False
            self.set_stop_button_state(enabled=False) # Ensure stop is disabled

    # --- Other methods like handle_ctrl_enter, load_history_item, stop_playback, on_closing remain the same ---
    # Make sure load_history exists (or that you directly use history_manager.load_history in __init__)
    def load_history(self): # Example if you kept this wrapper method
         self.history = load_history(config.HISTORY_FILE)

    def _play_audio_blocking(self, audio_path_str: str, status_playing: str = "Playing audio...") -> bool:
        """
        Loads and plays an audio file blockingly, managing the Stop button.
        Returns True if playback completed naturally, False otherwise (stopped or error).
        """
        print(f"DEBUG: _play_audio_blocking started for path: {audio_path_str}") # <--- ADD DEBUG PRINT
        if not audio_path_str or not self.player.initialized:
            print(f"DEBUG: _play_audio_blocking returning early. Path: {audio_path_str}, Initialized: {self.player.initialized}") # <--- ADD DEBUG PRINT
            return False

        natural_finish = False
        try:
            print(f"DEBUG: _play_audio_blocking: Attempting to load {audio_path_str}") # <--- ADD DEBUG PRINT
            self.after(0, lambda: self.update_status("Loading audio..."))
            if not self.player.load(audio_path_str):
                print(f"DEBUG: _play_audio_blocking: FAILED to load {audio_path_str}") # <--- ADD DEBUG PRINT
                raise RuntimeError(f"Failed to load audio file: {audio_path_str}")
            print(f"DEBUG: _play_audio_blocking: Loaded successfully. Attempting to play.") # <--- ADD DEBUG PRINT

            self.is_playing = True
            self.set_stop_button_state(enabled=True) # Schedule enable
            self.update_status(status_playing)       # Schedule update

            self.player.play()
            print(f"DEBUG: _play_audio_blocking: play() called. Entering wait loop.") # <--- ADD DEBUG PRINT

            # Wait for playback to finish or be stopped
            while self.player.is_busy() and self.is_playing:
                # print("DEBUG: Waiting in playback loop...") # Uncomment this line for very verbose loop checking
                time.sleep(0.1)
            print(f"DEBUG: _play_audio_blocking: Exited wait loop. is_playing={self.is_playing}") # <--- ADD DEBUG PRINT

            # --- Playback finished or stopped ---
            if self.is_playing: # Finished naturally if flag wasn't cleared by stop_playback
                print("DEBUG: Playback finished naturally.") # <--- ADD DEBUG PRINT
                self.update_status("Playback finished.") # Schedule update
                self.is_playing = False # Clear flag *after* checking
                natural_finish = True
            # If stopped by user, is_playing is already False, status set in stop_playback

        except Exception as e:
            error_msg = f"DEBUG: _play_audio_blocking - Error during playback section: {e}" # <--- ADD DEBUG PRINT
            print(error_msg)
            self.update_status(f"Error during playback: {e}") # Schedule update
            self.is_playing = False
        finally:
            # Ensure mixer is stopped and unloaded
            print("DEBUG: _play_audio_blocking: finally block. Stopping/unloading player.") # <--- ADD DEBUG PRINT
            self.player.stop()
            self.player.unload()
            # Ensure stop button is disabled AFTER playback attempt ends
            print("DEBUG: _play_audio_blocking: finally block. Disabling stop button.") # <--- ADD DEBUG PRINT
            self.set_stop_button_state(enabled=False) # Schedule disable

        print(f"DEBUG: _play_audio_blocking finished. Returning: {natural_finish}") # <--- ADD DEBUG PRINT
        return natural_finish
    
    def toggle_speak_input(self):
        """Updates the speak input enabled state based on the checkbox."""
        checkbox_value = self.speak_input_checkbox.get() # 1 if checked, 0 if not
        self.speak_input_enabled = bool(checkbox_value)
        status = "enabled" if self.speak_input_enabled else "disabled"
        print(f"Speak Input is now {status}")
        # Optional: Update status bar if desired
        # self.update_status(f"Speak Input {status}")
    
    # --- Closing Method ---
    def on_closing(self):
        """Handles window closing event."""
        print("Closing application...")
        # Stop playback if active
        if self.is_playing:
             self.player.stop()
        # Save history
        save_history(config.HISTORY_FILE, self.history) # Use manager
        # Quit player
        self.player.quit() # Use player method
        # Destroy window
        self.destroy()
