import sys
import os
import django
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'honeypot_site.settings')
django.setup()

from src.llm_service import LLMService

def verify():
    print("Testing LLM Service (Auto-Detect Mode)...")
    llm = LLMService()
    
    if not llm.provider:
        print("❌ No Provider Initialized.")
        return

    print(f"✅ Active Provider: {llm.provider.upper()}")
    
    try:
        print("Sending test prompt...")
        response = llm.generate_response(
            text_input="Hello, I am calling from SBI Bank.", 
            history=[], 
            intent="bank_fraud", # Intent check
            session_id="test-anthropic"
        )
        print(f"🎉 Response: '{response}'")
        
        insight = llm.generate_insight("Scammer: Give me OTP. User: No.")
        print(f"🧠 Insight: {insight}")
        
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    verify()
