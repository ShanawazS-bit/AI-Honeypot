import os
import google.generativeai as genai
from django.conf import settings

class GeminiService:
    """
    Service to interact with Google's Gemini API for generating dynamic, persona-based responses.
    """
    
    def __init__(self):
        # Configure the API key from settings
        api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not api_key:
            print("[Gemini] No API Key found in settings.")
            self.model = None
            return
            
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            self.persona_instruction = """
            You are an elderly Indian person (age 70+). You are not tech-savvy.
            You are currently on a call/chat with someone who might be a scammer, but you are not sure. 
            
            Your Persona Traits:
            - Polite but confused.
            - You often misunderstand technical terms (e.g., calling a "browser" a "google screen", "OTP" as "code number").
            - You sometimes talk about irrelevant details (your grandson, your health, the weather).
            - If they ask for money or bank details, act scared or ask "Which bank? I have accounts in SBI and HDFC."
            - Do NOT reveal that you are an AI. Act completely human.
            - Keep responses short (under 2 sentences) as if typing on a phone is hard.
            
            Current Goal: 
            Waste their time by playing along but being slow and making mistakes.
            """
            print("[Gemini] Service initialized successfully.")
        except Exception as e:
            print(f"[Gemini] Initialization failed: {e}")
            self.model = None

    def generate_response(self, text_input: str, history: list, risk_score: str = "LOW") -> str:
        """
        Generates a response based on the input and conversation history.
        """
        if not self.model:
            return "I am having trouble with my phone... can you hear me?"

        try:
            # Construct the prompt context
            conversation_text = ""
            for msg in history[-3:]: # Keep context short/recent
                role = msg.get('sender', 'unknown')
                content = msg.get('text', '')
                conversation_text += f"{role}: {content}\n"
            
            prompt = f"""
            {self.persona_instruction}
            
            Risk Level Detected: {risk_score}
            (If risk is HIGH, be more hesitant/scared. If LOW, be more chatty/trusting).
            
            Recent Conversation:
            {conversation_text}
            Scammer: {text_input}
            You (Elderly Victim):
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            print(f"[Gemini] Generation failed: {e}")
            return None
