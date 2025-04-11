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
import theme_manager

class ChatApp(customtkinter.CTk):
    def __init__(self, player: AudioPlayer):
        super().__init__()

        # --- Set Appearance Mode ONCE at startup ---
        # Assuming this should be here from previous steps
        customtkinter.set_appearance_mode("System")
        # ------------------------------------------

        self.player = player # Assign only ONCE
        self.title("AI Chat & Speech")
        self.geometry("850x550")

        customtkinter.set_default_color_theme("blue")

        # --- Add threading event for shutdown signalling ---
        self._is_shutting_down = threading.Event()
        # --- Add instance var for settings window ---
        self.settings_window = None
        # --- Add instance var for storing loaded API key for display ---
        self.current_api_key_display = ""
        # --- Add instance var for selected history timestamp ---
        self.selected_history_timestamp = None # Initialize here

        # Configure main window grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create PanedWindow
        self.paned_window = tk.PanedWindow(
            self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED,
            sashwidth=6, bg="gray25" # Keep colored sash for visibility for now
        )
        self.paned_window.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # --- Pane 1: History Section ---
        self.history_container = tk.Frame(self.paned_window) # REMOVED bg=...
        self.paned_window.add(self.history_container, stretch="never", width=180)
        self.history_container.grid_rowconfigure(0, weight=0) # Title Label
        self.history_container.grid_rowconfigure(1, weight=1) # Scrollable Frame
        self.history_container.grid_columnconfigure(0, weight=1)

        self.history_title_label = customtkinter.CTkLabel(
            master=self.history_container, text="History",
            font=customtkinter.CTkFont(weight="bold")
        )
        self.history_title_label.grid(row=0, column=0, padx=10, pady=(5, 5), sticky="ew")

        self.history_frame = customtkinter.CTkScrollableFrame(
            master=self.history_container, fg_color="transparent"
        )
        self.history_frame.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="nsew")
        self.history_frame.grid_columnconfigure(0, weight=1)

        # --- Pane 2: Main Content Area ---
        self.main_content_container = tk.Frame(self.paned_window) # REMOVED bg=...
        self.main_content_frame = customtkinter.CTkFrame(
            self.main_content_container, fg_color="transparent"
        )
        self.main_content_frame.pack(fill="both", expand=True)
        self.paned_window.add(self.main_content_container, stretch="always")

        # --- Configure Grid Layout *INSIDE* main_content_frame ---
        # Correct row configuration: 0=Input, 1=Output, 2=ButtonFrame, 3=Status
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=1) # Input row
        self.main_content_frame.grid_rowconfigure(1, weight=3) # Output row
        self.main_content_frame.grid_rowconfigure(2, weight=0) # Button frame row
        self.main_content_frame.grid_rowconfigure(3, weight=0) # Status label row

        # --- REMOVE Speak Input Checkbox from here ---

        # --- Widgets INSIDE main_content_frame ---
        # Correct row numbers

        # Input Textbox (Row 0)
        self.input_textbox = customtkinter.CTkTextbox(self.main_content_frame, height=100)
        self.input_textbox.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")
        self.input_textbox.insert("0.0", "Enter your text here...")
        self.input_textbox.bind("<Control-Return>", self.handle_ctrl_enter)

        # Output Textbox (Row 1)
        self.output_textbox = customtkinter.CTkTextbox(self.main_content_frame, state="disabled")
        self.output_textbox.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        # Button Frame (Row 2)
        self.button_frame = customtkinter.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.button_frame.grid(row=2, column=0, padx=10, pady=(5,0), sticky="ew")
        # Configure button_frame grid (3 rows needed)
        self.button_frame.grid_columnconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure(1, weight=1)
        self.button_frame.grid_rowconfigure(0, weight=0) # Gen/Stop
        self.button_frame.grid_rowconfigure(1, weight=0) # Play Hist/Settings
        self.button_frame.grid_rowconfigure(2, weight=0) # Checkboxes

        # Buttons (Row 0 and 1 - Correct placement)
        self.submit_button = customtkinter.CTkButton(self.button_frame, text="Generate & Speak", command=self.start_processing_thread)
        self.submit_button.grid(row=0, column=0, padx=(0,5), pady=(2,2), sticky="ew")
        self.stop_button = customtkinter.CTkButton(self.button_frame, text="Stop Playback", command=self.stop_playback, state="disabled", fg_color="firebrick", hover_color="darkred")
        self.stop_button.grid(row=0, column=1, padx=(5,0), pady=(2,2), sticky="ew")
        self.play_history_button = customtkinter.CTkButton(self.button_frame, text="Play Selected Audio", command=self.play_selected_history, state="disabled")
        self.play_history_button.grid(row=1, column=0, padx=(0,5), pady=(2,2), sticky="ew")
        self.settings_button = customtkinter.CTkButton(self.button_frame, text="Settings", command=self.open_settings_window)
        self.settings_button.grid(row=1, column=1, padx=(5,0), pady=(2,2), sticky="ew")

        # Checkboxes (Row 2 - Correct placement within button_frame)
        self.tts_enabled = True
        self.tts_checkbox = customtkinter.CTkCheckBox(self.button_frame, text="Enable Speech Output", command=self.toggle_tts)
        self.tts_checkbox.grid(row=2, column=0, padx=(5,10), pady=(5,5), sticky="w")
        self.tts_checkbox.select()

        self.speak_input_enabled = False # Define state variable
        self.speak_input_checkbox = customtkinter.CTkCheckBox( # Create it here
            self.button_frame, # Parent is button_frame
            text="Speak My Input",
            command=self.toggle_speak_input
        )
        self.speak_input_checkbox.grid(row=2, column=1, padx=(10,5), pady=(5,5), sticky="w") # Grid it here
        self.speak_input_checkbox.deselect() # Default OFF

        # Status Label (Row 3 - Correct placement, remove duplicate definition)
        self.status_label = customtkinter.CTkLabel(self.main_content_frame, text="Status: Ready", anchor="w")
        self.status_label.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")

        # --- Setup for processing --- (Unchanged)
        self.responses_dir = config.RESPONSES_DIR
        self.max_recordings = config.MAX_RECORDINGS
        self.processing_thread = None
        self.is_playing = False
        self.history_file = config.HISTORY_FILE
        self.user_settings_file = config.APP_BASE_DATA_DIR / "user_settings.json"

        # --- Load Persistent Data --- (Unchanged)
        self.load_user_settings()
        self.history = load_history(self.history_file)
        self.update_history_display()

        # --- Apply Initial Theme --- (Unchanged)
        # Use self.current_appearance_mode which was set by load_user_settings
        theme_manager.apply_theme(self, self.current_appearance_mode)

        # --- Set closing protocol --- (Unchanged)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_user_settings(self):
        """Loads settings from JSON and sets API key env var. Determines startup theme."""
        self.current_api_key_display = ""
        loaded_mode = "System" # Default appearance mode
        key_loaded_from_settings = False
        settings_file_path = config.APP_BASE_DATA_DIR / "user_settings.json"

        if settings_file_path.exists():
            print(f"DEBUG: Found settings file: {settings_file_path}")
            try:
                with open(settings_file_path, "r", encoding="utf-8") as f:
                    settings_data = json.load(f)
                print(f"DEBUG: Loaded settings data: {settings_data}")

                # Load API Key
                loaded_key = settings_data.get("openai_api_key")
                if loaded_key and isinstance(loaded_key, str) and loaded_key.startswith("sk-"):
                    os.environ['OPENAI_API_KEY'] = loaded_key
                    self.current_api_key_display = loaded_key
                    key_loaded_from_settings = True
                    print("DEBUG: Loaded API key from user_settings.json and set os.environ.")
                elif "openai_api_key" in settings_data:
                     print("DEBUG: Found 'openai_api_key' in settings but it's invalid or empty.")

                # Load Appearance Mode setting name
                loaded_mode_setting = settings_data.get("appearance_mode")
                if loaded_mode_setting in ["Light", "Dark", "System"]:
                    loaded_mode = loaded_mode_setting # Use saved setting name
                    print(f"DEBUG: Loaded appearance mode preference: '{loaded_mode}'")
                else:
                    print("DEBUG: Appearance mode setting not found/invalid, will use default 'System'.")

            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading user settings file {settings_file_path}: {e}")
                loaded_mode = "System" # Default on error
            except Exception as e:
                print(f"Unexpected error loading user settings: {e}")
                loaded_mode = "System" # Default on error
        else:
            print(f"DEBUG: Settings file not found: {settings_file_path}")

        # Fallback API Key Check
        if not key_loaded_from_settings:
             env_key = os.getenv('OPENAI_API_KEY')
             if env_key:
                  print("DEBUG: Using API key found in environment variable or .env file.")
                  self.current_api_key_display = env_key
             else:
                  print("WARN: OpenAI API key not found anywhere.")
                  self.current_api_key_display = ""

        # Store the determined mode - theme application happens at end of __init__
        self.current_appearance_mode = loaded_mode
        print(f"DEBUG: Startup mode determined as: {self.current_appearance_mode}")

    def open_settings_window(self):
        """Opens the settings window or focuses it if already open."""
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.focus()
            return

        self.settings_window = customtkinter.CTkToplevel(self)
        self.settings_window.title("Settings")
        self.settings_window.geometry("500x300") # Increased height for new controls
        self.settings_window.resizable(False, False)
        self.settings_window.transient(self)
        self.settings_window.grab_set()

        # Configure grid
        self.settings_window.grid_columnconfigure(1, weight=1)
        # Add row configs
        self.settings_window.grid_rowconfigure(0, weight=0) # API Key
        self.settings_window.grid_rowconfigure(1, weight=0) # Status Label
        self.settings_window.grid_rowconfigure(2, weight=0) # Appearance Label
        self.settings_window.grid_rowconfigure(3, weight=0) # Appearance Radio Buttons
        self.settings_window.grid_rowconfigure(4, weight=0) # Save/Close Buttons

        # --- API Key Section ---
        api_key_label = customtkinter.CTkLabel(self.settings_window, text="OpenAI API Key:")
        api_key_label.grid(row=0, column=0, padx=(20, 5), pady=(20, 5), sticky="w")
        self.settings_api_key_entry = customtkinter.CTkEntry(self.settings_window, width=350, show="*") # Store as instance var
        self.settings_api_key_entry.grid(row=0, column=1, padx=(0, 20), pady=(20, 5), sticky="ew")
        self.settings_api_key_entry.insert(0, self.current_api_key_display or "")

        # --- Status Label for Settings ---
        self.settings_status_label = customtkinter.CTkLabel(self.settings_window, text="", anchor="w") # Store as instance var
        self.settings_status_label.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")

        # --- Appearance Mode Section ---
        appearance_label = customtkinter.CTkLabel(self.settings_window, text="Appearance Mode:")
        appearance_label.grid(row=2, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="w")

        # Variable to hold the selected radio button state
        # Ensure self.current_appearance_mode is loaded before this window opens
        self.appearance_mode_var = customtkinter.StringVar(value=self.current_appearance_mode)

        # Frame to hold radio buttons horizontally
        radio_frame = customtkinter.CTkFrame(self.settings_window, fg_color="transparent")
        # Grid the frame into the settings window
        radio_frame.grid(row=3, column=0, columnspan=2, padx=15, pady=0, sticky="w")

        # Create radio buttons WITH radio_frame as the master directly
        radio_light = customtkinter.CTkRadioButton(
            master=radio_frame,
            text="Light", variable=self.appearance_mode_var,
            value="Light", command=self.change_appearance_mode
        )
        radio_light.grid(row=0, column=0, padx=5, pady=5, sticky="w") # Grid within radio_frame

        radio_dark = customtkinter.CTkRadioButton(
            master=radio_frame,
            text="Dark", variable=self.appearance_mode_var,
            value="Dark", command=self.change_appearance_mode
        )
        radio_dark.grid(row=0, column=1, padx=5, pady=5, sticky="w") # Grid within radio_frame

        radio_system = customtkinter.CTkRadioButton(
            master=radio_frame,
            text="System", variable=self.appearance_mode_var,
            value="System", command=self.change_appearance_mode
        )
        radio_system.grid(row=0, column=2, padx=5, pady=5, sticky="w") # Grid within radio_frame

        # --- Save/Close Buttons ---
        save_button = customtkinter.CTkButton(
            self.settings_window, text="Save Settings",
            command=self.save_settings # Command now saves both API key and appearance
        )
        save_button.grid(row=4, column=0, padx=(20, 5), pady=(20, 20), sticky="ew")

        close_button = customtkinter.CTkButton(
            self.settings_window, text="Close",
            command=self.on_settings_close # Use handler to reset variable
        )
        close_button.grid(row=4, column=1, padx=(5, 20), pady=(20, 20), sticky="ew")

        self.settings_window.protocol("WM_DELETE_WINDOW", self.on_settings_close)

    def on_settings_close(self):
        """Callback for when the settings window is closed."""
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.grab_release()
            self.settings_window.destroy()
        self.settings_window = None # Reset variable
        # Clean up variables associated with the settings window if needed
        if hasattr(self, 'appearance_mode_var'):
             del self.appearance_mode_var
        if hasattr(self, 'settings_api_key_entry'):
             del self.settings_api_key_entry
        if hasattr(self, 'settings_status_label'):
             del self.settings_status_label

    def save_settings(self):
        """Saves the API key and appearance mode from the settings window."""
        # ... (logic to get API key from self.settings_api_key_entry) ...
        new_key = self.settings_api_key_entry.get().strip()
        key_warning = ""
        if not new_key:
             new_key = None
        elif not new_key.startswith("sk-"):
             key_warning = "Warning: Key might be invalid. "

        # Get the *currently applied* mode
        selected_mode = self.current_appearance_mode

        settings_data = {}
        if new_key:
             settings_data["openai_api_key"] = new_key
        settings_data["appearance_mode"] = selected_mode # Save the mode

        try:
            # ... (logic to save settings_data to self.user_settings_file) ...
             settings_file_path = config.APP_BASE_DATA_DIR / "user_settings.json" # Use config path
             settings_file_path.parent.mkdir(parents=True, exist_ok=True)
             with open(settings_file_path, "w", encoding="utf-8") as f:
                 json.dump(settings_data, f, indent=4)

             if new_key:
                 os.environ['OPENAI_API_KEY'] = new_key
                 self.current_api_key_display = new_key
                 print("Saved new API key to user_settings.json and updated environment variable.")
             else:
                 print("API key cleared in user_settings.json.")
                 self.current_api_key_display = os.getenv('OPENAI_API_KEY', '')

             print(f"Saved appearance mode '{selected_mode}' to user_settings.json.")
             self.settings_status_label.configure(text=key_warning + "Settings Saved!", text_color="green")

        except Exception as e:
            print(f"Error saving user settings: {e}")
            self.settings_status_label.configure(text=f"Error saving settings: {e}", text_color="red")


    def on_settings_close(self):
        """Callback for when the settings window is closed."""
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.grab_release() # Release grab
            self.settings_window.destroy()
        self.settings_window = None # Reset variable

    def change_appearance_mode(self):
        """Updates the stored mode and applies the theme using theme_manager."""
        new_mode = self.appearance_mode_var.get()
        print(f"DEBUG: Appearance mode radio button changed to: {new_mode}")

        if new_mode in ["Light", "Dark", "System"]:
            # Store the new mode preference
            self.current_appearance_mode = new_mode
            # Apply the theme using the external manager
            theme_manager.apply_theme(self, new_mode)
        else:
             print(f"Error: Invalid appearance mode selected in UI: {new_mode}")

    # --- Ensure on_closing method exists from previous steps ---
    def on_closing(self):
        """Handles window closing event."""
        print("Closing application...")
        # --- Set shutdown flag FIRST ---
        self._is_shutting_down.set()
        # -------------------------------

        # Stop playback if active (player might check flag soon)
        if self.is_playing:
             print("Stopping active playback...")
             self.player.stop()
             self.is_playing = False # Also clear flag here

        # Optional: Wait briefly for threads to potentially notice the flag
        # time.sleep(0.2) # Small delay might help, but joining is better if needed

        # Save history
        print("Saving history...")
        save_history(self.history_file, self.history)

        # Quit player
        print("Quitting pygame mixer...")
        self.player.quit()

        # Destroy window (LAST)
        print("Destroying main window...")
        self.destroy()

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
        def _update():
            # Check if the widget still exists before configuring
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                self.status_label.configure(text=f"Status: {message}")
            else:
                print(f"DEBUG: Status label no longer exists, skipping update: {message}")

        # Ensure this runs in the main thread
        if threading.current_thread() is not threading.main_thread():
            self.after(0, _update)
        else:
            _update() # Run directly if already in main thread


    def update_output_textbox(self, text):
        """Safely updates the output textbox from any thread."""
        def _update():
             # Check if the widget still exists before configuring
            if hasattr(self, 'output_textbox') and self.output_textbox.winfo_exists():
                self.output_textbox.configure(state="normal")
                self.output_textbox.delete("0.0", "end")
                self.output_textbox.insert("0.0", text or "")
                self.output_textbox.configure(state="disabled")
            else:
                 print("DEBUG: Output textbox no longer exists, skipping update.")

        if threading.current_thread() is not threading.main_thread():
            self.after(0, _update)
        else:
            _update()

    def set_ui_state(self, processing: bool):
        """Safely enable/disable UI elements based on processing state."""
        def _update():
            submit_state = "disabled" if processing else "normal"
            input_state = "disabled" if processing else "normal"

            # Check each widget before configuring
            if hasattr(self, 'submit_button') and self.submit_button.winfo_exists():
                self.submit_button.configure(state=submit_state)
            if hasattr(self, 'input_textbox') and self.input_textbox.winfo_exists():
                self.input_textbox.configure(state=input_state)

        if threading.current_thread() is not threading.main_thread():
             self.after(0, _update)
        else:
             _update()


    def set_stop_button_state(self, enabled: bool):
        """Safely enable/disable the stop button."""
        def _update():
            state = "normal" if enabled else "disabled"
            # Check if the widget still exists
            if hasattr(self, 'stop_button') and self.stop_button.winfo_exists():
                self.stop_button.configure(state=state)
            else:
                 print("DEBUG: Stop button no longer exists, skipping state change.")

        if threading.current_thread() is not threading.main_thread():
             self.after(0, _update)
        else:
             _update()


    # --- History Methods ---
    def update_history_display(self):
        """Clears and redraws the history frame, checking existence."""
        # Check if frame itself exists first
        if not hasattr(self, 'history_frame') or not self.history_frame.winfo_exists():
             print("DEBUG: History frame no longer exists, skipping display update.")
             return

        for widget in self.history_frame.winfo_children():
            widget.destroy()

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
        """Wrapper executed in thread: plays audio, then safely re-enables history button."""
        playback_completed_naturally = False
        try:
            playback_completed_naturally = self._play_audio_blocking(audio_path_str, status_playing)
        finally:
            # Check if button still exists before configuring
            def _safe_reenable_play_button():
                 if not hasattr(self, 'play_history_button') or not self.play_history_button.winfo_exists():
                      print("DEBUG: Play history button no longer exists, skipping re-enable.")
                      return

                 current_selected_ts = self.selected_history_timestamp
                 new_state = "disabled" # Default to disabled
                 if current_selected_ts and (config.RESPONSES_DIR / f"response_{current_selected_ts}.mp3").exists():
                      new_state = "normal"
                 self.play_history_button.configure(state=new_state)

            self.after(0, _safe_reenable_play_button)

            # Set final status if needed (update_status already has checks)
            current_status = self.status_label.cget("text") # Check status from main thread? Risky.
            # Better to just call update_status which handles checks safely
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

    def _safe_reenable_ui_after_thread(self):
         """Safely re-enables UI after background thread finishes, respecting shutdown flag."""
         if self._is_shutting_down.is_set(): return # Don't re-enable if closing
         # Check if main window still exists just in case
         if not self.winfo_exists(): return

         print("DEBUG: Background thread finished cleanly. Re-enabling UI.")
         self.set_ui_state(processing=False) # Calls safe method
         if self.is_playing: self.is_playing = False # Reset flag if needed
         self.set_stop_button_state(enabled=False) # Calls safe method
    
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
