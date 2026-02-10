import os
import requests
import zipfile
import io

MODELS_DIR = "models"
VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
MODEL_NAME = "vosk-model-small-en-us-0.15"

def download_and_extract_model():
    if not os.path.exists(MODELS_DIR):
        os.makedirs(MODELS_DIR)
        print(f"Created directory: {MODELS_DIR}")

    model_path = os.path.join(MODELS_DIR, MODEL_NAME)
    if os.path.exists(model_path):
        print(f"Model already exists at: {model_path}")
        return

    print(f"Downloading model from {VOSK_MODEL_URL}...")
    try:
        response = requests.get(VOSK_MODEL_URL, stream=True)
        response.raise_for_status()
        
        print("Extracting model...")
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            z.extractall(MODELS_DIR)
            
        print(f"Model successfully downloaded and extracted to {model_path}")
        
    except Exception as e:
        print(f"Failed to download/extract model: {e}")

if __name__ == "__main__":
    download_and_extract_model()
