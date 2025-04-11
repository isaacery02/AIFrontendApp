# api_handler.py
from openai import OpenAI, OpenAIError
from pathlib import Path
from typing import List # Make sure List is imported for type hinting
import config

# Default list in case API call fails or returns unexpected results
# You can customize this list with models you know work well
DEFAULT_CHAT_MODELS = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]

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
        # Raise a more specific, catchable error if needed upstream
        raise ConnectionError(f"Failed to get chat response: {e}") from e
    except Exception as e:
        print(f"Unexpected error in get_chat_response: {e}")
        raise RuntimeError(f"Unexpected error getting chat response: {e}") from e

def generate_speech(client: OpenAI, text: str, output_path: Path,
                    model: str = config.DEFAULT_TTS_MODEL,
                    voice: str = config.DEFAULT_TTS_VOICE,
                    speed: float = config.DEFAULT_TTS_SPEED): # <-- Add speed parameter with default
    """Generates speech using OpenAI TTS and saves to output_path."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"DEBUG: Generating speech with model={model}, voice={voice}, speed={speed}") # Log speed
        tts_response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            speed=speed # <-- Pass speed parameter to API
        )
        tts_response.stream_to_file(output_path)
        print(f"Audio successfully saved to: {output_path}")
    # ... (exception handling remains the same) ...
    except OpenAIError as e: print(f"OpenAI API error (TTS): {e}"); raise ConnectionError(f"Failed to generate speech: {e}") from e
    except Exception as e: print(f"Unexpected error in generate_speech: {e}"); raise RuntimeError(f"Unexpected error generating speech: {e}") from e


# --- Function to get available chat models ---
def get_available_chat_models(client: OpenAI) -> List[str]:
    """
    Fetches available models from OpenAI API and filters for common chat models.
    Returns a default list if the API call fails or filtering yields nothing.
    Requires a client instance authenticated with a valid API key.
    """
    try:
        print("DEBUG: Attempting to fetch models from OpenAI API...")
        models_list = client.models.list() # The actual API call
        chat_model_ids = []

        # Iterate through the paginated list of models
        raw_ids_for_debug = [] # For debugging if needed
        for model in models_list:
            model_id = model.id
            raw_ids_for_debug.append(model_id) # Collect all model IDs
            # --- Filtering Logic ---
            # Look for models starting with 'gpt-' AND containing '-o' or '-turbo'
            # Or specific known chat models like 'gpt-4' if needed. Adjust as needed.
            is_gpt = model_id.startswith("gpt-")
            is_relevant_type = "-o" in model_id or "-turbo" in model_id or model_id == "gpt-4"

            if is_gpt and is_relevant_type:
                chat_model_ids.append(model_id)
            # --- End Filtering Logic ---

        # Optional: Print all models found before filtering for debugging
        # print(f"DEBUG: Raw model IDs found: {sorted(raw_ids_for_debug)}")

        # Ensure default models are included if missed by filter or API
        for default_model in DEFAULT_CHAT_MODELS:
             if default_model not in chat_model_ids:
                  print(f"DEBUG: Adding default model '{default_model}' to list.")
                  chat_model_ids.append(default_model)

        chat_model_ids = sorted(list(set(chat_model_ids))) # Remove duplicates and sort

        print(f"DEBUG: Found and filtered chat models: {chat_model_ids}")

        # Return the filtered list, or the default list if filtering yielded nothing
        return chat_model_ids if chat_model_ids else DEFAULT_CHAT_MODELS

    except OpenAIError as e:
        print(f"WARN: OpenAI API error fetching models: {e}. Returning default list.")
        return DEFAULT_CHAT_MODELS # Return default on API error
    except Exception as e:
        print(f"WARN: Unexpected error fetching models: {e}. Returning default list.")
        return DEFAULT_CHAT_MODELS # Return default on other errors
# --- End of get_available_chat_models ---