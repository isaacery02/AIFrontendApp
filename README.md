# AI Chat & Speech Desktop Application

A Python desktop application allowing users to interact with an OpenAI chat model (like GPT-4o-mini, GPT-4, etc.), get text responses, and optionally have both their input and the AI's response converted to speech using OpenAI's Text-to-Speech (TTS) API. Includes persistent history and configurable settings via a GUI built with CustomTkinter.

*(Generated on: Saturday, April 12, 2025 at 12:02 AM BST, Location: United Kingdom)*

## Features

* **AI Chat:** Send text prompts to a selected OpenAI chat model.
* **Text-to-Speech (TTS):**
    * Convert AI text responses to audible speech using selectable OpenAI voices (alloy, echo, fable, onyx, nova, shimmer).
    * Optionally convert the user's input text to speech before sending it to the AI.
    * Generated audio files are saved persistently.
* **Configurable Settings:**
    * Enter/Save OpenAI API Key via a dedicated Settings window.
    * Select the desired OpenAI Chat Model from a dynamically fetched list (with fallbacks).
    * Select the desired OpenAI TTS Voice.
    * Select the desired TTS Generation Speed (affects newly generated audio).
    * Choose Appearance Mode (Light, Dark, System - Dark mode uses manual overrides for stability).
    * Settings are saved persistently in `data/user_settings.json`.
* **Chat History:**
    * View previous prompts and AI responses in a scrollable history panel.
    * Load previous prompts/responses back into the main text areas.
    * Play back the audio associated with previous AI responses or spoken inputs (if saved).
    * History is saved persistently in `data/chat_history.json`.
* **Audio Management:**
    * Saves generated audio responses (and optionally spoken inputs) to `data/responses/`.
    * Automatically cleans up older audio files, keeping only the most recent (default: 10).
    * Includes a "Stop Playback" button.
* **User Interface:**
    * Built with CustomTkinter for a modern look and feel.
    * Adjustable panel width between History and Main area using a draggable divider (via tk.PanedWindow).
    * Keyboard shortcut: Ctrl+Enter in the input box triggers generation.
* **Packaging:** Configured for building a standalone Windows executable using PyInstaller.

## Technology Stack

* **Language:** Python 3.x
* **GUI:** CustomTkinter
* **Audio Playback:** Pygame (`pygame.mixer`)
* **API Interaction:** OpenAI Python Library (`openai`)
* **Configuration:** python-dotenv, JSON
* **Building:** PyInstaller (for Windows executable)
* **Standard Libraries:** tkinter (via CustomTkinter & PanedWindow), threading, time, os, pathlib, json, datetime

## File Structure

chat_to_speech_project/├── .venv/                  # Python Virtual Environment├── data/                   # Runtime data (created automatically)│   ├── responses/          # Saved MP3 audio files│   └── chat_history.json   # Saved conversation history│   └── user_settings.json  # Saved user preferences├── static/                 # (Optional: for images, etc. - not used currently)├── templates/              # (Optional: for web frameworks - not used currently)├── .env                    # REQUIRED: For OpenAI API Key (user must create)├── .gitignore              # Git ignore rules├── requirements.txt        # Python dependencies├── ChatSpeechApp.spec      # PyInstaller build configuration├── silence.wav             # (Optional: If audio priming is used)|├── main.py                 # Main application entry point├── app_gui.py              # Core ChatApp class, GUI orchestration, event handling├── settings_window.py      # Defines the CTkToplevel Settings window class├── ui_components.py        # Functions to create main UI panels/widgets├── config.py               # Configuration constants, path definitions, .env loading├── api_handler.py          # Functions for OpenAI API calls (Chat, TTS, Models)├── audio_player.py         # Class abstracting Pygame audio playback├── history_manager.py      # Functions for loading/saving JSON history├── file_utils.py           # Utility for cleaning up old audio files└── theme_manager.py        # Handles applying appearance modes (including manual overrides)
## Setup and Installation (Running from Source)

1.  **Prerequisites:**
    * Python 3.10 or higher recommended.
    * Git installed.
2.  **Clone Repository:**
    ```bash
    git clone https://github.com/isaacery02/AIFrontendApp.git
    cd chat_to_speech_project
    ```
3.  **Create Virtual Environment:**
    ```bash
    python -m venv .venv
    ```
4.  **Activate Environment:**
    * Windows (CMD/PowerShell): `.venv\Scripts\activate`
    * macOS/Linux (bash/zsh): `source .venv/bin/activate`
5.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
6.  **Create `.env` File:**
    * Create a file named exactly `.env` in the project root (`chat_to_speech_project/`).
    * Add your OpenAI API key to this file:
        ```dotenv
        OPENAI_API_KEY=sk-YourActualOpenAIapiKeyGoesHere
        ```
    * **Note:** Alternatively, set the `OPENAI_API_KEY` as a system environment variable, or enter it via the app's Settings window after first launch (though fetching the model list requires it).

## Running the Application (from Source)

1.  Ensure your virtual environment is activated.
2.  Make sure the `.env` file exists with your API key (or the key is set as an environment variable).
3.  Run the main script:
    ```bash
    python main.py
    ```

## Configuration

* **API Key:** The primary way to set the API key is via the `.env` file or an environment variable. You can also add/change it via the **Settings** window within the application. The key saved via the Settings window (`data/user_settings.json`) takes precedence over the `.env` file or environment variable on subsequent runs.
* **Other Settings:** Appearance mode, Chat Model, TTS Voice, and TTS Speed are configured via the **Settings** window and saved in `data/user_settings.json`.
* **Code Defaults:** Default models, voices, speeds, etc., can be adjusted in `config.py`.

## Building the Executable (Windows using PyInstaller)

1.  **Install PyInstaller:**
    ```bash
    pip install pyinstaller
    ```
2.  **Ensure `silence.wav` exists:** If using the audio priming feature, make sure `silence.wav` is in the project root.
3.  **Check `.spec` File:** Review `ChatSpeechApp.spec`. Ensure the `datas` list in the `Analysis` block includes `('silence.wav', '.')` if using priming. Ensure `icon='your_icon.ico'` is set if you created an icon. Make sure `onefile=False` is set in the `EXE` block for creating a folder distribution (recommended for testing).
4.  **Build:** Run PyInstaller using the spec file from the project root:
    ```bash
    pyinstaller ChatSpeechApp.spec
    ```
5.  **Output:** The distributable application will be inside the `dist/ChatSpeechApp` folder.

## Running the Built Executable (`.exe`)

1.  Navigate into the `dist/ChatSpeechApp` folder.
2.  **Create `.env` File:** Manually create a `.env` file *inside this folder* and add the `OPENAI_API_KEY=...` line with a valid key.
3.  Double-click `ChatSpeechApp.exe` to run.
4.  The application will create a `data` subfolder within `dist/ChatSpeechApp` for its history and audio responses.

## Distributing

1.  Zip the *entire* `dist/ChatSpeechApp` folder.
2.  Send the zip file to your users.
3.  Instruct them to:
    * Unzip the folder.
    * Create a `.env` file inside the unzipped `ChatSpeechApp` folder with their *own* OpenAI API key.
    * Run `ChatSpeechApp.exe`.

## Usage

1.  Launch the application (`python main.py` or `ChatSpeechApp.exe`).
2.  (First Run Recommended) Click "Settings", enter your OpenAI API key, select preferred Model/Voice/Speed/Theme, and click "Save Settings".
3.  Type your prompt into the top text box.
4.  Optionally, check "Speak My Input" to hear your prompt read aloud before sending.
5.  Optionally, uncheck "Enable Speech Output" if you only want the text response from the AI.
6.  Click "Generate & Speak" or press Ctrl+Enter.
7.  The AI response will appear in the bottom text box. If speech output is enabled, it will play automatically.
8.  Previous interactions appear in the "History" panel. Click an item to load the text. If audio was generated for that item, the "Play Selected Audio" button will become active.
9.  Use the "Stop Playback" button to interrupt any currently playing audio.

## Known Issues / Limitations

* **Dark Mode:** The manual "Dark" mode implementation is a workaround to avoid potential crashes. It primarily styles backgrounds and text areas; buttons, checkboxes, scrollbars, and the PanedWindow sash will retain their underlying "Light" theme appearance, leading to visual inconsistencies.
* **Audio Blip:** A small blip or cutoff might occur on the very first audio playback after the application starts or after a long pause, likely due to audio driver/mixer initialization latency. Subsequent playbacks are usually clean.
* **API Key Handling:** Requires users to manage their own OpenAI API key via the `.env` file or Settings window. Key is stored plain-text in `user_settings.json`.
* **Error Handling:** Basic error handling for API calls and file operations exists, but could be more comprehensive.

