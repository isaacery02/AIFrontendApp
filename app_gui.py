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

        # --- REMOVE Speak Input Checkbox FROM HERE ---
        # self.speak_input_enabled = False # Default OFF <-- MOVE this definition down
        # self.speak_input_checkbox = customtkinter.CTkCheckBox(...) <-- MOVE creation/gridding
        # self.speak_input_checkbox.grid(row=0, ...) <-- DELETE this grid call
        # self.speak_input_checkbox.deselect() <-- MOVE this call down

        # --- Widgets INSIDE main_content_frame ---
        # Adjust row numbers back

        # Input Textbox (Back to row 0)
        self.input_textbox = customtkinter.CTkTextbox(self.main_content_frame, height=100)
        self.input_textbox.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")
        self.input_textbox.insert("0.0", "Enter your text here...")
        self.input_textbox.bind("<Control-Return>", self.handle_ctrl_enter)

        # Output Textbox (Back to row 1)
        self.output_textbox = customtkinter.CTkTextbox(self.main_content_frame, state="disabled")
        self.output_textbox.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        # Button Frame (Back to row 2)
        self.button_frame = customtkinter.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.button_frame.grid(row=2, column=0, padx=10, pady=(5,0), sticky="ew")
        # Configure columns/rows inside button_frame (Unchanged)
        self.button_frame.grid_columnconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure(1, weight=1)
        self.button_frame.grid_rowconfigure(0, weight=0)
        self.button_frame.grid_rowconfigure(1, weight=0)

        # Buttons (Row 0 of button_frame - Unchanged)
        self.submit_button = customtkinter.CTkButton(self.button_frame, text="Generate & Speak", command=self.start_processing_thread)
        self.submit_button.grid(row=0, column=0, padx=(0,5), pady=(5,2), sticky="ew")
        self.stop_button = customtkinter.CTkButton(self.button_frame, text="Stop Playback", command=self.stop_playback, state="disabled", fg_color="firebrick", hover_color="darkred")
        self.stop_button.grid(row=0, column=1, padx=(5,0), pady=(5,2), sticky="ew")

        # --- Checkboxes (Row 1 of button_frame) ---

        # Enable Speech Output Checkbox (Row 1, Column 0)
        self.tts_enabled = True
        self.tts_checkbox = customtkinter.CTkCheckBox(
            self.button_frame, # Parent is button_frame
            text="Enable Speech Output",
            command=self.toggle_tts
        )
        # Update grid call: remove columnspan, add padx, ensure row/col correct
        self.tts_checkbox.grid(row=1, column=0, padx=(5,10), pady=(2,5), sticky="w") # Col 0
        self.tts_checkbox.select() # Default ON

        # Speak My Input Checkbox (Row 1, Column 1) <-- MOVED HERE
        self.speak_input_enabled = False # Define state variable
        self.speak_input_checkbox = customtkinter.CTkCheckBox(
            self.button_frame, # Parent is button_frame
            text="Speak My Input",
            command=self.toggle_speak_input
        )
        # Grid it in the next column
        self.speak_input_checkbox.grid(row=1, column=1, padx=(10,5), pady=(2,5), sticky="w") # Col 1
        self.speak_input_checkbox.deselect() # Default OFF
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
             if isinstance(item, (list, tuple)) and len(item) == 2:
                 prompt, response = item
                 display_prompt = (prompt[:35] + '...') if len(prompt) > 38 else prompt
                 history_button = customtkinter.CTkButton(
                     self.history_frame, text=display_prompt.replace("\n", " "), anchor="w",
                     command=lambda p=prompt, r=response: self.load_history_item(p, r)
                 )
                 history_button.grid(row=i, column=0, padx=5, pady=3, sticky="ew")
             else:
                 print(f"Warning: Skipping invalid history item at index {i}: {item}")

    def load_history_item(self, prompt, response):
        """Loads selected history item back into input/output fields."""
        if self.processing_thread and self.processing_thread.is_alive():
             self.update_status("Error: Cannot load history while processing.")
             return
        self.input_textbox.configure(state="normal")
        self.input_textbox.delete("0.0", "end")
        self.input_textbox.insert("0.0", prompt)
        self.output_textbox.configure(state="normal")
        self.output_textbox.delete("0.0", "end")
        self.output_textbox.insert("0.0", response)
        self.output_textbox.configure(state="disabled")
        self.update_status("Loaded item from history.")

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
        If 'Speak Input' is checked, only generates TTS for the prompt and plays it.
        Otherwise, gets AI response, displays it, adds to history, and optionally plays response TTS.
        """
        client = None
        generated_text = None # To ensure it's defined for finally block's potential use in error reporting
        playback_completed_naturally = True # Assume true unless stopped/error

        try:
            # --- Initialize Client ---
            # Needed for both input TTS and chat/response TTS
            client = OpenAI()
            if not client.api_key:
                raise ValueError("OpenAI API key missing.")

            # --- Path 1: Speak Input ONLY ---
            if self.speak_input_enabled:
                self.update_status("Generating speech for input...")
                prompt_audio_path = None
                try:
                    temp_prompt_audio_path = config.APP_BASE_DATA_DIR / "prompt_audio.mp3"
                    api_handler.generate_speech(
                        client, prompt, temp_prompt_audio_path,
                        config.DEFAULT_TTS_MODEL, config.DEFAULT_TTS_VOICE
                    )
                    prompt_audio_path = str(temp_prompt_audio_path)
                except (ConnectionError, RuntimeError, Exception) as prompt_tts_error:
                    print(f"Error generating speech for prompt: {prompt_tts_error}")
                    self.update_status(f"Error generating prompt audio: {prompt_tts_error}")
                    # Fall through to finally block to re-enable UI

                if prompt_audio_path:
                    # Play the prompt audio blockingly
                    playback_completed_naturally = self._play_audio_blocking(
                        prompt_audio_path, status_playing="Speaking input..."
                    )
                    try: # Clean up temp file
                        Path(prompt_audio_path).unlink(missing_ok=True)
                    except OSError as e:
                        print(f"Error deleting temp prompt audio: {e}")

                    # Update status based on playback outcome
                    if playback_completed_naturally:
                        self.update_status("Ready (Input spoken).")
                    else: # Playback was stopped
                        self.update_status("Ready (Input speech stopped).")
                else:
                     # TTS failed, update status
                     self.update_status("Ready (Input audio generation failed).")

                # IMPORTANT: Skip the rest of the AI interaction
                return # Exit the thread function here

            # --- Path 2: Get AI Response and Optionally Speak Response ---
            else: # (self.speak_input_enabled is False)
                # --- Get Text Response ---
                self.update_status("Generating AI response...")
                generated_text = api_handler.get_chat_response(client, prompt, config.DEFAULT_CHAT_MODEL)
                self.after(0, lambda: self.update_output_textbox(generated_text)) # Schedule text update ASAP

                # --- Add to History (if text is valid) ---
                if generated_text and not generated_text.startswith(("(No text response", "Error:")):
                    self.history.insert(0, (prompt, generated_text))
                    self.after(0, self.update_history_display) # Schedule history update
                    status_msg = "Response received. Generating audio..." if self.tts_enabled else "Response received (Speech disabled)."
                    self.update_status(status_msg)
                else:
                    self.update_status("Failed to get valid text response.")
                    return # Exit thread

                # --- Generate and Play Response Speech (ONLY IF ENABLED) ---
                if self.tts_enabled:
                    response_audio_path = None
                    response_audio_generated = False
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_filename = config.RESPONSES_DIR / f"response_{timestamp}.mp3"
                    try:
                        api_handler.generate_speech(client, generated_text, output_filename, config.DEFAULT_TTS_MODEL, config.DEFAULT_TTS_VOICE)
                        response_audio_path = str(output_filename)
                        response_audio_generated = True
                    except (ConnectionError, RuntimeError, Exception) as response_tts_error:
                         print(f"Error during response TTS generation: {response_tts_error}")
                         self.update_status(f"Error generating response audio: {response_tts_error}")

                    if response_audio_generated:
                         playback_completed_naturally = self._play_audio_blocking(
                             response_audio_path, status_playing="Playing response..."
                         )
                         # Cleanup old response recordings
                         file_utils.cleanup_old_recordings(config.RESPONSES_DIR, config.MAX_RECORDINGS)
                         # Update final status
                         if playback_completed_naturally:
                              self.update_status("Ready")
                         # If stopped/error, status is already set

                    else: # Response audio generation failed
                         self.update_status("Ready (Response audio generation failed).")

                else: # Response TTS disabled
                    print("Response TTS is disabled.")
                    self.update_status("Ready (Speech disabled).")

        except (ValueError, ConnectionError, RuntimeError, Exception) as e:
             # Catch errors from Client Init, Chat API call or other unexpected issues
             error_msg_thread = f"Error: {e}"
             print(error_msg_thread)
             final_text = generated_text or f"Error: {e}" # Show text if available before error
             self.after(0, lambda: self.update_output_textbox(final_text))
             self.update_status(f"Error: {e}")
             self.is_playing = False # Ensure flag is reset

        finally:
            # --- Always Re-enable UI ---
            # This runs regardless of which path was taken or if errors occurred
            self.after(0, lambda: self.set_ui_state(processing=False))
            # Ensure stop button is disabled if thread ends unexpectedly or completes
            if self.is_playing: self.is_playing = False
            self.set_stop_button_state(enabled=False) # Schedule disable

    # --- Other methods like handle_ctrl_enter, load_history_item, stop_playback, on_closing remain the same ---
    # Make sure load_history exists (or that you directly use history_manager.load_history in __init__)
    def load_history(self): # Example if you kept this wrapper method
         self.history = load_history(config.HISTORY_FILE)

    def _play_audio_blocking(self, audio_path_str: str, status_playing: str = "Playing audio...") -> bool:
        """
        Loads and plays an audio file blockingly, managing the Stop button.
        Returns True if playback completed naturally, False otherwise (stopped or error).
        """
        if not audio_path_str or not self.player.initialized:
            return False

        natural_finish = False
        try:
            self.update_status("Loading audio...") # Direct update ok here? No, schedule.
            self.after(0, lambda: self.update_status("Loading audio..."))
            if not self.player.load(audio_path_str):
                raise RuntimeError(f"Failed to load audio file: {audio_path_str}")

            print(f"Playing: {audio_path_str}")
            self.is_playing = True
            self.set_stop_button_state(enabled=True) # Schedule enable
            self.update_status(status_playing)      # Schedule update

            self.player.play()

            # Wait for playback to finish or be stopped
            while self.player.is_busy() and self.is_playing:
                time.sleep(0.1)

            # --- Playback finished or stopped ---
            if self.is_playing: # Finished naturally if flag wasn't cleared by stop_playback
                print("Playback finished naturally.")
                self.update_status("Playback finished.") # Schedule update
                self.is_playing = False # Clear flag *after* checking
                natural_finish = True
            # If stopped by user, is_playing is already False, status set in stop_playback

        except Exception as e:
            error_msg = f"Error during playback: {e}"
            print(error_msg)
            self.update_status(error_msg) # Schedule update
            self.is_playing = False
        finally:
            # Ensure mixer is stopped and unloaded
            self.player.stop()
            self.player.unload()
            # Ensure stop button is disabled AFTER playback attempt ends
            self.set_stop_button_state(enabled=False) # Schedule disable

        return natural_finish

    def _play_audio_blocking(self, audio_path_str: str, status_playing: str = "Playing audio...") -> bool:
        """
        Loads and plays an audio file blockingly, managing the Stop button.
        Returns True if playback completed naturally, False otherwise (stopped or error).
        """
        if not audio_path_str or not self.player.initialized:
            return False

        natural_finish = False
        try:
            self.update_status("Loading audio...") # Direct update ok here? No, schedule.
            self.after(0, lambda: self.update_status("Loading audio..."))
            if not self.player.load(audio_path_str):
                raise RuntimeError(f"Failed to load audio file: {audio_path_str}")

            print(f"Playing: {audio_path_str}")
            self.is_playing = True
            self.set_stop_button_state(enabled=True) # Schedule enable
            self.update_status(status_playing)      # Schedule update

            self.player.play()

            # Wait for playback to finish or be stopped
            while self.player.is_busy() and self.is_playing:
                time.sleep(0.1)

            # --- Playback finished or stopped ---
            if self.is_playing: # Finished naturally if flag wasn't cleared by stop_playback
                print("Playback finished naturally.")
                self.update_status("Playback finished.") # Schedule update
                self.is_playing = False # Clear flag *after* checking
                natural_finish = True
            # If stopped by user, is_playing is already False, status set in stop_playback

        except Exception as e:
            error_msg = f"Error during playback: {e}"
            print(error_msg)
            self.update_status(error_msg) # Schedule update
            self.is_playing = False
        finally:
            # Ensure mixer is stopped and unloaded
            self.player.stop()
            self.player.unload()
            # Ensure stop button is disabled AFTER playback attempt ends
            self.set_stop_button_state(enabled=False) # Schedule disable

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
