# audio_player.py
# Handles audio playback using pygame.mixer.Sound

import pygame
from pathlib import Path
import logging
import config # Although unused directly, keep it if config module sets up logging

# Configure logging (basic setup, can be configured externally)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AudioPlayer:
    """Handles audio playback using pygame.mixer.Sound."""
    def __init__(self, buffer_size: int = 2048):
        self.initialized: bool = False
        self.current_channel: pygame.mixer.Channel | None = None
        self.sound_cache: dict[str, pygame.mixer.Sound] = {}  # Dictionary to store preloaded sounds
        self.logger = logging.getLogger(f"{__name__}.AudioPlayer") # Create instance-specific logger if desired, or use module logger

        try:
            # Initialize pygame mixer with configurable buffer size
            pygame.mixer.init(buffer=buffer_size)
            self.initialized = True
            self.logger.info(f"Pygame mixer initialized successfully (buffer={buffer_size}).")
        except pygame.error as e:
            self.logger.error(f"Error initializing pygame mixer: {e}. Audio playback disabled.", exc_info=True)

    def preload_sound(self, filepath: str, sound_id: str | None = None) -> bool:
        """
        Preload a sound file into memory for faster playback later.
        Optionally assign it an ID for later reference.
        Returns True if preloading succeeded, False otherwise.
        """
        if not self.initialized:
            self.logger.warning("AudioPlayer not initialized, cannot preload sound.")
            return False

        if sound_id is None:
            sound_id = filepath  # Use filepath as the default ID

        try:
            sound = pygame.mixer.Sound(filepath)
            self.sound_cache[sound_id] = sound
            self.logger.debug(f"Preloaded sound '{sound_id}' from {filepath}")
            return True
        except pygame.error as e:
            self.logger.error(f"Pygame error preloading sound '{sound_id}' from {filepath}: {e}", exc_info=True)
            return False
        except FileNotFoundError:
            self.logger.error(f"Sound file not found at {filepath} during preload for '{sound_id}'")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error preloading sound '{sound_id}': {e}", exc_info=True)
            return False

    def play_sound(self, filepath: str, use_cache: bool = True) -> bool:
        """
        Loads a sound file and plays it on an available channel.
        Returns True if playback started successfully, False otherwise.
        Stores the channel used for potential stopping.

        If use_cache is True, will check for preloaded sound first.
        """
        if not self.initialized:
            self.logger.warning("AudioPlayer not initialized, cannot play sound.")
            return False

        if self.current_channel and self.current_channel.get_busy():
            self.logger.warning("Already playing a sound, stopping previous one.")
            self.current_channel.stop()

        try:
            sound: pygame.mixer.Sound | None = None
            if use_cache and filepath in self.sound_cache:
                sound = self.sound_cache[filepath]
                self.logger.debug(f"Using cached sound for {filepath}")
            else:
                self.logger.debug(f"Loading sound: {filepath}")
                sound = pygame.mixer.Sound(filepath)
                # Optionally cache for future use
                if use_cache:
                    self.sound_cache[filepath] = sound

            # Play the sound immediately without delay
            self.logger.debug(f"Playing sound '{filepath}'...")
            self.current_channel = sound.play()

            if self.current_channel is None:
                self.logger.error("Failed to get channel for playback.")
                return False

            self.logger.debug("Sound playing.")
            return True

        except pygame.error as e:
            self.logger.error(f"Pygame error loading/playing sound file {filepath}: {e}", exc_info=True)
            self.current_channel = None
            return False
        except FileNotFoundError:
            self.logger.error(f"Error: Sound file not found at {filepath}")
            self.current_channel = None
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error playing sound '{filepath}': {e}", exc_info=True)
            self.current_channel = None
            return False


    def play_cached_sound(self, sound_id: str) -> bool:
        """Play a sound that has been previously cached by ID."""
        if not self.initialized:
             self.logger.warning("AudioPlayer not initialized, cannot play cached sound.")
             return False

        if sound_id not in self.sound_cache:
            self.logger.warning(f"Sound '{sound_id}' not found in cache")
            return False

        if self.current_channel and self.current_channel.get_busy():
            self.logger.warning("Already playing a sound, stopping previous one.")
            self.current_channel.stop()

        try:
            sound = self.sound_cache[sound_id]
            self.logger.debug(f"Playing cached sound '{sound_id}'...")
            self.current_channel = sound.play()

            if self.current_channel is None:
                self.logger.error(f"Failed to get channel for playback of cached sound '{sound_id}'.")
                return False

            self.logger.debug(f"Cached sound '{sound_id}' playing.")
            return True
        except pygame.error as e:
            self.logger.error(f"Pygame error playing cached sound '{sound_id}': {e}", exc_info=True)
            self.current_channel = None
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error playing cached sound '{sound_id}': {e}", exc_info=True)
            self.current_channel = None
            return False

    def stop(self) -> None:
        """Stops playback on the current channel if active, or all channels."""
        if not self.initialized:
            return

        self.logger.debug("AudioPlayer stop requested.")

        if self.current_channel and self.current_channel.get_busy():
            self.current_channel.stop()
            self.logger.debug("Stopped playback on specific channel.")
        else:
            # Fallback: stop all channels if specific channel lost or wasn't busy
            try:
                pygame.mixer.stop()
                self.logger.debug("Called pygame.mixer.stop() (fallback/ensure stopped).")
            except pygame.error as e:
                 self.logger.error(f"Pygame error during mixer.stop(): {e}", exc_info=True)


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
             self.logger.debug("Playback finished, clearing current channel reference.")
             self.current_channel = None

        return False

    def clear_cache(self) -> None:
        """Clear the sound cache to free memory."""
        self.sound_cache.clear()
        self.logger.info("Sound cache cleared.")

    def quit(self) -> None:
        """Stops playback, clears cache, and quits the pygame mixer."""
        if self.initialized:
            try:
                self.logger.info("Quitting AudioPlayer...")
                # Stop all sounds first
                self.stop() # Use the stop method which includes logging
                # Clear the cache
                self.clear_cache()
                self.logger.info("Quitting pygame mixer...")
                pygame.mixer.quit()
                self.initialized = False
                self.logger.info("Pygame mixer quit successfully.")
            except pygame.error as e:
                self.logger.error(f"Error quitting pygame mixer: {e}", exc_info=True)

