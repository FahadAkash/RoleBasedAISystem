import os
import sys

# Add the current directory to sys.path to import backend modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.config import GEMINI_API_KEY, GEMINI_MODEL
from google import genai

def test_gemini_api():
    print(f"Testing Gemini API Key: {GEMINI_API_KEY[:5]}...{GEMINI_API_KEY[-5:]}")
    print(f"Using Model: {GEMINI_MODEL}")
    
    try:
        # Initialize the client
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Test generation
        print("Sending prompt to Gemini: 'Hello, are you working?'")
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents="Hello, are you working? Please respond with a short confirmation.",
        )
        
        print("\n--- GEMINI RESPONSE ---")
        print(response.text)
        print("-----------------------")
        print("\n[SUCCESS] The Gemini API key and LLM are working correctly.")
        
    except Exception as e:
        print("\n[ERROR] Failed to communicate with Gemini API.")
        print(f"Exception details: {e}")

if __name__ == "__main__":
    test_gemini_api()
