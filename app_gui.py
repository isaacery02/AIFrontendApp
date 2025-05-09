# app_gui.py

# ... (Keep all existing imports) ...
import customtkinter
import threading
import time
from pathlib import Path
from openai import OpenAI, OpenAIError
import os
import json
from datetime import datetime
import tkinter as tk
import traceback

import config
import api_handler
from audio_player import AudioPlayer
from history_manager import load_history, save_history
from file_utils import cleanup_old_recordings
import theme_manager
from settings_window import SettingsWindow, TTS_VOICES, TTS_SPEEDS


class ChatApp(customtkinter.CTk):
    """Main Application class."""

    def __init__(self, player: AudioPlayer):
        super().__init__()

        # --- Initial Setup ---
        customtkinter.set_appearance_mode("System")
        customtkinter.set_default_color_theme("blue")

        self.player = player
        self.title("AI Chat & Speech")
        self.geometry("850x550")

        # --- State Variables ---
        self._is_shutting_down = threading.Event()
        self.settings_window = None
        self.current_api_key_display = ""
        self.selected_history_timestamp = None
        self.current_chat_model = config.DEFAULT_CHAT_MODEL
        self.current_appearance_mode = "System"
        self.current_tts_voice = config.DEFAULT_TTS_VOICE
        self.current_tts_speed = config.DEFAULT_TTS_SPEED
        self.tts_enabled = True
        self.speak_input_enabled = False
        self.is_playing = False
        self.processing_thread = None
        # --- Add variable to store fetched models ---
        self.available_models = api_handler.DEFAULT_CHAT_MODELS # Initialize with default

        # --- File Paths ---
        self.history_file = config.HISTORY_FILE
        self.user_settings_file = config.APP_BASE_DATA_DIR / "user_settings.json"

        # --- Load Persistent Data ---
        self.load_user_settings() # Load saved prefs first
        self.history = load_history(self.history_file)

        # --- Fetch Models ONCE at Startup ---
        self.fetch_models_startup() # Call new method to get model list

        # --- Build UI ---
        self._create_widgets() # Build UI AFTER models might be fetched
        self.update_history_display() # Populate history frame

        # --- Apply Initial Theme ---
        theme_manager.apply_theme(self, self.current_appearance_mode)

        # --- Set closing protocol ---
        self.protocol("WM_DELETE_WINDOW", self.on_closing)


    def _create_widgets(self):
        """Creates and lays out the main UI widgets using components."""
        # Configure main window grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create PanedWindow
        self.paned_window = tk.PanedWindow(
            self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED,
            sashwidth=6, bg="gray25" # Visible sash color
        )
        self.paned_window.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # --- Pane 1: History Section ---
        self.history_container = tk.Frame(self.paned_window) # Intermediate tk Frame
        self.paned_window.add(self.history_container, stretch="never", width=180)
        # Configure grid inside container
        self.history_container.grid_rowconfigure(0, weight=0) # Title Label row
        self.history_container.grid_rowconfigure(1, weight=1) # Scrollable Frame row
        self.history_container.grid_columnconfigure(0, weight=1)

        # Create history widgets using ui_components function (assuming it exists)
        # If ui_components.py wasn't created, define widgets directly here
        # Assuming ui_components.create_history_panel exists:
        try:
            # Import locally within method if preferred, or keep at top level
            from ui_components import create_history_panel
            self.history_title_label, self.history_frame = create_history_panel(self.history_container)
        except ImportError:
            # Fallback: Define history panel widgets directly if ui_components missing
            print("WARN: ui_components.py not found, defining history panel widgets directly.")
            self.history_title_label = customtkinter.CTkLabel(master=self.history_container, text="History", font=customtkinter.CTkFont(weight="bold")); self.history_title_label.grid(row=0, column=0, padx=10, pady=(5, 5), sticky="ew")
            self.history_frame = customtkinter.CTkScrollableFrame(master=self.history_container, fg_color="transparent"); self.history_frame.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="nsew"); self.history_frame.grid_columnconfigure(0, weight=1)


        # --- Pane 2: Main Content Area ---
        self.main_content_container = tk.Frame(self.paned_window) # Intermediate tk Frame
        self.paned_window.add(self.main_content_container, stretch="always")
        # Create main panel widgets using ui_components function
        try:
            # Import locally within method if preferred, or keep at top level
            from ui_components import create_main_panel
            widgets = create_main_panel(self.main_content_container)
            # Store references to the created widgets
            self.main_content_frame = widgets["main_frame"]
            self.input_textbox = widgets["input_textbox"]
            self.output_textbox = widgets["output_textbox"]
            self.button_frame = widgets["button_frame"]
            self.submit_button = widgets["submit_button"]
            self.stop_button = widgets["stop_button"]
            self.play_history_button = widgets["play_history_button"]
            self.settings_button = widgets["settings_button"]
            self.tts_checkbox = widgets["tts_checkbox"]
            self.speak_input_checkbox = widgets["speak_input_checkbox"]
            self.status_label = widgets["status_label"]
        except ImportError:
            # Fallback: Define main panel widgets directly if ui_components missing
            print("WARN: ui_components.py not found, defining main panel widgets directly.")
            self.main_content_frame = customtkinter.CTkFrame(master=self.main_content_container, fg_color="transparent"); self.main_content_frame.pack(fill="both", expand=True)
            self.main_content_frame.grid_columnconfigure(0, weight=1); self.main_content_frame.grid_rowconfigure(0, weight=1); self.main_content_frame.grid_rowconfigure(1, weight=3); self.main_content_frame.grid_rowconfigure(2, weight=0); self.main_content_frame.grid_rowconfigure(3, weight=0)
            self.input_textbox = customtkinter.CTkTextbox(self.main_content_frame, height=100); self.input_textbox.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew"); self.input_textbox.insert("0.0", "Enter your text here...")
            self.output_textbox = customtkinter.CTkTextbox(self.main_content_frame, state="disabled"); self.output_textbox.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
            self.button_frame = customtkinter.CTkFrame(self.main_content_frame, fg_color="transparent"); self.button_frame.grid(row=2, column=0, padx=10, pady=(5,0), sticky="ew")
            self.button_frame.grid_columnconfigure(0, weight=1); self.button_frame.grid_columnconfigure(1, weight=1); self.button_frame.grid_rowconfigure(0, weight=0); self.button_frame.grid_rowconfigure(1, weight=0); self.button_frame.grid_rowconfigure(2, weight=0)
            self.submit_button = customtkinter.CTkButton(self.button_frame, text="Generate & Speak"); self.submit_button.grid(row=0, column=0, padx=(0,5), pady=(2,2), sticky="ew")
            self.stop_button = customtkinter.CTkButton(self.button_frame, text="Stop Playback", state="disabled", fg_color="firebrick", hover_color="darkred"); self.stop_button.grid(row=0, column=1, padx=(5,0), pady=(2,2), sticky="ew")
            self.play_history_button = customtkinter.CTkButton(self.button_frame, text="Play Selected Audio", state="disabled"); self.play_history_button.grid(row=1, column=0, padx=(0,5), pady=(2,2), sticky="ew")
            self.settings_button = customtkinter.CTkButton(self.button_frame, text="Settings"); self.settings_button.grid(row=1, column=1, padx=(5,0), pady=(2,2), sticky="ew")
            self.tts_checkbox = customtkinter.CTkCheckBox(self.button_frame, text="Enable Speech Output"); self.tts_checkbox.grid(row=2, column=0, padx=(5,10), pady=(5,5), sticky="w")
            self.speak_input_checkbox = customtkinter.CTkCheckBox(self.button_frame, text="Speak My Input"); self.speak_input_checkbox.grid(row=2, column=1, padx=(10,5), pady=(5,5), sticky="w")
            self.status_label = customtkinter.CTkLabel(self.main_content_frame, text="Status: Ready", anchor="w"); self.status_label.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")


        # --- Assign Commands/Bindings AFTER widgets are created ---
        self.input_textbox.bind("<Control-Return>", self.handle_ctrl_enter)
        self.submit_button.configure(command=self.start_processing_thread)
        self.stop_button.configure(command=self.stop_playback)
        self.play_history_button.configure(command=self.play_selected_history)
        self.settings_button.configure(command=self.open_settings_window)
        self.tts_checkbox.configure(command=self.toggle_tts)
        self.speak_input_checkbox.configure(command=self.toggle_speak_input)

        # --- Set initial checkbox states correctly --- ## SYNTAX FIX HERE ##
        # Use standard multi-line if/else
        if self.tts_enabled:
            self.tts_checkbox.select()
        else:
            self.tts_checkbox.deselect()

        if self.speak_input_enabled:
            self.speak_input_checkbox.select()
        else:
            self.speak_input_checkbox.deselect()

    def fetch_models_startup(self):
        """Fetches available chat models once during startup."""
        print("Attempting to fetch OpenAI models at startup...")
        try:
            current_key = os.getenv("OPENAI_API_KEY")
            if current_key:
                # Create temporary client instance JUST for listing models
                # Consider making self.client an instance variable initialized here if key exists
                temp_client = OpenAI(api_key=current_key)
                fetched_list = api_handler.get_available_chat_models(temp_client)
                if fetched_list:
                    self.available_models = fetched_list # Store fetched list
                    print(f"Successfully fetched models: {len(self.available_models)} found.")
                else:
                     print("WARN: Fetched model list was empty, using default list.")
                     self.available_models = api_handler.DEFAULT_CHAT_MODELS
            else:
                print("WARN: No API key configured, cannot fetch model list at startup. Using default list.")
                self.available_models = api_handler.DEFAULT_CHAT_MODELS
        except Exception as e:
             print(f"ERROR fetching model list during startup: {e}. Using default list.")
             self.available_models = api_handler.DEFAULT_CHAT_MODELS


    # --- Settings and Loading Methods ---

    def load_user_settings(self):
        # (Keep implementation from previous step - loads key, mode, model, voice)
        # ... no changes needed here ...
        self.current_api_key_display = ""; loaded_mode = "System"; loaded_chat_model = config.DEFAULT_CHAT_MODEL; loaded_tts_voice = config.DEFAULT_TTS_VOICE; loaded_tts_speed = config.DEFAULT_TTS_SPEED; key_loaded_from_settings = False; settings_file_path = self.user_settings_file
        if settings_file_path.exists():
            print(f"DEBUG: Found settings file: {settings_file_path}")
            try:
                with open(settings_file_path, "r", encoding="utf-8") as f: settings_data = json.load(f)
                print(f"DEBUG: Loaded settings data: {settings_data}")
                loaded_key = settings_data.get("openai_api_key");
                if loaded_key and isinstance(loaded_key, str) and loaded_key.startswith("sk-"): os.environ['OPENAI_API_KEY'] = loaded_key; self.current_api_key_display = loaded_key; key_loaded_from_settings = True; print("DEBUG: Loaded API key from settings.")
                loaded_mode_setting = settings_data.get("appearance_mode");
                if loaded_mode_setting in ["Light", "Dark", "System"]: loaded_mode = loaded_mode_setting; print(f"DEBUG: Loaded appearance mode preference: '{loaded_mode}'")
                loaded_model_setting = settings_data.get("chat_model");
                if loaded_model_setting and isinstance(loaded_model_setting, str): loaded_chat_model = loaded_model_setting; print(f"DEBUG: Loaded chat model preference: '{loaded_chat_model}'")
                loaded_voice_setting = settings_data.get("tts_voice");
                if loaded_voice_setting and loaded_voice_setting in TTS_VOICES: loaded_tts_voice = loaded_voice_setting; print(f"DEBUG: Loaded tts voice preference: '{loaded_tts_voice}'")
                loaded_speed_setting = settings_data.get("tts_speed");
                if isinstance(loaded_speed_setting, (float, int)) and 0.25 <= loaded_speed_setting <= 4.0: loaded_tts_speed = float(loaded_speed_setting); print(f"DEBUG: Loaded tts speed preference: {loaded_tts_speed}")
            except Exception as e: print(f"Error loading user settings file {settings_file_path}: {e}"); loaded_mode = "System"; loaded_chat_model = config.DEFAULT_CHAT_MODEL; loaded_tts_voice = config.DEFAULT_TTS_VOICE; loaded_tts_speed = config.DEFAULT_TTS_SPEED
        else: print(f"DEBUG: Settings file not found: {settings_file_path}")
        if not key_loaded_from_settings:
             env_key = os.getenv('OPENAI_API_KEY');
             if env_key: self.current_api_key_display = env_key; print("DEBUG: Using API key from environment.")
             else: print("WARN: OpenAI API key not found anywhere."); self.current_api_key_display = ""
        self.current_appearance_mode = loaded_mode; self.current_chat_model = loaded_chat_model; self.current_tts_voice = loaded_tts_voice; self.current_tts_speed = loaded_tts_speed
        print(f"DEBUG: Startup mode: {self.current_appearance_mode}, model: {self.current_chat_model}, voice: {self.current_tts_voice}, speed: {self.current_tts_speed}")


    def open_settings_window(self):
        """Opens the settings window, passing the pre-fetched model list."""
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.focus()
        else:
            # Pass the stored model list to the SettingsWindow constructor
            self.settings_window = SettingsWindow(
                master_app=self,
                model_list=self.available_models # Pass the fetched list
            )

    # --- Callback methods for SettingsWindow ---
    # (Keep update_and_save_settings, apply_app_theme, settings_window_closed)
    # ... Methods from previous step ...
    def update_and_save_settings(self, api_key, appearance_mode, chat_model, tts_voice, tts_speed) -> bool:
        print(f"DEBUG: Main app received settings: mode={appearance_mode}, model={chat_model}, voice={tts_voice}, speed={tts_speed}")
        self.current_appearance_mode = appearance_mode; self.current_chat_model = chat_model; self.current_tts_voice = tts_voice; self.current_tts_speed = tts_speed
        key_warning = "";
        if api_key and not api_key.startswith("sk-"): key_warning = "Warning: Key might be invalid. "
        settings_data = {"appearance_mode": self.current_appearance_mode, "chat_model": self.current_chat_model, "tts_voice": self.current_tts_voice, "tts_speed": self.current_tts_speed}
        if api_key: settings_data["openai_api_key"] = api_key
        try:
            self.user_settings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.user_settings_file, "w", encoding="utf-8") as f: json.dump(settings_data, f, indent=4)
            key_saved_message = ""
            if api_key and api_key.startswith("sk-"): os.environ['OPENAI_API_KEY'] = api_key; self.current_api_key_display = api_key; key_saved_message = "API Key Saved. "; print("Saved new API key.")
            elif not api_key: self.current_api_key_display = "";
            if 'OPENAI_API_KEY' in os.environ and not api_key: del os.environ['OPENAI_API_KEY']; key_saved_message = "API Key Cleared. "; print("API key cleared in settings & os.environ.")
            print(f"Saved settings: mode='{self.current_appearance_mode}', model='{self.current_chat_model}', voice='{self.current_tts_voice}', speed={self.current_tts_speed}")
            return True
        except Exception as e: print(f"Error saving user settings from main app: {e}"); return False
    def apply_app_theme(self, mode): print(f"DEBUG: Main app applying theme: {mode}"); self.current_appearance_mode = mode; theme_manager.apply_theme(self, mode)
    def settings_window_closed(self): print("DEBUG: Main app notified that settings window closed."); self.settings_window = None


    # --- UI Update & Control Methods ---
    # (Keep toggle_tts, toggle_speak_input, handle_ctrl_enter)
    # (Keep update_status, update_output_textbox, set_ui_state, set_stop_button_state)
    # (Keep _safe_ui_update helper method)
    # ... Methods from previous versions ...
    def toggle_tts(self): self.tts_enabled = bool(self.tts_checkbox.get()); print(f"TTS: {self.tts_enabled}")
    def toggle_speak_input(self): self.speak_input_enabled = bool(self.speak_input_checkbox.get()); print(f"SpeakInput: {self.speak_input_enabled}")
    def handle_ctrl_enter(self, event): print("Ctrl+Enter"); self.start_processing_thread(); return "break"
    def update_status(self, message): self._safe_ui_update(self.status_label, configure_options={"text": f"Status: {message}"})
    def update_output_textbox(self, text): self._safe_ui_update(self.output_textbox, configure_options={"state": "normal"}, insert_text=text, final_configure_options={"state": "disabled"})
    def set_ui_state(self, processing: bool): submit_state = "disabled" if processing else "normal"; input_state = "disabled" if processing else "normal"; self._safe_ui_update(self.submit_button, configure_options={"state": submit_state}); self._safe_ui_update(self.input_textbox, configure_options={"state": input_state})
    def set_stop_button_state(self, enabled: bool): state = "normal" if enabled else "disabled"; self._safe_ui_update(self.stop_button, configure_options={"state": state})
    def _safe_ui_update(self, widget, configure_options={}, insert_text=None, final_configure_options=None):
        def _update():
            if self._is_shutting_down.is_set(): return
            widget_ref = getattr(self, widget_name, None)
            if widget_ref is not None and widget_ref.winfo_exists():
                if configure_options: widget_ref.configure(**configure_options)
                if insert_text is not None: widget_ref.delete("0.0", "end"); widget_ref.insert("0.0", insert_text or "")
                if final_configure_options: widget_ref.configure(**final_configure_options)
            else: print(f"DEBUG: Widget '{widget_name}' no longer exists, skipping update.")
        widget_name = "UnknownWidget";
        for name, value in self.__dict__.items():
             if value is widget: widget_name = name; break
        if threading.current_thread() is not threading.main_thread(): self.after(0, _update)
        else: _update()


    # --- History Methods ---
    # (Keep update_history_display, load_history_item)
    # ... Methods from previous versions ...
    def update_history_display(self):
        if self._is_shutting_down.is_set(): return
        if not hasattr(self, 'history_frame') or not self.history_frame.winfo_exists(): return
        for widget in self.history_frame.winfo_children(): widget.destroy()
        if not isinstance(self.history, list): self.history = []
        for i, item in enumerate(self.history):
             if isinstance(item, (list, tuple)) and len(item) >= 2:
                 prompt, response = item[0], item[1]; timestamp = item[2] if len(item) > 2 else None
                 display_prompt = (prompt[:35] + '...') if len(prompt) > 38 else prompt
                 history_button = customtkinter.CTkButton(self.history_frame, text=display_prompt.replace("\n", " "), anchor="w", command=lambda p=prompt, r=response, ts=timestamp: self.load_history_item(p, r, ts))
                 history_button.grid(row=i, column=0, padx=5, pady=3, sticky="ew")
             else: print(f"Warning: Skipping invalid history item at index {i}: {item}")
    def load_history_item(self, prompt, response, timestamp):
        if self._is_shutting_down.is_set(): return
        if self.processing_thread and self.processing_thread.is_alive(): self.update_status("Error: Cannot load history while processing."); return
        if hasattr(self, 'input_textbox') and self.input_textbox.winfo_exists(): self.input_textbox.configure(state="normal"); self.input_textbox.delete("0.0", "end"); self.input_textbox.insert("0.0", prompt)
        self.update_output_textbox(response)
        self.selected_history_timestamp = None; play_button_state = "disabled"; status_msg = "Loaded item. "
        if timestamp:
            audio_path = config.RESPONSES_DIR / f"response_{timestamp}.mp3"
            if audio_path.exists(): self.selected_history_timestamp = timestamp; play_button_state = "normal"; status_msg += "Audio available."
            else: status_msg += "Audio file missing."
        else: status_msg += "No audio recorded for this entry."
        self.update_status(status_msg)
        if hasattr(self, 'play_history_button') and self.play_history_button.winfo_exists(): self.play_history_button.configure(state=play_button_state)


    # --- Playback Methods ---
    # (Keep play_selected_history, _start_playback_thread, _execute_playback_and_reenable)
    # (Keep _play_audio_blocking using Pygame Sound + delay)
    # (Keep stop_playback using Pygame Sound)
    # ... Methods from previous versions ...
    def play_selected_history(self):
        if self._is_shutting_down.is_set(): return
        if not self.selected_history_timestamp: self.update_status("Error: No history item with audio selected."); return
        if self.processing_thread and self.processing_thread.is_alive(): self.update_status("Error: Cannot play history while processing."); return
        if self.is_playing: self.update_status("Error: Already playing audio."); return
        audio_path = config.RESPONSES_DIR / f"response_{self.selected_history_timestamp}.mp3"
        if not audio_path.exists(): self.update_status(f"Error: Audio file not found: {audio_path.name}"); self._safe_ui_update(self.play_history_button, {"state": "disabled"}); self.selected_history_timestamp = None; return
        self._safe_ui_update(self.play_history_button, {"state": "disabled"}); self._start_playback_thread(str(audio_path), "Playing history audio...")
    def _start_playback_thread(self, audio_path_str: str, status_playing: str):
        if self._is_shutting_down.is_set(): return
        if not self.player.initialized: self.update_status("Error: Audio player not initialized."); self._safe_reenable_play_history_button_after_thread(); return
        playback_thread = threading.Thread(target=self._execute_playback_and_reenable, args=(audio_path_str, status_playing), daemon=True); playback_thread.start()
    def _execute_playback_and_reenable(self, audio_path_str: str, status_playing: str):
        playback_completed_naturally = False
        try:
            if self._is_shutting_down.is_set(): return
            playback_completed_naturally = self._play_audio_blocking(audio_path_str, status_playing)
            if self._is_shutting_down.is_set(): return
        finally: self.after(0, self._safe_reenable_play_history_button_after_thread)
        current_status = "";
        if hasattr(self, 'status_label') and self.status_label.winfo_exists(): current_status = self.status_label.cget("text")
        if "Error" not in current_status and "stopped" not in current_status and "finished" not in current_status: self.after(100, lambda: self.update_status("Ready"))
    def _safe_reenable_play_history_button_after_thread(self):
        if self._is_shutting_down.is_set(): return
        if not hasattr(self, 'play_history_button') or not self.play_history_button.winfo_exists(): return
        current_selected_ts = self.selected_history_timestamp; new_state = "disabled"
        if current_selected_ts and (config.RESPONSES_DIR / f"response_{current_selected_ts}.mp3").exists(): new_state = "normal"
        self.play_history_button.configure(state=new_state)
    def _play_audio_blocking(self, audio_path_str: str, status_playing: str = "Playing audio...") -> bool:
        # (Keep implementation using Pygame Sound + delay)
        print(f"DEBUG: _play_audio_blocking started for path: {audio_path_str}");
        if self._is_shutting_down.is_set(): return False
        if not audio_path_str or not self.player.initialized: return False
        natural_finish = False
        try:
            if self._is_shutting_down.is_set(): return False
            self.after(0, lambda: self.update_status("Loading audio..."))
            playback_started = self.player.play_sound(audio_path_str) # Assumes this loads + plays + includes delay
            if not playback_started: raise RuntimeError(f"AudioPlayer failed to start playback for {audio_path_str}")
            if self._is_shutting_down.is_set(): self.player.stop(); return False
            self.is_playing = True; self.set_stop_button_state(enabled=True); self.update_status(status_playing)
            print(f"DEBUG: _play_audio_blocking: Playback started. Entering wait loop.")
            while self.player.is_busy() and self.is_playing:
                if self._is_shutting_down.is_set(): print("DEBUG: Shutdown detected during playback loop."); self.player.stop(); self.is_playing = False; break
                time.sleep(0.1)
            print(f"DEBUG: _play_audio_blocking: Exited wait loop. is_playing={self.is_playing}")
            if self.is_playing: print("DEBUG: Playback finished naturally."); self.update_status("Playback finished."); self.is_playing = False; natural_finish = True
        except Exception as e: print(f"DEBUG: _play_audio_blocking - Error during playback section: {e}"); self.update_status(f"Error during playback: {e}"); self.is_playing = False; self.player.stop()
        finally: print("DEBUG: _play_audio_blocking: finally block."); self.player.stop(); self.set_stop_button_state(enabled=False)
        print(f"DEBUG: _play_audio_blocking finished. Returning: {natural_finish}")
        return natural_finish
    def stop_playback(self):
        # (Keep implementation using Pygame Sound player stop)
        if self.is_playing: print("Stop playback requested."); self.is_playing = False; self.player.stop(); self.update_status("Playback stopped."); self.set_stop_button_state(enabled=False)
        else: print("DEBUG: Stop requested but not currently playing.")


    # --- Core Logic and Threading ---

    def start_processing_thread(self):
        # (Keep implementation)
        if self._is_shutting_down.is_set(): return
        user_prompt = self.input_textbox.get("0.0", "end-1c").strip()
        if not user_prompt or user_prompt == "Enter your text here...": self.update_status("Error: Please enter some text."); return
        if self.processing_thread and self.processing_thread.is_alive(): self.update_status("Error: Processing already in progress."); return
        self.set_ui_state(processing=True); self.update_status("Processing..."); self.update_output_textbox("")
        self.processing_thread = threading.Thread(target=self.process_request_in_background, args=(user_prompt,), daemon=True); self.processing_thread.start()

    def process_request_in_background(self, prompt):
        """Handles background processing logic, using the selected chat model and TTS voice/speed."""
        # (Keep implementation from previous step, ensuring it passes self.current_tts_voice AND self.current_tts_speed to generate_speech)
        client = None; generated_text = None; playback_completed_naturally = True; timestamp_for_history = None
        try:
            if self._is_shutting_down.is_set(): return
            print("DEBUG: Background thread started."); client = OpenAI();
            if not client.api_key: raise ValueError("OpenAI API key missing.")
            print("DEBUG: OpenAI client initialized.")
            if self.speak_input_enabled: # Path 1: Speak Input ONLY
                 if self._is_shutting_down.is_set(): return
                 self.update_status("Generating speech for input..."); prompt_audio_path_str = None; audio_generated = False
                 timestamp_for_history = datetime.now().strftime("%Y%m%d_%H%M%S"); output_filename = config.RESPONSES_DIR / f"response_{timestamp_for_history}.mp3"; print(f"DEBUG: Input TTS - Target output file: {output_filename}")
                 try:
                     # --- Use selected voice AND speed --- ## CHECKED ##
                     api_handler.generate_speech(client, prompt, output_filename,
                                                 config.DEFAULT_TTS_MODEL,
                                                 self.current_tts_voice, # Pass voice
                                                 self.current_tts_speed) # Pass speed
                     prompt_audio_path_str = str(output_filename); audio_generated = True; print(f"DEBUG: Input TTS - API call succeeded for {prompt_audio_path_str}")
                 except (ConnectionError, RuntimeError, Exception) as prompt_tts_error: print(f"DEBUG: Input TTS - ERROR during generation: {prompt_tts_error}"); self.update_status(f"Error generating prompt audio: {prompt_tts_error}"); timestamp_for_history = None
                 if audio_generated and prompt_audio_path_str:
                     if self._is_shutting_down.is_set(): return
                     print("DEBUG: Input TTS - Generation succeeded."); playback_completed_naturally = self._play_audio_blocking(prompt_audio_path_str, status_playing="Speaking input..."); print(f"DEBUG: Input TTS - Playback finished. Completed naturally: {playback_completed_naturally}")
                 elif not audio_generated: print("DEBUG: Input TTS - Generation failed.")
                 if self._is_shutting_down.is_set(): return
                 print(f"DEBUG: Adding input-only history. Timestamp: {timestamp_for_history}"); placeholder_response = "(Input Spoken - No AI Response)"; self.history.insert(0, (prompt, placeholder_response, timestamp_for_history)); self.after(0, self.update_history_display)
                 final_status = "Ready";
                 if not audio_generated: final_status = "Ready (Input audio generation failed)."
                 elif playback_completed_naturally: final_status = "Ready (Input spoken)."
                 else: final_status = "Ready (Input speech stopped)."
                 self.update_status(final_status); print("DEBUG: Input TTS path finished."); return
            else: # Path 2: Get AI Response
                 if self._is_shutting_down.is_set(): return
                 self.update_status("Generating AI response.")
                 # --- Use selected chat model --- (Keep this)
                 generated_text = api_handler.get_chat_response(client, prompt, self.current_chat_model)
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
                     try:
                         print(f"DEBUG: Response TTS - Attempting generation for file: {output_filename}")
                         # --- Use selected voice AND speed --- ## CHECKED ##
                         api_handler.generate_speech(client, generated_text, output_filename,
                                                     config.DEFAULT_TTS_MODEL,
                                                     self.current_tts_voice, # Pass voice
                                                     self.current_tts_speed) # Pass speed
                         response_audio_path = str(output_filename); response_audio_generated = True; print(f"DEBUG: Response TTS - API call succeeded for {output_filename}")
                     except (ConnectionError, RuntimeError, Exception) as response_tts_error: print(f"DEBUG: Response TTS - ERROR during generation: {response_tts_error}"); self.update_status(f"Error generating response audio: {response_tts_error}")
                     if response_audio_generated:
                         if self._is_shutting_down.is_set(): return
                         print("DEBUG: Response TTS - Generation succeeded."); playback_completed_naturally = self._play_audio_blocking(response_audio_path, status_playing="Playing response..."); print(f"DEBUG: Response TTS - Playback finished. Completed naturally: {playback_completed_naturally}")
                         if self._is_shutting_down.is_set(): return
                         print("DEBUG: Response TTS - Initiating cleanup."); cleanup_old_recordings(config.RESPONSES_DIR, config.MAX_RECORDINGS)
                         if playback_completed_naturally: self.update_status("Ready")
                     else: print("DEBUG: Response TTS - Generation failed."); self.update_status("Ready (Response audio generation failed).")
                 elif self.tts_enabled and not timestamp_for_history: print("DEBUG: Warning - TTS enabled but no timestamp captured."); self.update_status("Ready (Internal history timestamp error).")
                 else: print("DEBUG: Response TTS is disabled."); self.update_status("Ready (Speech disabled).")
        except (ValueError, ConnectionError, RuntimeError, Exception) as e: error_msg_thread = f"Error: {e}"; print(error_msg_thread); final_text = generated_text or f"Error: {e}"; self.after(0, lambda: self.update_output_textbox(final_text)); self.update_status(f"Error: {e}"); self.is_playing = False
        finally: self.after(0, self._safe_reenable_ui_after_thread)


    # --- Closing Method ---
    def on_closing(self):
        # (Keep implementation from previous step)
        print("Closing application..."); self._is_shutting_down.set()
        if self.is_playing: print("Stopping active playback..."); self.player.stop(); self.is_playing = False
        print("Saving history..."); save_history(self.history_file, self.history)
        print("Quitting audio player..."); self.player.quit()
        print("Destroying main window..."); self.destroy()

    # --- Safe UI Re-enable Helper ---
    def _safe_reenable_ui_after_thread(self):
         # (Keep implementation from previous step)
         if self._is_shutting_down.is_set(): return
         if not self.winfo_exists(): return
         print("DEBUG: Background thread finished cleanly. Re-enabling UI.")
         self.set_ui_state(processing=False);
         if self.is_playing: self.is_playing = False
         self.set_stop_button_state(enabled=False)
