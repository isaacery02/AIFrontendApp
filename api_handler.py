# api_handler.py
from openai import OpenAI, OpenAIError
from pathlib import Path

def get_chat_response(client: OpenAI, prompt: str, model: str) -> str:
    """Gets a text response from the OpenAI Chat API."""
    try:
        chat_response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        generated_text = chat_response.choices[0].message.content
        if not generated_text:
            return "(No text response received from API.)" # Return informative message
        return generated_text
    except OpenAIError as e:
        print(f"OpenAI API error (Chat): {e}")
        raise ConnectionError(f"Failed to get chat response: {e}") from e # Raise specific error
    except Exception as e:
        print(f"Unexpected error in get_chat_response: {e}")
        raise RuntimeError(f"Unexpected error getting chat response: {e}") from e

def generate_speech(client: OpenAI, text: str, output_path: Path, model: str, voice: str):
    """Generates speech using OpenAI TTS and saves to output_path."""
    try:
        # Ensure parent directory exists (though typically handled before calling)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        tts_response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text
        )
        tts_response.stream_to_file(output_path)
        print(f"Audio successfully saved to: {output_path}")
    except OpenAIError as e:
        print(f"OpenAI API error (TTS): {e}")
        raise ConnectionError(f"Failed to generate speech: {e}") from e # Raise specific error
    except Exception as e:
        print(f"Unexpected error in generate_speech: {e}")
        raise RuntimeError(f"Unexpected error generating speech: {e}") from e