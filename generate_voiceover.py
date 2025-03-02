import requests
import os
from dotenv import load_dotenv

load_dotenv()

def text_to_speech(text: str, api_key: str, language: str = 'en-us', codec: str = 'MP3', output_file: str = "voiceover.mp3") -> None:
    """
    Converts text to speech using the Voice RSS API and saves the result as an audio file.
    
    Args:
        text (str): The text to be converted to speech.
        api_key (str): Your Voice RSS API key.
        language (str): The language code (default 'en-us').
        codec (str): The audio codec to use (default 'MP3').
        output_file (str): The file path where the audio will be saved.
    """
    url = "http://api.voicerss.org/"
    params = {
        'key': api_key,
        'src': text,
        'hl': language,
        'c': codec,
        'f': '44khz_16bit_stereo'
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        with open(output_file, "wb") as audio_file:
            audio_file.write(response.content)
        print(f"Voiceover saved as '{output_file}'")
    else:
        print("Error:", response.text)

# Example usage remains unchanged.
if __name__ == "__main__":
    API_KEY = os.getenv("VOICE_RSS_API_KEY")
    sample_text = "Hello, this is a sample voiceover generated from text using a free API."
    text_to_speech(sample_text, API_KEY)
