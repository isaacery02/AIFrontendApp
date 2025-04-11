# history_manager.py
import json
from pathlib import Path
from typing import List, Tuple

def load_history(history_file: Path) -> List[Tuple[str, str, str | None]]: # Updated type hint
    """Loads chat history from the JSON file. Handles 3-element tuples."""
    history = []
    if history_file.exists():
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
                # Basic validation: Ensure it's a list
                if isinstance(loaded_data, list):
                    processed_count = 0
                    skipped_count = 0
                    for item in loaded_data:
                        # Check if item is a list/tuple with 3 elements
                        if isinstance(item, (list, tuple)) and len(item) == 3:
                            # Ensure prompt/response are strings, timestamp can be str or None (JSON null)
                            prompt = str(item[0]) if item[0] is not None else ""
                            response = str(item[1]) if item[1] is not None else ""
                            timestamp = item[2] # Keep as str or None
                            history.append((prompt, response, timestamp))
                            processed_count += 1
                        # Optional: Handle old 2-element format if needed
                        elif isinstance(item, (list, tuple)) and len(item) == 2:
                            print("DEBUG: Loading old 2-element history item (no timestamp).")
                            history.append((str(item[0]), str(item[1]), None)) # Add None for timestamp
                            processed_count += 1
                        else:
                            print(f"Warning: Skipping invalid item format during history load: {item}")
                            skipped_count += 1
                    print(f"Loaded {processed_count} items from {history_file}" + (f", skipped {skipped_count} invalid items." if skipped_count else "."))
                else:
                     print(f"Warning: History file {history_file} does not contain a list. Starting fresh.")
                     history = [] # Ensure history is a list
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading/parsing history file {history_file}: {e}. Starting fresh.")
            history = [] # Reset on error
        except Exception as e:
             print(f"Unexpected error loading history: {e}. Starting fresh.")
             history = [] # Reset on error
    else:
        print("History file not found, starting fresh.")
        history = [] # Ensure history is a list if file doesn't exist

    # Ensure it always returns a list
    return history if isinstance(history, list) else []

# (save_history function remains the same)
def save_history(history_file: Path, history_data: List[Tuple[str, str, str | None]]):
    """Saves chat history to the JSON file."""
    try:
        # Ensure parent directory exists just in case
        history_file.parent.mkdir(parents=True, exist_ok=True)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history_data, f, indent=4) # indent=4 makes the file readable
        print(f"Saved {len(history_data)} items to {history_file}")
    except IOError as e:
        print(f"Error saving history file {history_file}: {e}")
    except Exception as e:
         print(f"Unexpected error saving history: {e}")