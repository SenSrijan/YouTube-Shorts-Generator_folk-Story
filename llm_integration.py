import os
import re
import json
import requests
from dotenv import load_dotenv
from groq import Groq
from typing import Dict

load_dotenv()

def call_llm(instruction: str) -> Dict[str, object]:
    """
    Sends a POST request to the OpenRouter AI API for chat completions.

    Args:
        instruction (str): The instruction to send to the API.

    Returns:
        dict: Contains 'response_status' and 'response_text'.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return {"response_status": None, "response_text": "Error: OPENROUTER_API_KEY not set"}

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "qwen/qwen2.5-vl-72b-instruct:free",
        "messages": [
            {"role": "user", "content": instruction}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        return {"response_status": None, "response_text": f"Request error: {str(e)}"}

    try:
        data = response.json()
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        return {"response_status": response.status_code, "response_text": content}
    except json.JSONDecodeError:
        return {"response_status": response.status_code, "response_text": "Error: Invalid JSON response"}


def call_llm_gorq(instruction: str) -> str:
    """
    Sends a chat completion request to the Groq language model API.

    Args:
        instruction (str): The instruction to be sent to the language model.

    Returns:
        str: The cleaned response from the model.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY not set"
    
    client = Groq(api_key=api_key)
    
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": instruction}
        ],
        model="deepseek-r1-distill-llama-70b",
    )
    
    api_response = chat_completion.choices[0].message.content
    # Remove internal chain-of-thought markers if present
    clean_response = re.sub(r'<think>.*?</think>', '', api_response, flags=re.DOTALL).strip()
    return clean_response


if __name__ == "__main__":
    # Example usage
    tweet = call_llm_gorq("Create a 100 word Funny Tweet.")
    print(tweet)
