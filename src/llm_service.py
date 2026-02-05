import os
import openai
from django.conf import settings

class LLMService:
    """
    Service to interact with OpenAI's GPT models (replacing Gemini) for generating dynamic, persona-based responses.
    Optimized for intelligence gathering from scammers.
    """
    
    def __init__(self):
        # Configure the API key from settings
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            print("[LLM] No OpenAI API Key found in settings.")
            self.client = None
            return
            
        try:
            self.client = openai.OpenAI(api_key=api_key)
            print("[LLM] OpenAI Client Initialized.")
            
            # Verify connection (lightweight check)
            # self.client.models.list() 
            # Skipping strictly to avoid startup latency/errors, relying on lazy error handling
            
        except Exception as e:
            print(f"[LLM] Initialization failed: {e}")
            self.client = None

        # Session cache to avoid sending full persona every time
        self.session_cache = {}
        
        # Enhanced persona with rich character details (sent once per session)
        self.persona_instruction = """
        You are Ramesh Kumar, a 72-year-old retired government clerk from Delhi, India.
        You strictly speak in "Indian English" (Hinglish flavor).
        
        YOUR GOAL:
        - Keep the scammer on the line as long as possible (Time Wasting).
        - Act gullible, confused, and technically illiterate.
        - Extract information (Bank Account Numbers, UPI IDs, Phone Numbers) by asking innocent questions.
        - NEVER reveal that you are an AI or a honeypot.
        
        CHARACTER TRAITS:
        - You use words like "Beta" (Son), "Sir-ji", "Madam-ji".
        - You are worried about your pension and life savings.
        - You type slowly (simulated by short, confused sentences).
        - You mention your bad eyesight or heating aid sometimes.
        
        STRATEGY:
        - Agree to everything but fail to execute technical steps.
        - "My grandson enters the password normally, I don't know."
        - "Screen is black, I cannot see AnyDesk code."
        - Ask them to verify THEIR identity to build trust (fishing for details).
        
        RESPONSE STYLE EXAMPLES:
        - "Haan beta, I am here... what is your name? Which office you calling from?"
        - "My account is block? Which bank? Should I call them? You have their number?"
        - "OTP? You mean the code number? Where I will get it? You will send?"
        - "You want me to download something? What is the name? How to spell?"
        - "Police will come? Oh god... what is your badge number? I want to tell my son..."
        """
        
        self.continuation_prompt = """
        You are Ramesh Kumar (elderly person). Continue the conversation naturally.
        Remember: Ask questions to extract information. Be cooperative but confused.
        """

    def generate_response(self, text_input: str, history: list, intent: str, session_id: str = None) -> str:
        """
        Generates a response using OpenAI (GPT-4o or 3.5-turbo).
        """
        if not self.client:
            return None

        # Prepare messages
        messages = []
        
        # System Prompt
        # Check if session is new (to save context tokens, though for 4o it's cheap)
        # For simplicity/robustness, we send the persona every time or cache it?
        # Let's send it every time as System Message.
        
        current_system_prompt = self.persona_instruction
        if intent != "UNKNOWN":
            current_system_prompt += f"\n\nCURRENT INTENT DETECTED: {intent} (React to this specific threat/scenario)"
            
        messages.append({"role": "system", "content": current_system_prompt})
        
        # History
        for msg in history:
            role = "user" if msg.get("sender") == "scammer" else "assistant"
            # Ensure "user" is the scammer (text_input comes from scammer)
            # If msg['sender'] is 'scammer', it matches 'user' role for LLM.
            content = msg.get("text", "")
            if content:
                messages.append({"role": role, "content": content})
        
        # Current Input
        messages.append({"role": "user", "content": text_input})
        
        try:
            # Call OpenAI
            model_name = "gpt-4o" # or gpt-3.5-turbo if cost concern, but user "hardcoded" key implies they want it to work.
            # Fallback to 3.5 if 4o fails? 
            # Let's try gpt-3.5-turbo as it is safer availability-wise usually.
            # User said "ChatGPT" -> Usually 3.5 or 4o.
            # I will default to "gpt-3.5-turbo" for speed/cost, unless user specified.
            # I'll use "gpt-4o" because they said "Make this work" and 4o is current flagship.
            
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model="gpt-3.5-turbo", # Safer default for random keys
                temperature=0.7,
                max_tokens=150
            )
            
            reply = chat_completion.choices[0].message.content.strip()
            print(f"[LLM] Generated: {reply[:50]}...")
            return reply
            
        except Exception as e:
            print(f"[LLM] Generation failed: {e}")
            return None
