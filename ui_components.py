# ui_components.py
# Functions to create parts of the main application UI

import customtkinter
import tkinter as tk

def create_history_panel(master_container):
    """
    Creates the widgets for the history panel.

    Args:
        master_container (tk.Frame): The parent tk.Frame widget.

    Returns:
        tuple: (history_title_label, history_frame)
    """
    # Configure grid inside container
    master_container.grid_rowconfigure(0, weight=0) # Title Label row
    master_container.grid_rowconfigure(1, weight=1) # Scrollable Frame row
    master_container.grid_columnconfigure(0, weight=1)

    # 1. Create the separate "History" Title Label
    history_title_label = customtkinter.CTkLabel(
        master=master_container, # Parent is the tk Frame container
        text="History",
        font=customtkinter.CTkFont(weight="bold") # Make font bold like default
    )
    history_title_label.grid(row=0, column=0, padx=10, pady=(5, 5), sticky="ew") # Place at top

    # 2. Create the Scrollable Frame WITHOUT the label_text argument
    history_frame = customtkinter.CTkScrollableFrame(
        master=master_container,  # Parent is the tk Frame container
        fg_color="transparent"    # Make its own background transparent initially
    )
    history_frame.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="nsew") # Place below label
    history_frame.grid_columnconfigure(0, weight=1) # Allow buttons inside to expand width

    return history_title_label, history_frame


def create_main_panel(master_container):
    """
    Creates the widgets for the main interaction panel.

    Args:
        master_container (tk.Frame): The parent tk.Frame widget.

    Returns:
        dict: A dictionary containing references to the created widgets.
              Keys: 'main_frame', 'input_textbox', 'output_textbox',
                    'button_frame', 'submit_button', 'stop_button',
                    'play_history_button', 'settings_button',
                    'tts_checkbox', 'speak_input_checkbox', 'status_label'
    """
    # Main CTkFrame inside the container
    main_content_frame = customtkinter.CTkFrame(
        master=master_container, fg_color="transparent"
    )
    main_content_frame.pack(fill="both", expand=True) # Fill the tk container

    # --- Configure Grid Layout *INSIDE* main_content_frame ---
    main_content_frame.grid_columnconfigure(0, weight=1) # Single column
    main_content_frame.grid_rowconfigure(0, weight=1) # Input row weight
    main_content_frame.grid_rowconfigure(1, weight=3) # Output row weight (larger)
    main_content_frame.grid_rowconfigure(2, weight=0) # Button frame row weight
    main_content_frame.grid_rowconfigure(3, weight=0) # Status label row weight

    # --- Widgets INSIDE main_content_frame ---

    # Input Textbox (Row 0)
    input_textbox = customtkinter.CTkTextbox(main_content_frame, height=100)
    input_textbox.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")
    input_textbox.insert("0.0", "Enter your text here...")

    # Output Textbox (Row 1)
    output_textbox = customtkinter.CTkTextbox(main_content_frame, state="disabled")
    output_textbox.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

    # Button Frame (Row 2)
    button_frame = customtkinter.CTkFrame(main_content_frame, fg_color="transparent")
    button_frame.grid(row=2, column=0, padx=10, pady=(5,0), sticky="ew")
    # Configure button_frame grid (2 cols, 3 rows)
    button_frame.grid_columnconfigure(0, weight=1)
    button_frame.grid_columnconfigure(1, weight=1)
    button_frame.grid_rowconfigure(0, weight=0) # Gen/Stop
    button_frame.grid_rowconfigure(1, weight=0) # Play History/Settings
    button_frame.grid_rowconfigure(2, weight=0) # Checkboxes

    # Buttons (Rows 0, 1)
    submit_button = customtkinter.CTkButton(button_frame, text="Generate & Speak") # Command set later
    submit_button.grid(row=0, column=0, padx=(0,5), pady=(2,2), sticky="ew")
    stop_button = customtkinter.CTkButton(button_frame, text="Stop Playback", state="disabled", fg_color="firebrick", hover_color="darkred") # Command set later
    stop_button.grid(row=0, column=1, padx=(5,0), pady=(2,2), sticky="ew")
    play_history_button = customtkinter.CTkButton(button_frame, text="Play Selected Audio", state="disabled") # Command set later
    play_history_button.grid(row=1, column=0, padx=(0,5), pady=(2,2), sticky="ew")
    settings_button = customtkinter.CTkButton(button_frame, text="Settings") # Command set later
    settings_button.grid(row=1, column=1, padx=(5,0), pady=(2,2), sticky="ew")

    # Checkboxes (Row 2)
    tts_checkbox = customtkinter.CTkCheckBox(button_frame, text="Enable Speech Output") # Command set later
    tts_checkbox.grid(row=2, column=0, padx=(5,10), pady=(5,5), sticky="w")
    tts_checkbox.select() # Default ON

    speak_input_checkbox = customtkinter.CTkCheckBox(button_frame, text="Speak My Input") # Command set later
    speak_input_checkbox.grid(row=2, column=1, padx=(10,5), pady=(5,5), sticky="w")
    speak_input_checkbox.deselect() # Default OFF

    # Status Label (Row 3)
    status_label = customtkinter.CTkLabel(main_content_frame, text="Status: Ready", anchor="w")
    status_label.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")

    # Return dictionary of key widgets
    return {
        "main_frame": main_content_frame,
        "input_textbox": input_textbox,
        "output_textbox": output_textbox,
        "button_frame": button_frame,
        "submit_button": submit_button,
        "stop_button": stop_button,
        "play_history_button": play_history_button,
        "settings_button": settings_button,
        "tts_checkbox": tts_checkbox,
        "speak_input_checkbox": speak_input_checkbox,
        "status_label": status_label
    }

