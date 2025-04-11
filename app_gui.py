# app_gui.py
# Main application GUI class using CustomTkinter

import customtkinter
import threading
import time
from pathlib import Path
from openai import OpenAI, OpenAIError
import os
import json
from datetime import datetime
import tkinter as tk
import traceback # For more detailed error logging if needed

# Import from custom modules
import config
import api_handler # Contains get_chat_response, generate_speech, get_available_chat_models
from audio_player import AudioPlayer # Contains the Pygame playback logic
from history_manager import load_history, save_history # Handles JSON loading/saving
from file_utils import cleanup_old_recordings # Handles deleting old audio files
import theme_manager # Handles applying appearance modes


class ChatApp(customtkinter.CTk):
    """Main Application class."""

    def __init__(self, player: AudioPlayer): # Pass player instance
        super().__init__()

        # --- Initial Setup ---
        # Set Appearance Mode EARLY before creating complex widgets
        # load_user_settings will apply the actual saved/default mode later
        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")

        self.player = player # Store the audio player instance
        self.title("AI Chat & Speech")
        self.geometry("850x550") # Initial size

        # --- State Variables ---
        self._is_shutting_down = threading.Event() # For clean shutdown
        self.settings_window = None
        self.current_api_key_display = "" # Loaded API key for display
        self.selected_history_timestamp = None # Timestamp of history item clicked
        self.current_chat_model = config.DEFAULT_CHAT_MODEL # Loaded/saved chat model preference
        self.current_appearance_mode = "System" # Loaded/saved appearance mode preference
        self.tts_enabled = True # State for enabling response speech
        self.speak_input_enabled = False # State for speaking user input
        self.is_playing = False # Flag to track if audio is currently playing
        self.processing_thread = None # To hold reference to background thread

        # --- File Paths ---
        self.history_file = config.HISTORY_FILE # Path to history JSON
        self.user_settings_file = config.APP_BASE_DATA_DIR / "user_settings.json" # Path to settings JSON

        # --- Configure main window grid (holds the PanedWindow) ---
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Create PanedWindow for adjustable layout ---
        self.paned_window = tk.PanedWindow(
            self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED,
            sashwidth=6, bg="gray25" # Visible sash color
        )
        self.paned_window.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # --- Pane 1: History Section ---
        # Use intermediate tk.Frame container
        self.history_container = tk.Frame(self.paned_window)
        self.paned_window.add(self.history_container, stretch="never", width=180)
        # Configure grid inside container
        self.history_container.grid_rowconfigure(0, weight=0) # Title Label row
        self.history_container.grid_rowconfigure(1, weight=1) # Scrollable Frame row
        self.history_container.grid_columnconfigure(0, weight=1)

        # Separate History Title Label
        self.history_title_label = customtkinter.CTkLabel(
            master=self.history_container, text="History",
            font=customtkinter.CTkFont(weight="bold")
        )
        self.history_title_label.grid(row=0, column=0, padx=10, pady=(5, 5), sticky="ew")

        # Scrollable Frame for History items
        self.history_frame = customtkinter.CTkScrollableFrame(
            master=self.history_container, fg_color="transparent" # Transparent background
        )
        self.history_frame.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="nsew")
        self.history_frame.grid_columnconfigure(0, weight=1)

        # --- Pane 2: Main Content Area ---
        # Use intermediate tk.Frame container
        self.main_content_container = tk.Frame(self.paned_window)
        self.paned_window.add(self.main_content_container, stretch="always")

        # Main CTkFrame inside the container
        self.main_content_frame = customtkinter.CTkFrame(
            master=self.main_content_container, fg_color="transparent"
        )
        self.main_content_frame.pack(fill="both", expand=True) # Fill the tk container

        # --- Configure Grid Layout *INSIDE* main_content_frame ---
        self.main_content_frame.grid_columnconfigure(0, weight=1) # Single column
        self.main_content_frame.grid_rowconfigure(0, weight=1) # Input row weight
        self.main_content_frame.grid_rowconfigure(1, weight=3) # Output row weight (larger)
        self.main_content_frame.grid_rowconfigure(2, weight=0) # Button frame row weight
        self.main_content_frame.grid_rowconfigure(3, weight=0) # Status label row weight

        # --- Widgets INSIDE main_content_frame ---

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
        # Configure button_frame grid (2 cols, 3 rows)
        self.button_frame.grid_columnconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure(1, weight=1)
        self.button_frame.grid_rowconfigure(0, weight=0) # Gen/Stop
        self.button_frame.grid_rowconfigure(1, weight=0) # Play History/Settings
        self.button_frame.grid_rowconfigure(2, weight=0) # Checkboxes

        # Buttons (Rows 0, 1)
        self.submit_button = customtkinter.CTkButton(self.button_frame, text="Generate & Speak", command=self.start_processing_thread)
        self.submit_button.grid(row=0, column=0, padx=(0,5), pady=(2,2), sticky="ew")
        self.stop_button = customtkinter.CTkButton(self.button_frame, text="Stop Playback", command=self.stop_playback, state="disabled", fg_color="firebrick", hover_color="darkred")
        self.stop_button.grid(row=0, column=1, padx=(5,0), pady=(2,2), sticky="ew")
        self.play_history_button = customtkinter.CTkButton(self.button_frame, text="Play Selected Audio", command=self.play_selected_history, state="disabled")
        self.play_history_button.grid(row=1, column=0, padx=(0,5), pady=(2,2), sticky="ew") # Col 0
        self.settings_button = customtkinter.CTkButton(self.button_frame, text="Settings", command=self.open_settings_window)
        self.settings_button.grid(row=1, column=1, padx=(5,0), pady=(2,2), sticky="ew") # Col 1

        # Checkboxes (Row 2)
        self.tts_checkbox = customtkinter.CTkCheckBox(self.button_frame, text="Enable Speech Output", command=self.toggle_tts)
        self.tts_checkbox.grid(row=2, column=0, padx=(5,10), pady=(5,5), sticky="w")
        self.tts_checkbox.select() # Default ON

        self.speak_input_checkbox = customtkinter.CTkCheckBox(self.button_frame, text="Speak My Input", command=self.toggle_speak_input)
        self.speak_input_checkbox.grid(row=2, column=1, padx=(10,5), pady=(5,5), sticky="w")
        self.speak_input_checkbox.deselect() # Default OFF

        # Status Label (Row 3)
        self.status_label = customtkinter.CTkLabel(self.main_content_frame, text="Status: Ready", anchor="w")
        self.status_label.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")

        # --- Load Persistent Data ---
        # Load user settings first (sets API key env var, gets theme/model prefs)
        self.load_user_settings()
        # Load history (uses history_manager function)
        self.history = load_history(self.history_file)
        self.update_history_display() # Populate history frame based on loaded data

        # --- Apply Initial Theme ---
        # Uses the self.current_appearance_mode set by load_user_settings
        theme_manager.apply_theme(self, self.current_appearance_mode)

        # --- Set closing protocol ---
        self.protocol("WM_DELETE_WINDOW", self.on_closing)


    # --- Settings and Loading Methods ---

    def load_user_settings(self):
        """Loads settings from JSON, sets API key env var, determines startup theme & chat model."""
        self.current_api_key_display = ""
        loaded_mode = "System"
        loaded_chat_model = config.DEFAULT_CHAT_MODEL
        key_loaded_from_settings = False
        settings_file_path = self.user_settings_file

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
                    print("DEBUG: Loaded API key from settings.")

                # Load Appearance Mode
                loaded_mode_setting = settings_data.get("appearance_mode")
                if loaded_mode_setting in ["Light", "Dark", "System"]:
                    loaded_mode = loaded_mode_setting
                    print(f"DEBUG: Loaded appearance mode preference: '{loaded_mode}'")

                # Load Chat Model
                loaded_model_setting = settings_data.get("chat_model")
                if loaded_model_setting and isinstance(loaded_model_setting, str):
                     loaded_chat_model = loaded_model_setting
                     print(f"DEBUG: Loaded chat model preference: '{loaded_chat_model}'")

            except Exception as e:
                print(f"Error loading user settings file {settings_file_path}: {e}")
                loaded_mode = "System"
                loaded_chat_model = config.DEFAULT_CHAT_MODEL
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

        # Store determined settings before applying theme in __init__
        self.current_appearance_mode = loaded_mode
        self.current_chat_model = loaded_chat_model
        print(f"DEBUG: Startup mode determined as: {self.current_appearance_mode}")
        print(f"DEBUG: Startup chat model determined as: {self.current_chat_model}")


    def open_settings_window(self):
        """Opens the settings window or focuses it if already open."""
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.focus()
            return

        self.settings_window = customtkinter.CTkToplevel(self)
        self.settings_window.title("Settings")
        self.settings_window.geometry("500x400")
        self.settings_window.resizable(False, False)
        self.settings_window.transient(self)
        self.settings_window.grab_set() # Make modal

        # Configure grid
        self.settings_window.grid_columnconfigure(1, weight=1)
        # Configure rows
        self.settings_window.grid_rowconfigure(0, weight=0) # API Key
        self.settings_window.grid_rowconfigure(1, weight=0) # Status
        self.settings_window.grid_rowconfigure(2, weight=0) # Appearance Lbl
        self.settings_window.grid_rowconfigure(3, weight=0) # Appearance Radios
        self.settings_window.grid_rowconfigure(4, weight=0) # Model Lbl
        self.settings_window.grid_rowconfigure(5, weight=0) # Model Dropdown
        self.settings_window.grid_rowconfigure(6, weight=0) # Save/Close Buttons

        # --- API Key Section --- (Row 0)
        api_key_label = customtkinter.CTkLabel(self.settings_window, text="OpenAI API Key:")
        api_key_label.grid(row=0, column=0, padx=(20, 5), pady=(15, 5), sticky="w")
        # Store entry widget ref on the settings window itself or the main app
        self.settings_api_key_entry = customtkinter.CTkEntry(self.settings_window, width=350, show="*")
        self.settings_api_key_entry.grid(row=0, column=1, padx=(0, 20), pady=(15, 5), sticky="ew")
        self.settings_api_key_entry.insert(0, self.current_api_key_display or "")

        # --- Status Label for Settings --- (Row 1)
        self.settings_status_label = customtkinter.CTkLabel(self.settings_window, text="", anchor="w")
        self.settings_status_label.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")

        # --- Appearance Mode Section --- (Row 2, 3)
        appearance_label = customtkinter.CTkLabel(self.settings_window, text="Appearance Mode:")
        appearance_label.grid(row=2, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="w")
        # Store var on settings window or main app
        self.appearance_mode_var = customtkinter.StringVar(master=self.settings_window, value=self.current_appearance_mode)
        radio_frame = customtkinter.CTkFrame(self.settings_window, fg_color="transparent")
        radio_frame.grid(row=3, column=0, columnspan=2, padx=15, pady=0, sticky="w")
        radio_light = customtkinter.CTkRadioButton(master=radio_frame, text="Light", variable=self.appearance_mode_var, value="Light", command=self.change_appearance_mode)
        radio_light.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        radio_dark = customtkinter.CTkRadioButton(master=radio_frame, text="Dark", variable=self.appearance_mode_var, value="Dark", command=self.change_appearance_mode)
        radio_dark.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        radio_system = customtkinter.CTkRadioButton(master=radio_frame, text="System", variable=self.appearance_mode_var, value="System", command=self.change_appearance_mode)
        radio_system.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # --- Chat Model Selection Section --- (Row 4, 5)
        model_label = customtkinter.CTkLabel(self.settings_window, text="Chat Model:")
        model_label.grid(row=4, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="w")
        # Store var on settings window or main app
        self.settings_model_var = customtkinter.StringVar(master=self.settings_window, value=self.current_chat_model)
        model_list = api_handler.DEFAULT_CHAT_MODELS # Start with default
        try:
            current_key = os.getenv("OPENAI_API_KEY")
            if current_key:
                print("DEBUG: API key found, attempting to fetch model list for settings...")
                temp_client = OpenAI(api_key=current_key)
                fetched_list = api_handler.get_available_chat_models(temp_client)
                if fetched_list: model_list = fetched_list
                else: print("WARN: Fetched model list was empty, using defaults.")
            else:
                print("WARN: No API key configured, cannot fetch model list. Using default models.")
                if self.settings_status_label.winfo_exists():
                     self.settings_status_label.configure(text="API Key needed to fetch full model list.", text_color="orange")
        except Exception as e:
             print(f"Error fetching model list: {e}. Using defaults.")
             if self.settings_status_label.winfo_exists():
                  self.settings_status_label.configure(text="Error fetching model list.", text_color="orange")

        if self.current_chat_model not in model_list:
             model_list.insert(0, self.current_chat_model)

        model_dropdown = customtkinter.CTkOptionMenu(
            self.settings_window, values=model_list, variable=self.settings_model_var
        )
        model_dropdown.grid(row=5, column=0, columnspan=2, padx=20, pady=5, sticky="ew")

        # --- Save/Close Buttons --- (Row 6)
        save_button = customtkinter.CTkButton(self.settings_window, text="Save Settings", command=self.save_settings)
        save_button.grid(row=6, column=0, padx=(20, 5), pady=(20, 20), sticky="ew")
        close_button = customtkinter.CTkButton(self.settings_window, text="Close", command=self.on_settings_close)
        close_button.grid(row=6, column=1, padx=(5, 20), pady=(20, 20), sticky="ew")

        self.settings_window.protocol("WM_DELETE_WINDOW", self.on_settings_close)

    def save_settings(self):
        """Saves the API key, appearance mode, and chat model."""
        # Check if window and widgets still exist before accessing them
        if self.settings_window is None or not self.settings_window.winfo_exists(): return
        if not hasattr(self, 'settings_api_key_entry') or not self.settings_api_key_entry.winfo_exists(): return
        if not hasattr(self, 'settings_model_var'): return # Var should still exist even if dropdown doesn't
        if not hasattr(self, 'settings_status_label') or not self.settings_status_label.winfo_exists(): return

        # Get API Key
        new_key = self.settings_api_key_entry.get().strip()
        key_warning = ""
        if not new_key: new_key = None
        elif not new_key.startswith("sk-"): key_warning = "Warning: Key might be invalid. "

        # Get Appearance Mode (already updated in self.current_appearance_mode)
        selected_mode = self.current_appearance_mode

        # Get Chat Model
        selected_model = self.settings_model_var.get()
        if not selected_model: selected_model = config.DEFAULT_CHAT_MODEL
        self.current_chat_model = selected_model
        print(f"DEBUG: Chat model preference to save: {self.current_chat_model}")

        # Prepare data
        settings_data = {}
        if new_key: settings_data["openai_api_key"] = new_key
        settings_data["appearance_mode"] = selected_mode
        settings_data["chat_model"] = selected_model

        try:
            # Save to JSON file
            settings_file_path = self.user_settings_file
            settings_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(settings_file_path, "w", encoding="utf-8") as f:
                json.dump(settings_data, f, indent=4)

            # Update environment variable IF a valid key was entered/saved
            key_saved_message = ""
            if new_key and new_key.startswith("sk-"):
                os.environ['OPENAI_API_KEY'] = new_key
                self.current_api_key_display = new_key
                key_saved_message = "API Key Saved. "
                print("Saved new API key.")
            elif not new_key: # Key was cleared
                 # Update display, potentially clear env var? Risky if set externally.
                 self.current_api_key_display = "" # Clear display if cleared in settings
                 if 'OPENAI_API_KEY' in os.environ: del os.environ['OPENAI_API_KEY'] # Clear env var only if explicitly cleared via settings
                 key_saved_message = "API Key Cleared in Settings. "
                 print("API key cleared in settings & os.environ.")

            print(f"Saved appearance mode '{selected_mode}' and chat model '{selected_model}'.")
            self.settings_status_label.configure(text=key_warning + key_saved_message + "Settings Saved!", text_color="green")

        except Exception as e:
            print(f"Error saving user settings: {e}")
            self.settings_status_label.configure(text=f"Error saving settings: {e}", text_color="red")

    def on_settings_close(self):
        """Callback for when the settings window is closed."""
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.grab_release()
            self.settings_window.destroy()
        self.settings_window = None
        # Clean up potentially lingering instance variables from settings window
        attrs_to_delete = ['appearance_mode_var', 'settings_api_key_entry',
                           'settings_status_label', 'settings_model_var']
        for attr in attrs_to_delete:
            if hasattr(self, attr):
                try:
                    delattr(self, attr)
                except AttributeError:
                    pass # Ignore if already deleted


    def change_appearance_mode(self):
        """Updates the stored mode and applies the theme using theme_manager."""
        if not hasattr(self, 'appearance_mode_var'): return # Check if var exists
        new_mode = self.appearance_mode_var.get()
        print(f"DEBUG: Appearance mode radio button changed to: {new_mode}")
        if new_mode in ["Light", "Dark", "System"]:
            self.current_appearance_mode = new_mode
            theme_manager.apply_theme(self, new_mode)
        else:
             print(f"Error: Invalid appearance mode selected in UI: {new_mode}")

    # --- UI Update & Control Methods ---
    # toggle_tts, toggle_speak_input, handle_ctrl_enter
    # update_status, update_output_textbox, set_ui_state, set_stop_button_state
    # (Keep these as they were with the winfo_exists checks)
    def toggle_tts(self): self.tts_enabled = bool(self.tts_checkbox.get()); print(f"TTS: {self.tts_enabled}") # Simplified for brevity
    def toggle_speak_input(self): self.speak_input_enabled = bool(self.speak_input_checkbox.get()); print(f"SpeakInput: {self.speak_input_enabled}")
    def handle_ctrl_enter(self, event): print("Ctrl+Enter"); self.start_processing_thread(); return "break"
    def update_status(self, message): self._safe_ui_update(self.status_label, configure_options={"text": f"Status: {message}"})
    def update_output_textbox(self, text): self._safe_ui_update(self.output_textbox, configure_options={"state": "normal"}, insert_text=text, final_configure_options={"state": "disabled"})
    def set_ui_state(self, processing: bool):
        submit_state = "disabled" if processing else "normal"
        input_state = "disabled" if processing else "normal"
        self._safe_ui_update(self.submit_button, configure_options={"state": submit_state})
        self._safe_ui_update(self.input_textbox, configure_options={"state": input_state})
    def set_stop_button_state(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self._safe_ui_update(self.stop_button, configure_options={"state": state})

    # Helper for safe UI updates from threads via self.after
    def _safe_ui_update(self, widget, configure_options={}, insert_text=None, final_configure_options=None):
        def _update():
            if self._is_shutting_down.is_set(): return
            if hasattr(self, widget_name) and widget is not None and widget.winfo_exists():
                if configure_options: widget.configure(**configure_options)
                if insert_text is not None: # Handle text insertion separately
                     # Assuming Textbox for insert_text
                     widget.delete("0.0", "end")
                     widget.insert("0.0", insert_text or "")
                if final_configure_options: widget.configure(**final_configure_options) # e.g., set state back
            else: print(f"DEBUG: Widget '{widget_name}' no longer exists, skipping update.")

        # Find the widget's name on self for debug message
        widget_name = "UnknownWidget"
        for name, value in self.__dict__.items():
            if value is widget: widget_name = name; break

        if threading.current_thread() is not threading.main_thread(): self.after(0, _update)
        else: _update()


    # --- History Methods ---
    def update_history_display(self):
        if self._is_shutting_down.is_set(): return
        if not hasattr(self, 'history_frame') or not self.history_frame.winfo_exists(): return
        for widget in self.history_frame.winfo_children(): widget.destroy()
        if not isinstance(self.history, list): self.history = []
        for i, item in enumerate(self.history):
             if isinstance(item, (list, tuple)) and len(item) >= 2:
                 prompt, response = item[0], item[1]
                 timestamp = item[2] if len(item) > 2 else None
                 display_prompt = (prompt[:35] + '...') if len(prompt) > 38 else prompt
                 history_button = customtkinter.CTkButton(self.history_frame, text=display_prompt.replace("\n", " "), anchor="w", command=lambda p=prompt, r=response, ts=timestamp: self.load_history_item(p, r, ts))
                 history_button.grid(row=i, column=0, padx=5, pady=3, sticky="ew")
             else: print(f"Warning: Skipping invalid history item at index {i}: {item}")

    def load_history_item(self, prompt, response, timestamp):
        if self._is_shutting_down.is_set(): return
        if self.processing_thread and self.processing_thread.is_alive(): self.update_status("Error: Cannot load history while processing."); return
        if hasattr(self, 'input_textbox') and self.input_textbox.winfo_exists():
             self.input_textbox.configure(state="normal"); self.input_textbox.delete("0.0", "end"); self.input_textbox.insert("0.0", prompt)
        self.update_output_textbox(response)
        self.selected_history_timestamp = None
        play_button_state = "disabled"
        status_msg = "Loaded item. "
        if timestamp:
            audio_path = config.RESPONSES_DIR / f"response_{timestamp}.mp3"
            if audio_path.exists():
                self.selected_history_timestamp = timestamp
                play_button_state = "normal"
                status_msg += "Audio available."
            else: status_msg += "Audio file missing."
        else: status_msg += "No audio recorded for this entry."
        self.update_status(status_msg)
        if hasattr(self, 'play_history_button') and self.play_history_button.winfo_exists(): self.play_history_button.configure(state=play_button_state)

    # --- Playback Methods ---
    def play_selected_history(self):
        if self._is_shutting_down.is_set(): return
        if not self.selected_history_timestamp: self.update_status("Error: No history item with audio selected."); return
        if self.processing_thread and self.processing_thread.is_alive(): self.update_status("Error: Cannot play history while processing."); return
        if self.is_playing: self.update_status("Error: Already playing audio."); return
        audio_path = config.RESPONSES_DIR / f"response_{self.selected_history_timestamp}.mp3"
        if not audio_path.exists():
            self.update_status(f"Error: Audio file not found: {audio_path.name}")
            if hasattr(self, 'play_history_button') and self.play_history_button.winfo_exists(): self.play_history_button.configure(state="disabled")
            self.selected_history_timestamp = None; return
        if hasattr(self, 'play_history_button') and self.play_history_button.winfo_exists(): self.play_history_button.configure(state="disabled")
        self._start_playback_thread(str(audio_path), "Playing history audio...")

    def _start_playback_thread(self, audio_path_str: str, status_playing: str):
        if self._is_shutting_down.is_set(): return
        playback_thread = threading.Thread(target=self._execute_playback_and_reenable, args=(audio_path_str, status_playing), daemon=True)
        playback_thread.start()

    def _execute_playback_and_reenable(self, audio_path_str: str, status_playing: str):
        playback_completed_naturally = False
        try:
            if self._is_shutting_down.is_set(): return
            playback_completed_naturally = self._play_audio_blocking(audio_path_str, status_playing)
            if self._is_shutting_down.is_set(): return
        finally:
            self.after(0, self._safe_reenable_play_history_button_after_thread)
            # Set final status if needed
            # Maybe check self.status_label directly here is okay as it's scheduled via self.after
            if self.status_label.winfo_exists():
                 current_status = self.status_label.cget("text")
                 if "Error" not in current_status and "stopped" not in current_status and "finished" not in current_status:
                      self.after(100, lambda: self.update_status("Ready"))

    def _safe_reenable_play_history_button_after_thread(self):
        if self._is_shutting_down.is_set(): return
        if not hasattr(self, 'play_history_button') or not self.play_history_button.winfo_exists(): return
        current_selected_ts = self.selected_history_timestamp
        new_state = "disabled"
        if current_selected_ts and (config.RESPONSES_DIR / f"response_{current_selected_ts}.mp3").exists(): new_state = "normal"
        self.play_history_button.configure(state=new_state)

    def _play_audio_blocking(self, audio_path_str: str, status_playing: str = "Playing audio...") -> bool:
        # (Keep this method as previously corrected, with shutdown checks)
        print(f"DEBUG: _play_audio_blocking started for path: {audio_path_str}")
        if self._is_shutting_down.is_set(): return False
        if not audio_path_str or not self.player.initialized: return False
        natural_finish = False
        try:
            if self._is_shutting_down.is_set(): return False
            self.after(0, lambda: self.update_status("Loading audio..."))
            if not self.player.load(audio_path_str): raise RuntimeError(f"Failed to load audio file: {audio_path_str}")
            print(f"DEBUG: _play_audio_blocking: Loaded successfully.")
            if self._is_shutting_down.is_set(): return False
            self.is_playing = True
            self.set_stop_button_state(enabled=True)
            self.update_status(status_playing)
            print(f"DEBUG: _play_audio_blocking: Attempting to play.")
            self.player.play()
            print(f"DEBUG: _play_audio_blocking: play() called. Entering wait loop.")
            while self.player.is_busy() and self.is_playing:
                if self._is_shutting_down.is_set(): print("DEBUG: Shutdown detected during playback loop."); self.player.stop(); self.is_playing = False; break
                time.sleep(0.1)
            print(f"DEBUG: _play_audio_blocking: Exited wait loop. is_playing={self.is_playing}")
            if self.is_playing: print("DEBUG: Playback finished naturally."); self.update_status("Playback finished."); self.is_playing = False; natural_finish = True
        except Exception as e: print(f"DEBUG: _play_audio_blocking - Error during playback section: {e}"); self.update_status(f"Error during playback: {e}"); self.is_playing = False
        finally: print("DEBUG: _play_audio_blocking: finally block. Stopping/unloading player."); self.player.stop(); self.player.unload(); print("DEBUG: _play_audio_blocking: finally block. Disabling stop button."); self.set_stop_button_state(enabled=False)
        print(f"DEBUG: _play_audio_blocking finished. Returning: {natural_finish}")
        return natural_finish

    # --- Core Logic and Threading ---
    def start_processing_thread(self):
        # (Keep this method as previously corrected)
        if self._is_shutting_down.is_set(): return
        user_prompt = self.input_textbox.get("0.0", "end-1c").strip()
        if not user_prompt or user_prompt == "Enter your text here...": self.update_status("Error: Please enter some text."); return
        if self.processing_thread and self.processing_thread.is_alive(): self.update_status("Error: Processing already in progress."); return
        self.set_ui_state(processing=True); self.update_status("Processing..."); self.update_output_textbox("")
        self.processing_thread = threading.Thread(target=self.process_request_in_background, args=(user_prompt,), daemon=True); self.processing_thread.start()

    def stop_playback(self):
        # (Keep this method as previously corrected)
        if self.is_playing: print("Stop playback requested."); self.player.stop(); self.is_playing = False; self.update_status("Playback stopped."); self.set_stop_button_state(enabled=False)

    def process_request_in_background(self, prompt):
        # (Keep this method as previously corrected, with the split logic based on self.speak_input_enabled)
        client = None; generated_text = None; playback_completed_naturally = True; timestamp_for_history = None
        try:
            if self._is_shutting_down.is_set(): return
            print("DEBUG: Background thread started. Initializing OpenAI client.")
            client = OpenAI();
            if not client.api_key: raise ValueError("OpenAI API key missing.")
            print("DEBUG: OpenAI client initialized.")
            if self.speak_input_enabled: # Path 1: Speak Input ONLY
                 if self._is_shutting_down.is_set(): return
                 self.update_status("Generating speech for input...")
                 prompt_audio_path_str = None; audio_generated = False
                 timestamp_for_history = datetime.now().strftime("%Y%m%d_%H%M%S")
                 output_filename = config.RESPONSES_DIR / f"response_{timestamp_for_history}.mp3"
                 print(f"DEBUG: Input TTS - Target output file: {output_filename}")
                 try:
                     api_handler.generate_speech(client, prompt, output_filename, config.DEFAULT_TTS_MODEL, config.DEFAULT_TTS_VOICE); prompt_audio_path_str = str(output_filename); audio_generated = True; print(f"DEBUG: Input TTS - API call succeeded for {prompt_audio_path_str}")
                 except (ConnectionError, RuntimeError, Exception) as prompt_tts_error: print(f"DEBUG: Input TTS - ERROR during generation: {prompt_tts_error}"); self.update_status(f"Error generating prompt audio: {prompt_tts_error}"); timestamp_for_history = None
                 if audio_generated and prompt_audio_path_str:
                     if self._is_shutting_down.is_set(): return
                     print("DEBUG: Input TTS - Generation succeeded. Proceeding to play."); playback_completed_naturally = self._play_audio_blocking(prompt_audio_path_str, status_playing="Speaking input..."); print(f"DEBUG: Input TTS - Playback finished. Completed naturally: {playback_completed_naturally}")
                 elif not audio_generated: print("DEBUG: Input TTS - Generation failed.")
                 if self._is_shutting_down.is_set(): return
                 print(f"DEBUG: Adding input-only history. Timestamp: {timestamp_for_history}"); placeholder_response = "(Input Spoken - No AI Response)"; self.history.insert(0, (prompt, placeholder_response, timestamp_for_history)); self.after(0, self.update_history_display)
                 final_status = "Ready";
                 if not audio_generated: final_status = "Ready (Input audio generation failed)."
                 elif playback_completed_naturally: final_status = "Ready (Input spoken)."
                 else: final_status = "Ready (Input speech stopped)."
                 self.update_status(final_status); print("DEBUG: Input TTS path finished. Returning from thread."); return
            else: # Path 2: Get AI Response
                 if self._is_shutting_down.is_set(): return
                 self.update_status("Generating AI response."); generated_text = api_handler.get_chat_response(client, prompt, self.current_chat_model);
                 if self._is_shutting_down.is_set(): return
                 self.after(0, lambda: self.update_output_textbox(generated_text))
                 if generated_text and not generated_text.startswith(("(No text response", "Error:")):
                     if self._is_shutting_down.is_set(): return
                     timestamp_for_history = None;
                     if self.tts_enabled: timestamp_for_history = datetime.now().strftime("%Y%m%d_%H%M%S")
                     print(f"DEBUG: Saving history item: (prompt='{prompt[:20]}...', response='{generated_text[:20]}...', timestamp='{timestamp_for_history}')"); self.history.insert(0, (prompt, generated_text, timestamp_for_history)); self.after(0, self.update_history_display)
                     status_msg = "Response received. Generating audio..." if self.tts_enabled else "Response received (Speech disabled)."; self.update_status(status_msg)
                 else: self.update_status("Failed to get valid text response."); return
                 if self.tts_enabled and timestamp_for_history:
                     if self._is_shutting_down.is_set(): return
                     output_filename = config.RESPONSES_DIR / f"response_{timestamp_for_history}.mp3"; response_audio_path = None; response_audio_generated = False
                     try: print(f"DEBUG: Response TTS - Attempting generation for file: {output_filename}"); api_handler.generate_speech(client, generated_text, output_filename, config.DEFAULT_TTS_MODEL, config.DEFAULT_TTS_VOICE); response_audio_path = str(output_filename); response_audio_generated = True; print(f"DEBUG: Response TTS - API call succeeded for {output_filename}")
                     except (ConnectionError, RuntimeError, Exception) as response_tts_error: print(f"DEBUG: Response TTS - ERROR during generation: {response_tts_error}"); self.update_status(f"Error generating response audio: {response_tts_error}")
                     if response_audio_generated:
                         if self._is_shutting_down.is_set(): return
                         print("DEBUG: Response TTS - Generation succeeded. Proceeding to play."); playback_completed_naturally = self._play_audio_blocking(response_audio_path, status_playing="Playing response..."); print(f"DEBUG: Response TTS - Playback finished. Completed naturally: {playback_completed_naturally}")
                         if self._is_shutting_down.is_set(): return
                         print("DEBUG: Response TTS - Initiating cleanup."); cleanup_old_recordings(config.RESPONSES_DIR, config.MAX_RECORDINGS)
                         if playback_completed_naturally: self.update_status("Ready")
                     else: print("DEBUG: Response TTS - Generation failed. Setting status."); self.update_status("Ready (Response audio generation failed).")
                 elif self.tts_enabled and not timestamp_for_history: print("DEBUG: Warning - TTS enabled but no timestamp captured."); self.update_status("Ready (Internal history timestamp error).")
                 else: print("DEBUG: Response TTS is disabled."); self.update_status("Ready (Speech disabled).")
        except (ValueError, ConnectionError, RuntimeError, Exception) as e: error_msg_thread = f"Error: {e}"; print(error_msg_thread); final_text = generated_text or f"Error: {e}"; self.after(0, lambda: self.update_output_textbox(final_text)); self.update_status(f"Error: {e}"); self.is_playing = False
        finally: self.after(0, self._safe_reenable_ui_after_thread)


    # --- Closing Method ---
    def on_closing(self):
        """Handles window closing event."""
        print("Closing application...")
        self._is_shutting_down.set()
        if self.is_playing: print("Stopping active playback..."); self.player.stop(); self.is_playing = False
        print("Saving history..."); save_history(self.history_file, self.history)
        print("Quitting pygame mixer..."); self.player.quit()
        print("Destroying main window..."); self.destroy()