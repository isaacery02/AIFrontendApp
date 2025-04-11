# theme_manager.py
import customtkinter
import traceback

# --- Define Theme Colors ---
DARK_BG_MAIN = "#2B2B2B"
DARK_BG_INPUT = "#2B2B2B"
DARK_TEXT_PRIMARY = "#DCE4EE"
BUTTON_DARK_HOVER = "gray15" # Dark hover for buttons

# --- Define HARDCODED default light theme colors for resetting ---
# Remove the attempt to read from ThemeManager or tk.Frame defaults
print("INFO: Using hardcoded light theme colors for reset.")
LIGHT_WINDOW_BG = "#E5E5E5"
LIGHT_FRAME_BG = "#DBDBDB"
LIGHT_INPUT_BG = "#F9F9FA"
LIGHT_TEXT_COLOR = "#1F1F1F"
LIGHT_BUTTON_FG = "#E0E0E0" # Example light button color
LIGHT_BUTTON_TEXT = "#1F1F1F"
LIGHT_BUTTON_HOVER = "#CACACA"
LIGHT_STOP_BUTTON_HOVER = "#E57373"
LIGHT_TK_FRAME_BG = "#F0F0F0" # Default tk frame color

# --- Helper Functions ---

def _apply_manual_black_white_overrides(app_instance):
    """Applies manual dark theme overrides to selected widgets."""
    # Function definition MUST exist before apply_theme calls it
    try:
        print("DEBUG: Applying manual black/white OVERRIDES via theme_manager...")
        # Backgrounds
        if hasattr(app_instance, 'configure'): app_instance.configure(fg_color=DARK_BG_MAIN)
        if hasattr(app_instance, 'history_container'): app_instance.history_container.configure(bg=DARK_BG_MAIN)
        if hasattr(app_instance, 'main_content_container'): app_instance.main_content_container.configure(bg=DARK_BG_MAIN)
        if hasattr(app_instance, 'main_content_frame'): app_instance.main_content_frame.configure(fg_color=DARK_BG_MAIN)
        if hasattr(app_instance, 'history_frame'): app_instance.history_frame.configure(fg_color=DARK_BG_MAIN)
        if hasattr(app_instance, 'button_frame'): app_instance.button_frame.configure(fg_color=DARK_BG_MAIN)
        # Input Textbox
        if hasattr(app_instance, 'input_textbox'): app_instance.input_textbox.configure(fg_color=DARK_BG_INPUT, text_color=DARK_TEXT_PRIMARY)
        # Labels
        if hasattr(app_instance, 'history_title_label'): app_instance.history_title_label.configure(text_color=DARK_TEXT_PRIMARY)
        if hasattr(app_instance, 'status_label'): app_instance.status_label.configure(text_color=DARK_TEXT_PRIMARY)
        # Checkboxes
        if hasattr(app_instance, 'tts_checkbox'): app_instance.tts_checkbox.configure(text_color=DARK_TEXT_PRIMARY)
        if hasattr(app_instance, 'speak_input_checkbox'): app_instance.speak_input_checkbox.configure(text_color=DARK_TEXT_PRIMARY)
        # Buttons
        button_list = [
            getattr(app_instance, 'submit_button', None),
            getattr(app_instance, 'play_history_button', None),
            getattr(app_instance, 'settings_button', None)
        ]
        for button in button_list:
            if button and isinstance(button, customtkinter.CTkButton):
                 try:
                     button.configure(fg_color=DARK_BG_MAIN, text_color=DARK_TEXT_PRIMARY, hover_color=BUTTON_DARK_HOVER)
                 except Exception as btn_e: print(f"Warn: Failed to configure button {button}: {btn_e}")
        # Style Stop button text/hover only
        if hasattr(app_instance, 'stop_button') and app_instance.stop_button.winfo_exists():
             try: app_instance.stop_button.configure(text_color=DARK_TEXT_PRIMARY, hover_color="maroon") # Darker red hover
             except: pass

        print("DEBUG: Manual dark overrides applied.")
    except Exception as e:
        print(f"Error applying manual dark overrides: {e}")
        # traceback.print_exc()

def _reset_manual_overrides(app_instance):
    """Resets ALL manually styled widgets to explicit light theme default colors."""
    try:
        print("DEBUG: Resetting ALL manual OVERRIDES to default colors via theme_manager...")

        # --- Backgrounds ---
        if hasattr(app_instance, 'configure'): app_instance.configure(fg_color=LIGHT_WINDOW_BG)
        if hasattr(app_instance, 'history_container'): app_instance.history_container.configure(bg=LIGHT_TK_FRAME_BG)
        if hasattr(app_instance, 'main_content_container'): app_instance.main_content_container.configure(bg=LIGHT_TK_FRAME_BG)
        if hasattr(app_instance, 'main_content_frame'): app_instance.main_content_frame.configure(fg_color="transparent")
        if hasattr(app_instance, 'history_frame'): app_instance.history_frame.configure(fg_color=LIGHT_FRAME_BG)
        if hasattr(app_instance, 'button_frame'): app_instance.button_frame.configure(fg_color="transparent")

        # --- Text Widgets ---
        if hasattr(app_instance, 'input_textbox'):
             app_instance.input_textbox.configure(fg_color=LIGHT_INPUT_BG, text_color=LIGHT_TEXT_COLOR)

        # --- Labels ---
        if hasattr(app_instance, 'history_title_label'):
            app_instance.history_title_label.configure(text_color=LIGHT_TEXT_COLOR)
        if hasattr(app_instance, 'status_label'):
            app_instance.status_label.configure(text_color=LIGHT_TEXT_COLOR)

        # --- Checkboxes ---
        if hasattr(app_instance, 'tts_checkbox'):
            app_instance.tts_checkbox.configure(text_color=LIGHT_TEXT_COLOR)
        if hasattr(app_instance, 'speak_input_checkbox'):
            app_instance.speak_input_checkbox.configure(text_color=LIGHT_TEXT_COLOR)

        # --- Buttons ---
        # Reset using explicit light colors now
        print("DEBUG: Attempting to reset Button colors using EXPLICIT light values...")
        button_list = [
            getattr(app_instance, 'submit_button', None),
            getattr(app_instance, 'play_history_button', None),
            getattr(app_instance, 'settings_button', None)
        ]
        for button in button_list:
            if button and isinstance(button, customtkinter.CTkButton):
                try:
                     # Reset fg_color, text_color, hover_color
                     button.configure(fg_color=LIGHT_BUTTON_FG, text_color=LIGHT_BUTTON_TEXT, hover_color=LIGHT_BUTTON_HOVER)
                except Exception as btn_e: print(f"Warn: Failed to reset button {button}: {btn_e}")

        # Reset stop button text/hover only (keep red background)
        if hasattr(app_instance, 'stop_button') and app_instance.stop_button.winfo_exists():
             try:
                  app_instance.stop_button.configure(text_color=LIGHT_BUTTON_TEXT, hover_color=LIGHT_STOP_BUTTON_HOVER) # Use a light hover red
             except Exception as btn_e: print(f"Warn: Failed to reset stop button text/hover: {btn_e}")

        print("DEBUG: Manual overrides reset attempted.")

    except Exception as e:
        print(f"Error resetting manual overrides: {e}")
        # traceback.print_exc()


# --- Main Theme Application Function ---
# Make sure this is defined AFTER the helpers it calls (_apply... and _reset...)
def apply_theme(app_instance, mode: str):
    """
    Applies the global theme ('Light', 'Dark', 'System') and handles
    manual overrides. Calls full reset for Light/System.
    """
    print(f"DEBUG: theme_manager applying theme: {mode}")
    try:
        applied_mode = mode
        if mode == "Dark":
            customtkinter.set_appearance_mode("Light") # Set base theme
            _apply_manual_black_white_overrides(app_instance) # Apply overrides <--- Make sure this function name matches definition
        elif mode == "Light":
            customtkinter.set_appearance_mode("Light")
            _reset_manual_overrides(app_instance) # Call FULL reset
        else: # System mode
            if mode != "System":
                print(f"WARN: Invalid mode '{mode}' received, defaulting to System.")
                applied_mode = "System"
            customtkinter.set_appearance_mode("System")
            _reset_manual_overrides(app_instance) # Call FULL reset

        if hasattr(app_instance, 'current_appearance_mode'):
             app_instance.current_appearance_mode = applied_mode
    except NameError as ne: # Catch specific NameError
         print(f"FATAL NameError applying theme: {ne}. Check function definitions in theme_manager.py")
         traceback.print_exc()
    except Exception as e:
        print(f"Error applying theme mode '{mode}': {e}")
        try: # Fallback safely
             print("Attempting fallback to System theme.")
             customtkinter.set_appearance_mode("System")
             _reset_manual_overrides(app_instance) # Call FULL reset
             if hasattr(app_instance, 'current_appearance_mode'): app_instance.current_appearance_mode = "System"
        except Exception as fallback_e: print(f"Error applying fallback System theme: {fallback_e}")