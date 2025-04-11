# theme_manager.py
import customtkinter
import traceback

# --- Define Theme Colors ---
DARK_BG_MAIN = "#2B2B2B"
DARK_BG_INPUT = "#2B2B2B"
DARK_TEXT_PRIMARY = "#DCE4EE" # Use this for labels too

# Define explicit default light theme colors for resetting
LIGHT_WINDOW_BG = "#E5E5E5"
LIGHT_FRAME_BG = "#DBDBDB"
LIGHT_INPUT_BG = "#F9F9FA"
LIGHT_TEXT_COLOR = "#1F1F1F" # Use this for labels too

def _apply_manual_dark_overrides(app_instance):
    """Applies manual dark theme overrides to selected widgets."""
    try:
        print("DEBUG: Applying manual dark OVERRIDES via theme_manager...")
        # Backgrounds
        if hasattr(app_instance, 'configure'): app_instance.configure(fg_color=DARK_BG_MAIN)
        if hasattr(app_instance, 'main_content_frame'): app_instance.main_content_frame.configure(fg_color=DARK_BG_MAIN)
        if hasattr(app_instance, 'history_frame'): app_instance.history_frame.configure(fg_color=DARK_BG_MAIN)

        # Input Textbox
        if hasattr(app_instance, 'input_textbox'): app_instance.input_textbox.configure(fg_color=DARK_BG_INPUT, text_color=DARK_TEXT_PRIMARY)

        # Labels
        if hasattr(app_instance, 'history_frame'):
            # --- CORRECT WAY to change history label color ---
            app_instance.history_frame.configure(label_text_color=DARK_TEXT_PRIMARY)
            print(f"DEBUG: Set history_frame label_text_color.")
            # --- Remove old way: ---
            # try: app_instance.history_frame._label.configure(text_color=DARK_TEXT_PRIMARY)
            # except AttributeError: pass

        if hasattr(app_instance, 'status_label'):
            app_instance.status_label.configure(text_color=DARK_TEXT_PRIMARY)
            print(f"DEBUG: Set status_label color.")

        # Checkboxes
        checkbox_text_applied = False
        if hasattr(app_instance, 'tts_checkbox'):
            app_instance.tts_checkbox.configure(text_color=DARK_TEXT_PRIMARY)
            checkbox_text_applied = True
        if hasattr(app_instance, 'speak_input_checkbox'):
            app_instance.speak_input_checkbox.configure(text_color=DARK_TEXT_PRIMARY)
            checkbox_text_applied = True
        if checkbox_text_applied:
             print(f"DEBUG: Set checkbox text color.")

        print("DEBUG: Skipping manual styling for Buttons.")
    except Exception as e:
        print(f"Error applying manual dark overrides: {e}")
        # traceback.print_exc()

def _reset_manual_overrides(app_instance):
    """Resets manually styled widgets to explicit light theme default colors."""
    try:
        print("DEBUG: Resetting manual OVERRIDES to HARDCODED light colors via theme_manager...")

        # Backgrounds
        if hasattr(app_instance, 'configure'): app_instance.configure(fg_color=LIGHT_WINDOW_BG)
        if hasattr(app_instance, 'main_content_frame'): app_instance.main_content_frame.configure(fg_color="transparent")
        if hasattr(app_instance, 'history_frame'): app_instance.history_frame.configure(fg_color=LIGHT_FRAME_BG)

        # Input Textbox
        if hasattr(app_instance, 'input_textbox'):
             app_instance.input_textbox.configure(fg_color=LIGHT_INPUT_BG, text_color=LIGHT_TEXT_COLOR)

        # Labels
        if hasattr(app_instance, 'history_frame'):
            # --- CORRECT WAY to reset history label color ---
            app_instance.history_frame.configure(label_text_color=LIGHT_TEXT_COLOR) # Use light text default
            print(f"DEBUG: Reset history_frame label_text_color.")

        if hasattr(app_instance, 'status_label'):
            app_instance.status_label.configure(text_color=LIGHT_TEXT_COLOR) # Use light text default
            print(f"DEBUG: Reset status_label color.")

        # Checkboxes
        checkbox_text_reset = False
        if hasattr(app_instance, 'tts_checkbox'):
            app_instance.tts_checkbox.configure(text_color=LIGHT_TEXT_COLOR)
            checkbox_text_reset = True
        if hasattr(app_instance, 'speak_input_checkbox'):
            app_instance.speak_input_checkbox.configure(text_color=LIGHT_TEXT_COLOR)
            checkbox_text_reset = True
        if checkbox_text_reset:
             print(f"DEBUG: Reset checkbox text color.")

        print("DEBUG: Manual overrides reset.")

    except Exception as e:
        print(f"Error resetting manual overrides: {e}")
        # traceback.print_exc()


def apply_theme(app_instance, mode: str):
    """
    Applies the global theme ('Light', 'Dark', 'System') and handles
    manual overrides when 'Dark' is selected.
    """
    # (This function's logic remains the same)
    print(f"DEBUG: theme_manager applying theme: {mode}")
    try:
        if mode == "Dark":
            customtkinter.set_appearance_mode("Light") # Set base theme
            _apply_manual_dark_overrides(app_instance) # Apply overrides
        elif mode == "Light":
            customtkinter.set_appearance_mode("Light")
            _reset_manual_overrides(app_instance) # Reset overrides
        else: # System mode
            if mode != "System": print(f"WARN: Invalid mode '{mode}' received, defaulting to System.")
            customtkinter.set_appearance_mode("System")
            _reset_manual_overrides(app_instance) # Reset overrides

        if hasattr(app_instance, 'current_appearance_mode'):
             app_instance.current_appearance_mode = mode
    except Exception as e:
        print(f"Error applying theme mode '{mode}': {e}")
        try: # Fallback safely
             print("Attempting fallback to System theme.")
             customtkinter.set_appearance_mode("System")
             _reset_manual_overrides(app_instance)
             if hasattr(app_instance, 'current_appearance_mode'): app_instance.current_appearance_mode = "System"
        except Exception as fallback_e: print(f"Error applying fallback System theme: {fallback_e}")