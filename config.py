# config.py
import os
import sys # <-- Import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# This will work if a .env file is placed next to the final .exe
load_dotenv()

# --- Helper function to get base path ---
def get_base_path():
    """ Get base path reliably, whether running as script or frozen executable """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in a PyInstaller bundle (esp. --onefile)
        # sys.executable points to the executable itself
        application_path = Path(os.path.dirname(sys.executable))
        print(f"DEBUG (Frozen): Base path determined as: {application_path}")
    else:
        # Running as a normal script
        # __file__ points to this config.py file
        application_path = Path(__file__).parent
        print(f"DEBUG (Script): Base path determined as: {application_path}")
    return application_path

# --- Define Base Data Directory using the helper function ---
# Data will be stored relative to the executable or the script location
APP_BASE_PATH = get_base_path()
APP_BASE_DATA_DIR = APP_BASE_PATH / "data" # Changed from os.getenv default

# --- Derived Paths ---
RESPONSES_DIR = APP_BASE_DATA_DIR / "responses"
HISTORY_FILE = APP_BASE_DATA_DIR / "chat_history.json"

# --- Other Constants ---
MAX_RECORDINGS = 50
DEFAULT_CHAT_MODEL = os.getenv("DEFAULT_CHAT_MODEL", "gpt-4o")
DEFAULT_TTS_MODEL = "tts-1"
DEFAULT_TTS_VOICE = "alloy"

# --- Ensure Directories Exist ---
try:
    APP_BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ensured base data directory exists: {APP_BASE_DATA_DIR}")
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ensured responses directory exists: {RESPONSES_DIR}")
except OSError as e:
    print(f"Warning: Could not create data directories: {e}")

# Note: OPENAI_API_KEY is still expected as an environment variable,
# loaded via load_dotenv() from a .env file next to the executable,
# or set globally on the system.