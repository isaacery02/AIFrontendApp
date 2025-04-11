# settings_window.py
# Defines the Settings Toplevel window

import customtkinter
import tkinter as tk
import os
from openai import OpenAI, OpenAIError

# Import from custom modules
import config
import api_handler

# Define available TTS voices
TTS_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

class SettingsWindow(customtkinter.CTkToplevel):
    """
    Toplevel window for application settings (API Key, Theme, Model, Voice).
    """
    def __init__(self, master_app):
        super().__init__(master_app)

        self.master_app = master_app

        self.title("Settings")
        self.geometry("500x480") # Increased height again for voice option
        self.resizable(False, False)
        self.transient(master_app)
        self.grab_set()

        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        # Add more rows
        self.grid_rowconfigure(0, weight=0) # API Key
        self.grid_rowconfigure(1, weight=0) # Status
        self.grid_rowconfigure(2, weight=0) # Appearance Lbl
        self.grid_rowconfigure(3, weight=0) # Appearance Radios
        self.grid_rowconfigure(4, weight=0) # Model Lbl
        self.grid_rowconfigure(5, weight=0) # Model Dropdown
        self.grid_rowconfigure(6, weight=0) # Voice Lbl  <-- NEW
        self.grid_rowconfigure(7, weight=0) # Voice Dropdown <-- NEW
        self.grid_rowconfigure(8, weight=1) # Spacer <-- NEW
        self.grid_rowconfigure(9, weight=0) # Save/Close Buttons <-- NEW ROW INDEX

        # --- API Key Section --- (Row 0)
        api_key_label = customtkinter.CTkLabel(self, text="OpenAI API Key:")
        api_key_label.grid(row=0, column=0, padx=(20, 5), pady=(15, 5), sticky="w")
        self.api_key_entry = customtkinter.CTkEntry(self, width=350, show="*")
        self.api_key_entry.grid(row=0, column=1, padx=(0, 20), pady=(15, 5), sticky="ew")
        self.api_key_entry.insert(0, self.master_app.current_api_key_display or "")

        # --- Status Label for Settings --- (Row 1)
        self.status_label = customtkinter.CTkLabel(self, text="", anchor="w")
        self.status_label.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")

        # --- Appearance Mode Section --- (Row 2, 3)
        appearance_label = customtkinter.CTkLabel(self, text="Appearance Mode:")
        appearance_label.grid(row=2, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="w")
        self.appearance_mode_var = customtkinter.StringVar(master=self, value=self.master_app.current_appearance_mode)
        radio_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        radio_frame.grid(row=3, column=0, columnspan=2, padx=15, pady=0, sticky="w")
        # (Radio buttons creation remains the same)
        radio_light = customtkinter.CTkRadioButton(master=radio_frame, text="Light", variable=self.appearance_mode_var, value="Light", command=self.apply_appearance_change)
        radio_light.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        radio_dark = customtkinter.CTkRadioButton(master=radio_frame, text="Dark", variable=self.appearance_mode_var, value="Dark", command=self.apply_appearance_change)
        radio_dark.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        radio_system = customtkinter.CTkRadioButton(master=radio_frame, text="System", variable=self.appearance_mode_var, value="System", command=self.apply_appearance_change)
        radio_system.grid(row=0, column=2, padx=5, pady=5, sticky="w")

        # --- Chat Model Selection Section --- (Row 4, 5)
        model_label = customtkinter.CTkLabel(self, text="Chat Model:")
        model_label.grid(row=4, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="w")
        self.model_var = customtkinter.StringVar(master=self, value=self.master_app.current_chat_model)
        model_list = self._fetch_models()
        if self.master_app.current_chat_model not in model_list:
             model_list.insert(0, self.master_app.current_chat_model)
        self.model_dropdown = customtkinter.CTkOptionMenu(
            self, values=model_list, variable=self.model_var
        )
        self.model_dropdown.grid(row=5, column=0, columnspan=2, padx=20, pady=5, sticky="ew")

        # --- TTS Voice Selection Section --- (Row 6, 7) ## NEW SECTION ##
        voice_label = customtkinter.CTkLabel(self, text="TTS Voice:")
        voice_label.grid(row=6, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="w")

        # Variable for dropdown
        self.voice_var = customtkinter.StringVar(master=self, value=self.master_app.current_tts_voice)

        voice_dropdown = customtkinter.CTkOptionMenu(
            self,
            values=TTS_VOICES, # Use the list defined at the top
            variable=self.voice_var
        )
        voice_dropdown.grid(row=7, column=0, columnspan=2, padx=20, pady=5, sticky="ew")
        # --- End TTS Voice Section ---

        # --- Save/Close Buttons --- (Row 9) ## ADJUSTED ROW ##
        save_button = customtkinter.CTkButton(self, text="Save Settings", command=self.save_and_close)
        save_button.grid(row=9, column=0, padx=(20, 5), pady=(20, 20), sticky="ew")
        close_button = customtkinter.CTkButton(self, text="Cancel", command=self.close_window)
        close_button.grid(row=9, column=1, padx=(5, 20), pady=(20, 20), sticky="ew")

        self.protocol("WM_DELETE_WINDOW", self.close_window)


    def _fetch_models(self) -> list[str]:
        # (Keep this method as is)
        model_list = api_handler.DEFAULT_CHAT_MODELS
        try:
            current_key = os.getenv("OPENAI_API_KEY")
            if current_key:
                print("DEBUG: Settings - API key found, attempting to fetch model list...")
                temp_client = OpenAI(api_key=current_key)
                fetched_list = api_handler.get_available_chat_models(temp_client)
                if fetched_list: model_list = fetched_list
                else: print("WARN: Settings - Fetched model list was empty, using defaults.")
            else:
                print("WARN: Settings - No API key configured, cannot fetch model list.")
                if self.status_label.winfo_exists():
                     self.status_label.configure(text="API Key needed to fetch model list.", text_color="orange")
        except Exception as e:
             print(f"Error fetching model list for settings: {e}. Using defaults.")
             if self.status_label.winfo_exists():
                  self.status_label.configure(text="Error fetching model list.", text_color="orange")
        return model_list

    def apply_appearance_change(self):
        """Applies appearance mode change to main app."""
        new_mode = self.appearance_mode_var.get()
        self.master_app.apply_app_theme(new_mode)

    def save_and_close(self):
        """Saves settings via master app and closes window."""
        new_key = self.api_key_entry.get().strip() or None
        new_mode = self.appearance_mode_var.get()
        new_model = self.model_var.get()
        # --- Get selected voice --- ## ADDED ##
        new_voice = self.voice_var.get()
        if new_voice not in TTS_VOICES: # Basic validation
             print(f"WARN: Invalid voice '{new_voice}' selected, using default.")
             new_voice = config.DEFAULT_TTS_VOICE
        # -------------------------- ## END ADDED ##

        # Call master app's save function with the new voice argument
        saved_ok = self.master_app.update_and_save_settings(
            api_key=new_key,
            appearance_mode=new_mode,
            chat_model=new_model,
            tts_voice=new_voice # Pass the voice
        )

        if saved_ok:
            print("Settings saved via main app.")
            self.close_window()
        else:
             print("Settings save failed (see main app logs).")
             if self.status_label.winfo_exists():
                  self.status_label.configure(text="Failed to save settings.", text_color="red")


    def close_window(self):
        """Handles closing the settings window."""
        print("Closing settings window.")
        self.grab_release()
        self.master_app.settings_window_closed() # Notify main app
        self.destroy()

