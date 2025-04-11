# main.py - Application Entry Point
import customtkinter
from app_gui import ChatApp
from audio_player import AudioPlayer
# config is loaded automatically when app_gui imports it, ensuring dir exists

if __name__ == "__main__":
    # Create the audio player instance first (initializes pygame mixer)
    player = AudioPlayer()

    # Check if player initialized successfully before starting app
    if player.initialized:
        app = ChatApp(player=player) # Pass player to the app
        app.mainloop()
        # Quit is handled by app.on_closing now
    else:
        # Handle pygame mixer init failure (optional: show an error message GUI)
        print("Application exiting due to audio initialization failure.")
        # You could show a simple Tkinter error message window here if desired
        root = customtkinter.CTk()
        root.withdraw() # Hide the root window
        customtkinter.CTkMessagebox(title="Error", message="Failed to initialize audio system (Pygame Mixer).\nPlease check audio drivers and pygame installation.\nApplication will exit.", icon="cancel")
        root.destroy()