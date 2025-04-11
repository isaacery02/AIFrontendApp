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
        # The main window (self) will now hold only the PanedWindow in a single cell
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Create the PanedWindow ---
        # This standard Tkinter widget will manage the two main sections
        self.paned_window = tk.PanedWindow(
            self,                       # Parent is the main window
            orient=tk.HORIZONTAL,       # Divide horizontally (left/right panes)
            sashrelief=tk.RAISED,       # Style for the draggable divider
            sashwidth=6,                # Thickness of the divider (adjust as needed)
            bg="gray25"                 # Background color for the sash area (adjust to match theme)
            # showhandle=True           # Optional: adds visual handles to the sash
        )
        # Place the PanedWindow using grid, making it fill the main window
        self.paned_window.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # --- Pane 1: History Section ---
        # Create a standard tk Frame as container first
        self.history_container = tk.Frame(self.paned_window)
        # Then place CustomTkinter widget inside this container
        self.history_frame = customtkinter.CTkScrollableFrame(
            self.history_container,     # Parent is the container Frame
            label_text="History",
            width=180
        )
        # Configure the history frame grid
        self.history_frame.grid_columnconfigure(0, weight=1) # Allow buttons inside to expand width
        # Pack the history frame into its container (fill the container)
        self.history_frame.pack(fill="both", expand=True)
        # Add the container to the PanedWindow
        self.paned_window.add(self.history_container, stretch="never")

        # --- Pane 2: Main Content Area ---
        # Create a standard tk Frame as container first
        self.main_content_container = tk.Frame(self.paned_window)
        # Then place CustomTkinter widget inside this container
        self.main_content_frame = customtkinter.CTkFrame(
            self.main_content_container, # Parent is the container Frame
            fg_color="transparent"      # Make its background transparent
        )
        # Pack the main content frame into its container
        self.main_content_frame.pack(fill="both", expand=True)
        # Add the container to the PanedWindow
        self.paned_window.add(self.main_content_container, stretch="always")

        # --- Configure Grid Layout *INSIDE* main_content_frame ---
        # This frame now manages the layout for the input/output/buttons/status
        self.main_content_frame.grid_columnconfigure(0, weight=1) # Single column
        self.main_content_frame.grid_rowconfigure(0, weight=1) # Input row weight
        self.main_content_frame.grid_rowconfigure(1, weight=3) # Output row weight (larger)
        self.main_content_frame.grid_rowconfigure(2, weight=0) # Button frame row weight
        self.main_content_frame.grid_rowconfigure(3, weight=0) # Status label row weight

        # --- Widgets INSIDE main_content_frame ---
        # IMPORTANT: Change the parent/master of these widgets to self.main_content_frame
        # And set column to 0

        # Input Textbox
        self.input_textbox = customtkinter.CTkTextbox(self.main_content_frame, height=100)
        self.input_textbox.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")
        self.input_textbox.insert("0.0", "Enter your text here...")
        self.input_textbox.bind("<Control-Return>", self.handle_ctrl_enter)

        # Output Textbox
        self.output_textbox = customtkinter.CTkTextbox(self.main_content_frame, state="disabled")
        self.output_textbox.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        # Button Frame (Parent is main_content_frame)
        self.button_frame = customtkinter.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.button_frame.grid(row=2, column=0, padx=10, pady=(5,0), sticky="ew")
        # Configure columns inside button_frame (no change here)
        self.button_frame.grid_columnconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure(1, weight=1)
        self.button_frame.grid_rowconfigure(0, weight=0)
        self.button_frame.grid_rowconfigure(1, weight=0)

        # Buttons (Parent is button_frame - no change)
        self.submit_button = customtkinter.CTkButton(self.button_frame, text="Generate & Speak", command=self.start_processing_thread)
        self.submit_button.grid(row=0, column=0, padx=(0,5), pady=(5,2), sticky="ew")
        self.stop_button = customtkinter.CTkButton(self.button_frame, text="Stop Playback", command=self.stop_playback, state="disabled", fg_color="firebrick", hover_color="darkred")
        self.stop_button.grid(row=0, column=1, padx=(5,0), pady=(5,2), sticky="ew")

        # TTS Checkbox (Parent is button_frame - no change)
        self.tts_enabled = True
        self.tts_checkbox = customtkinter.CTkCheckBox(self.button_frame, text="Enable Speech Output", command=self.toggle_tts)
        self.tts_checkbox.grid(row=1, column=0, columnspan=2, padx=5, pady=(2,5), sticky="w")
        self.tts_checkbox.select()

        # Status Label (Parent is main_content_frame)
        self.status_label = customtkinter.CTkLabel(self.main_content_frame, text="Status: Ready", anchor="w")
        self.status_label.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")

        # --- Setup for processing (Reference config module) ---
        self.responses_dir = config.RESPONSES_DIR
        self.max_recordings = config.MAX_RECORDINGS
        self.processing_thread = None
        self.is_playing = False
        self.history_file = config.HISTORY_FILE

        # --- Load History & Update Display ---
        self.load_history() # Make sure this method exists or call manager directly
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
        """Runs API calls, cleanup, and playback in a background thread.
           Displays text response ASAP, then generates and plays audio if enabled."""
        audio_path_str = None
        generated_text = None
        audio_generated = False # Flag specific to audio generation success
        client = None
        try:
            # --- Step 1: Initialize Client ---
            client = OpenAI()
            if not client.api_key:
                 raise ValueError("OpenAI API key missing.")

            # --- Step 2: Get Text Response ---
            self.update_status("Generating AI response...")
            generated_text = api_handler.get_chat_response(client, prompt, config.DEFAULT_CHAT_MODEL)
            self.after(0, lambda: self.update_output_textbox(generated_text))

            # --- Step 3: Add to History (if text is valid) ---
            if generated_text and not generated_text.startswith(("(No text response", "Error:")):
                 self.history.insert(0, (prompt, generated_text))
                 self.after(0, self.update_history_display)
                 # Update status differently depending on TTS setting
                 status_msg = "Response received. Generating audio..." if self.tts_enabled else "Response received (Speech disabled)."
                 self.update_status(status_msg)
            else:
                 self.update_status("Failed to get valid text response.")
                 return

            # --- Steps 4-7: TTS, Playback, Cleanup (ONLY IF ENABLED) ---
            if self.tts_enabled:
                # --- Step 4: Generate Speech (TTS) ---
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = config.RESPONSES_DIR / f"response_{timestamp}.mp3"
                try:
                    api_handler.generate_speech(client, generated_text, output_filename, config.DEFAULT_TTS_MODEL, config.DEFAULT_TTS_VOICE)
                    audio_path_str = str(output_filename)
                    audio_generated = True
                except (ConnectionError, RuntimeError, Exception) as tts_error:
                     print(f"Error during TTS generation: {tts_error}")
                     self.update_status(f"Error generating audio: {tts_error}")
                     # audio_generated remains False

                # --- Step 5: Play Audio (if TTS was successful) ---
                if audio_generated:
                    if self.player.load(audio_path_str):
                        self.is_playing = True
                        self.set_stop_button_state(enabled=True) # Enable Stop button
                        self.update_status("Playing response...")
                        self.player.play()

                        while self.player.is_busy() and self.is_playing:
                            time.sleep(0.1)

                        # Playback finished or stopped
                        playback_naturally_finished = False
                        if self.is_playing: # Finished naturally
                            print("Playback finished naturally.")
                            self.update_status("Playback finished.")
                            self.is_playing = False
                            playback_naturally_finished = True

                        # Ensure stopped and unloaded
                        self.player.stop()
                        self.player.unload()

                    else: # Player failed to load
                         self.update_status("Error loading audio file for playback.")
                         self.is_playing = False

                    # Always ensure stop button is disabled after playback attempt
                    self.set_stop_button_state(enabled=False)

                    # --- Step 6: Cleanup ---
                    file_utils.cleanup_old_recordings(config.RESPONSES_DIR, config.MAX_RECORDINGS)

                    # --- Step 7: Update Final Status ---
                    if playback_naturally_finished:
                         self.update_status("Ready")
                    # If stopped/error, status already updated

                else: # Audio generation failed
                     self.update_status("Ready (audio generation failed).")
            else:
                # --- TTS was disabled ---
                print("TTS is disabled, skipping audio generation and playback.")
                # Status already set after text generation
                # We just need to ensure the UI gets enabled eventually.
                self.update_status("Ready (Speech disabled).")


        except (ValueError, ConnectionError, RuntimeError, Exception) as e:
             error_msg_thread = f"Error: {e}"
             print(error_msg_thread)
             final_text = generated_text or f"Error: {e}"
             self.after(0, lambda: self.update_output_textbox(final_text))
             self.update_status(f"Error: {e}")
             self.is_playing = False

        finally:
            # --- Step 8: Always Re-enable UI ---
            self.after(0, lambda: self.set_ui_state(processing=False))
            if self.is_playing: self.is_playing = False
            self.set_stop_button_state(enabled=False) # Ensure stop is disabled


    # --- Other methods like handle_ctrl_enter, load_history_item, stop_playback, on_closing remain the same ---
    # Make sure load_history exists (or that you directly use history_manager.load_history in __init__)
    def load_history(self): # Example if you kept this wrapper method
         self.history = load_history(config.HISTORY_FILE)

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
