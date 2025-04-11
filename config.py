# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file for local development (won't exist in typical Docker setup)
# API key should ideally be passed as Docker env var instead.
load_dotenv()

# --- Define Base Data Directory ---
# Use environment variable for Docker, default to '/data' inside container.
# in your environment or .env file.
# Use environment variable for Docker/override, default to './data' for local dev.
APP_BASE_DATA_DIR = Path(os.getenv("APP_DATA_DIR", "./data"))

# --- Derived Paths ---
RESPONSES_DIR = APP_BASE_DATA_DIR / "responses"
HISTORY_FILE = APP_BASE_DATA_DIR / "chat_history.json" # History file inside data dir

# --- Other Constants ---
MAX_RECORDINGS = 10
DEFAULT_CHAT_MODEL = os.getenv("DEFAULT_CHAT_MODEL", "gpt-4o")
DEFAULT_TTS_MODEL = "tts-1"
DEFAULT_TTS_VOICE = "alloy"

# --- Ensure Directories Exist ---
# Create the base data directory and the responses subdirectory at startup
try:
    # Create base data directory first
    APP_BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ensured base data directory exists: {APP_BASE_DATA_DIR}")
    # Then create responses subdirectory
    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ensured responses directory exists: {RESPONSES_DIR}")
except OSError as e:
    print(f"Warning: Could not create data directories: {e}")

# Note: OPENAI_API_KEY is expected to be set as an environment variable,
# especially when running in Docker. load_dotenv() helps for local .env files.
# The OpenAI library will pick up the OPENAI_API_KEY environment variable automatically.