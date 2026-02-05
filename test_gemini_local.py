import os
from dotenv import load_dotenv
load_dotenv()

import django
from django.conf import settings

# Setup Django standalone
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'honeypot_site.settings')
django.setup()

from src.llm_service import GeminiService
import google.generativeai as genai

print("--- Local Gemini Verification ---")
print(f"Google Generative AI version: {genai.__version__}")

service = GeminiService()

if service.model:
    print("\n✅ Service initialized successfully!")
    print(f"Model: {service.model.model_name}")
    
    print("\nAttempting generation...")
    try:
        response = service.generate_response(
            "Hello, I am calling from the bank.", 
            [], 
            session_id="local-test-1"
        )
        print(f"\n✅ Response received:\n{response}")
    except Exception as e:
        print(f"\n❌ Generation failed: {e}")
else:
    print("\n❌ Service failed to initialize.")
    print("Check GEMINI_API_KEY in .env file.")
