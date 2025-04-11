# settings_window.py
# Defines the Settings Toplevel window

import customtkinter
import tkinter as tk
import os
from openai import OpenAI, OpenAIError # Keep for type hint if needed, but not used directly

# Import from custom modules
import config
import api_handler # Keep for default model list

# Define available TTS voices and speed options
TTS_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
TTS_SPEEDS = { # Dictionary mapping display string to speed float value
    "0.5x": 0.5, "0.75x": 0.75, "Normal (1.0x)": 1.0,
    "1.25x": 1.25, "1.5x": 1.5, "2.0x": 2.0,
}

class SettingsWindow(customtkinter.CTkToplevel):
    """
    Toplevel window for application settings (API Key, Theme, Model, Voice, Speed).
    Receives the model list from the main application.
    """
    # Modified __init__ signature to accept model_list
    def __init__(self, master_app, model_list: list):
        super().__init__(master_app)

        self.master_app = master_app

        self.title("Settings")
        self.geometry("500x480")
        self.resizable(False, False)
        self.transient(master_app)
        self.grab_set()

        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0); self.grid_rowconfigure(1, weight=0) # API Key, Status
        self.grid_rowconfigure(2, weight=0); self.grid_rowconfigure(3, weight=0) # Appearance
        self.grid_rowconfigure(4, weight=0); self.grid_rowconfigure(5, weight=0) # Model
        self.grid_rowconfigure(6, weight=0); self.grid_rowconfigure(7, weight=0) # Voice
        self.grid_rowconfigure(8, weight=0); self.grid_rowconfigure(9, weight=0) # Speed
        self.grid_rowconfigure(10, weight=1) # Spacer
        self.grid_rowconfigure(11, weight=0) # Buttons

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
        appearance_label.grid(row=2, column=0, columnspan=2, padx=20, pady=(5, 0), sticky="w")
        self.appearance_mode_var = customtkinter.StringVar(master=self, value=self.master_app.current_appearance_mode)
        radio_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        radio_frame.grid(row=3, column=0, columnspan=2, padx=15, pady=0, sticky="w")
        radio_light = customtkinter.CTkRadioButton(master=radio_frame, text="Light", variable=self.appearance_mode_var, value="Light", command=self.apply_appearance_change)
        radio_light.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        radio_dark = customtkinter.CTkRadioButton(master=radio_frame, text="Dark", variable=self.appearance_mode_var, value="Dark", command=self.apply_appearance_change)
        radio_dark.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        radio_system = customtkinter.CTkRadioButton(master=radio_frame, text="System", variable=self.appearance_mode_var, value="System", command=self.apply_appearance_change)
        radio_system.grid(row=0, column=2, padx=5, pady=2, sticky="w")

        # --- Chat Model Selection Section --- (Row 4, 5)
        model_label = customtkinter.CTkLabel(self, text="Chat Model:")
        model_label.grid(row=4, column=0, columnspan=2, padx=20, pady=(5, 0), sticky="w")
        self.model_var = customtkinter.StringVar(master=self, value=self.master_app.current_chat_model)

        # --- Use the passed model_list --- ## MODIFIED ##
        # Ensure current model is in the list passed from main app
        if self.master_app.current_chat_model not in model_list:
             model_list.insert(0, self.master_app.current_chat_model)

        self.model_dropdown = customtkinter.CTkOptionMenu(
            self,
            values=model_list, # Use the list passed as argument
            variable=self.model_var
        )
        self.model_dropdown.grid(row=5, column=0, columnspan=2, padx=20, pady=2, sticky="ew")
        # --------------------------------- ## END MODIFIED ##

        # --- TTS Voice Selection Section --- (Row 6, 7)
        voice_label = customtkinter.CTkLabel(self, text="TTS Voice:")
        voice_label.grid(row=6, column=0, columnspan=2, padx=20, pady=(5, 0), sticky="w")
        current_voice = self.master_app.current_tts_voice
        if current_voice not in TTS_VOICES: current_voice = config.DEFAULT_TTS_VOICE
        self.voice_var = customtkinter.StringVar(master=self, value=current_voice)
        voice_dropdown = customtkinter.CTkOptionMenu(
            self, values=TTS_VOICES, variable=self.voice_var
        )
        voice_dropdown.grid(row=7, column=0, columnspan=2, padx=20, pady=2, sticky="ew")

        # --- TTS Speed Selection Section --- (Row 8, 9)
        speed_label = customtkinter.CTkLabel(self, text="Speech Speed:")
        speed_label.grid(row=8, column=0, columnspan=2, padx=20, pady=(5, 0), sticky="w")
        current_speed_float = self.master_app.current_tts_speed
        current_speed_str = "Normal (1.0x)"
        for display, value in TTS_SPEEDS.items():
             if value == current_speed_float: current_speed_str = display; break
        self.speed_var = customtkinter.StringVar(master=self, value=current_speed_str)
        speed_dropdown = customtkinter.CTkOptionMenu(
            self, values=list(TTS_SPEEDS.keys()), variable=self.speed_var
        )
        speed_dropdown.grid(row=9, column=0, columnspan=2, padx=20, pady=2, sticky="ew")

        # --- Save/Close Buttons --- (Row 11)
        save_button = customtkinter.CTkButton(self, text="Save Settings", command=self.save_and_close)
        save_button.grid(row=11, column=0, padx=(20, 5), pady=(20, 20), sticky="ew")
        close_button = customtkinter.CTkButton(self, text="Cancel", command=self.close_window)
        close_button.grid(row=11, column=1, padx=(5, 20), pady=(20, 20), sticky="ew")

        self.protocol("WM_DELETE_WINDOW", self.close_window)


    # --- REMOVE the internal _fetch_models method ---
    # def _fetch_models(self) -> list[str]: ...


    def apply_appearance_change(self):
        """Applies appearance mode change to main app."""
        new_mode = self.appearance_mode_var.get()
        # Call the main app's method to apply the theme
        self.master_app.apply_app_theme(new_mode)


    def save_and_close(self):
        """Saves settings via master app and closes window."""
        new_key = self.api_key_entry.get().strip() or None
        new_mode = self.appearance_mode_var.get()
        new_model = self.model_var.get()
        new_voice = self.voice_var.get()
        selected_speed_str = self.speed_var.get()
        new_speed = TTS_SPEEDS.get(selected_speed_str, config.DEFAULT_TTS_SPEED)

        if new_voice not in TTS_VOICES: new_voice = config.DEFAULT_TTS_VOICE

        # Call master app's save function with all arguments
        saved_ok = self.master_app.update_and_save_settings(
            api_key=new_key,
            appearance_mode=new_mode,
            chat_model=new_model,
            tts_voice=new_voice,
            tts_speed=new_speed
        )

        if saved_ok:
            print("Settings saved via main app.")
            self.close_window()
        else:
             print("Settings save failed (see main app logs).")
             if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                  self.status_label.configure(text="Failed to save settings.", text_color="red")


    def close_window(self):
        """Handles closing the settings window."""
        print("Closing settings window.")
        self.grab_release()
        self.master_app.settings_window_closed() # Notify main app
        self.destroy()

