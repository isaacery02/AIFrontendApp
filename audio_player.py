# audio_player.py
import pygame

class AudioPlayer:
    """Handles audio playback using pygame.mixer."""
    def __init__(self):
        self.initialized = False
        try:
            pygame.mixer.init()
            self.initialized = True
            print("Pygame mixer initialized successfully.")
        except pygame.error as e:
            print(f"Error initializing pygame mixer: {e}. Audio playback disabled.")

    def load(self, filepath: str) -> bool:
        """Loads an audio file for playback."""
        if not self.initialized: return False
        try:
            pygame.mixer.music.load(filepath)
            print(f"Audio loaded: {filepath}")
            return True
        except pygame.error as e:
            print(f"Error loading audio file {filepath}: {e}")
            return False

    def play(self):
        """Starts playing the loaded audio."""
        if not self.initialized: return
        try:
            pygame.mixer.music.play()
            print("Audio playback started.")
        except pygame.error as e:
            print(f"Error starting playback: {e}")

    def stop(self):
        """Stops the currently playing audio."""
        if not self.initialized: return
        try:
            pygame.mixer.music.stop()
            print("Audio playback stopped.")
        except pygame.error as e:
            print(f"Error stopping playback: {e}")

    def unload(self):
        """Unloads the current music file."""
        if not self.initialized: return
        try:
            # Pygame doesn't always need unload if loading new track,
            # but good practice if explicitly done playing.
             pygame.mixer.music.unload()
        except Exception as e:
            print(f"Minor error unloading music: {e}")


    def is_busy(self) -> bool:
        """Checks if audio is currently playing."""
        if not self.initialized: return False
        try:
            return pygame.mixer.music.get_busy()
        except pygame.error as e:
            print(f"Error checking mixer status: {e}")
            return False

    def quit(self):
        """Quits the pygame mixer."""
        if self.initialized:
            try:
                 pygame.mixer.quit()
                 self.initialized = False
                 print("Pygame mixer quit.")
            except pygame.error as e:
                 print(f"Error quitting pygame mixer: {e}")