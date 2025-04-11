# AI Speech Interface

A Python application integrating OpenAI's text generation and speech synthesis capabilities, providing both text and voice responses to your queries.

## Overview

This application combines the power of OpenAI's language models with high-quality text-to-speech technology to create an interactive chat experience with voice feedback. The interface allows you to:

- Submit text queries to OpenAI's language models
- Receive text responses from AI
- Have those responses read aloud with natural-sounding speech
- Maintain a history of all past conversations
- Recall and replay previous interactions

The core functionality focuses on speech synthesis, making this tool particularly valuable for users who prefer voice-based interaction with AI systems. The exceptional quality of OpenAI's text-to-speech service provides a natural and engaging listening experience that feels conversational rather than robotic.

## Requirements

- Python 3.8 or newer
- OpenAI API key (paid service)
- Internet connection for API access

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/ai-speech-interface.git
   cd ai-speech-interface
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up your OpenAI API key:
   - Create a `.env` file in the project root
   - Add your API key: `OPENAI_API_KEY=your_api_key_here`

## Usage

1. Start the application:
   ```
   python main.py
   ```

2. Enter your text query in the input box
3. Click "Generate & Speak" or press Ctrl+Enter
4. The AI will generate a text response and read it aloud
5. Previous conversations appear in the history panel on the left
6. Click any history item to recall both the text and audio response

## Features

- **Dual-mode interaction**: Get both text and speech responses
- **Conversation history**: Keep track of all your past interactions
- **Playback controls**: Stop audio playback at any time
- **Customizable interface**: Enable/disable speech output as needed
- **Efficient storage management**: Automatic cleanup of old audio files

## Cost Considerations

The application uses OpenAI's API services which require payment:
- Text generation (chat completions API)
- Text-to-speech synthesis

You will need to provide your own OpenAI API key and will be billed according to OpenAI's pricing structure. Usage is optimized to minimize unnecessary API calls.

## License

[MIT License](LICENSE)

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.
