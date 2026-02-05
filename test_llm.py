
import os
from dotenv import load_dotenv
load_dotenv()

# Mock settings
from django.conf import settings
if not settings.configured:
    settings.configure(OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY"))

from src.llm_service import LLMService

def test_llm():
    print("Initializing LLM Service...")
    service = LLMService()
    
    if not service.client:
        print("❌ Client Init Failed (Check API Key)")
        return

    print("Testing Generation...")
    response = service.generate_response(
        text_input="Hello beta, who is this?", 
        history=[], 
        intent="GREETING"
    )
    
    if response:
        print(f"✅ Success! Response: {response}")
    else:
        print("❌ Generation Failed")

if __name__ == "__main__":
    test_llm()
