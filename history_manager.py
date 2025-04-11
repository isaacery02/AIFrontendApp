# history_manager.py
import json
from pathlib import Path
from typing import List, Tuple

def load_history(history_file: Path) -> List[Tuple[str, str]]:
    """Loads chat history from the JSON file."""
    history = []
    if history_file.exists():
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
                # Basic validation: Ensure it's a list of lists/tuples with 2 elements
                if isinstance(loaded_data, list):
                    history = [tuple(item) for item in loaded_data if isinstance(item, (list, tuple)) and len(item) == 2]
                    print(f"Loaded {len(history)} valid items from {history_file}")
                else:
                     print(f"Warning: History file {history_file} does not contain a list. Starting fresh.")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading history file {history_file}: {e}. Starting fresh.")
        except Exception as e:
             print(f"Unexpected error loading history: {e}. Starting fresh.")
    else:
        print("History file not found, starting fresh.")
    return history

def save_history(history_file: Path, history_data: List[Tuple[str, str]]):
    """Saves chat history to the JSON file."""
    try:
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history_data, f, indent=4)
        print(f"Saved {len(history_data)} items to {history_file}")
    except IOError as e:
        print(f"Error saving history file {history_file}: {e}")
    except Exception as e:
         print(f"Unexpected error saving history: {e}")