# file_utils.py
from pathlib import Path

def cleanup_old_recordings(responses_dir: Path, max_recordings: int):
    """Deletes oldest recordings in responses_dir if count exceeds max_recordings."""
    try:
        print(f"\nChecking recording history in {responses_dir} (keeping latest {max_recordings})...")
        if not responses_dir.is_dir():
             print("Responses directory not found for cleanup.")
             return

        # Use glob to find .mp3 files directly
        mp3_files = sorted(
            list(responses_dir.glob("*.mp3")),
            key=lambda x: x.stat().st_mtime # Sort by modification time (oldest first)
        )

        if len(mp3_files) > max_recordings:
            files_to_delete_count = len(mp3_files) - max_recordings
            files_to_delete = mp3_files[:files_to_delete_count]
            print(f"Found {len(mp3_files)} recordings. Deleting oldest {files_to_delete_count}:")
            for file_to_delete in files_to_delete:
                try:
                    file_to_delete.unlink() # Delete the file
                    print(f"  - Deleted: {file_to_delete.name}")
                except OSError as e:
                    print(f"  - Error deleting file {file_to_delete}: {e}")
        else:
            print(f"Found {len(mp3_files)} recordings. No cleanup needed.")
    except Exception as e:
        print(f"An error occurred during old recording cleanup: {e}")