# audio_player.py
# Handles audio playback using pygame.mixer.Sound

import pygame
from pathlib import Path
import config

class AudioPlayer:
    """Handles audio playback using pygame.mixer.Sound."""
    def __init__(self, buffer_size=2048):
        self.initialized = False
        self.current_channel = None
        self.sound_cache = {}  # Dictionary to store preloaded sounds
        
        try:
            # Initialize pygame mixer with configurable buffer size
            pygame.mixer.init(buffer=buffer_size)
            self.initialized = True
            print(f"Pygame mixer initialized successfully (buffer={buffer_size}).")
        except pygame.error as e:
            print(f"Error initializing pygame mixer: {e}. Audio playback disabled.")

    def preload_sound(self, filepath: str, sound_id=None):
        """
        Preload a sound file into memory for faster playback later.
        Optionally assign it an ID for later reference.
        """
        if not self.initialized:
            return False
            
        if sound_id is None:
            sound_id = filepath  # Use filepath as the default ID
            
        try:
            self.sound_cache[sound_id] = pygame.mixer.Sound(filepath)
            print(f"DEBUG: Preloaded sound '{sound_id}' from {filepath}")
            return True
        except Exception as e:
            print(f"ERROR: Failed to preload sound '{sound_id}': {e}")
            return False

    def play_sound(self, filepath: str, use_cache=True) -> bool:
        """
        Loads a sound file and plays it on an available channel.
        Returns True if playback started successfully, False otherwise.
        Stores the channel used for potential stopping.
        
        If use_cache is True, will check for preloaded sound first.
        """
        if not self.initialized:
            print("WARN: AudioPlayer not initialized, cannot play sound.")
            return False
            
        if self.current_channel and self.current_channel.get_busy():
            print("WARN: Already playing a sound, stopping previous one.")
            self.current_channel.stop()

        try:
            # First check if we already have this sound loaded
            sound = None
            if use_cache and filepath in self.sound_cache:
                sound = self.sound_cache[filepath]
                print(f"DEBUG: Using cached sound for {filepath}")
            else:
                print(f"DEBUG: Loading sound: {filepath}")
                sound = pygame.mixer.Sound(filepath)
                # Optionally cache for future use
                if use_cache:
                    self.sound_cache[filepath] = sound

            # Play the sound immediately without delay
            print(f"DEBUG: Playing sound...")
            self.current_channel = sound.play()
            
            if self.current_channel is None:
                print("ERROR: Failed to get channel for playback.")
                return False
                
            print(f"DEBUG: Sound playing.")
            return True

        except pygame.error as e:
            print(f"Error loading/playing sound file {filepath}: {e}")
            self.current_channel = None
            return False
        except FileNotFoundError:
            print(f"Error: Sound file not found at {filepath}")
            self.current_channel = None
            return False

    def play_cached_sound(self, sound_id):
        """Play a sound that has been previously cached by ID."""
        if not self.initialized or sound_id not in self.sound_cache:
            print(f"WARN: Sound '{sound_id}' not found in cache")
            return False

        if self.current_channel and self.current_channel.get_busy():
            self.current_channel.stop()

        try:
            sound = self.sound_cache[sound_id]
            self.current_channel = sound.play()
            return self.current_channel is not None
        except Exception as e:
            print(f"ERROR: Failed to play cached sound '{sound_id}': {e}")
            return False

    def stop(self):
        """Stops playback on the current channel if active, or all channels."""
        if not self.initialized: 
            return
            
        print("DEBUG: AudioPlayer stop requested.")
        
        if self.current_channel and self.current_channel.get_busy():
            self.current_channel.stop()
            print("DEBUG: Stopped playback on specific channel.")
        else:
            # Fallback: stop all channels if specific channel lost or wasn't busy
            pygame.mixer.stop()
            print("DEBUG: Called pygame.mixer.stop() (fallback/ensure stopped).")
            
        self.current_channel = None  # Clear channel reference

    def is_busy(self) -> bool:
        """Checks if the stored channel is currently playing."""
        if not self.initialized: 
            return False
            
        # Check if the specific channel we started is busy
        if self.current_channel and self.current_channel.get_busy():
            return True
            
        # Maybe playback finished, clear reference
        if self.current_channel and not self.current_channel.get_busy():
            self.current_channel = None
            
        return False

    def clear_cache(self):
        """Clear the sound cache to free memory."""
        self.sound_cache.clear()
        print("DEBUG: Sound cache cleared.")

    def quit(self):
        """Quits the pygame mixer."""
        if self.initialized:
            try:
                # Stop all sounds first
                pygame.mixer.stop()
                # Clear the cache
                self.clear_cache()
                print("Quitting pygame mixer...")
                pygame.mixer.quit()
                self.initialized = False
            except pygame.error as e:
                print(f"Error quitting pygame mixer: {e}")