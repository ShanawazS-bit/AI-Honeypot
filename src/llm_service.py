import os
import openai
import google.generativeai as genai
from django.conf import settings

class LLMService:
    """
    Service to interact with LLMs (Gemini or OpenAI) for generating dynamic, persona-based responses
    and extracting intelligence/insights.
    """
    
    def __init__(self):
        # 1. Try Gemini First (Preferred for this hackathon/user request)
        self.gemini_key = getattr(settings, "GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
        self.openai_key = getattr(settings, "OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        
        self.provider = None
        self.model = None
        
        # Initialize Gemini
        if self.gemini_key:
            try:
                genai.configure(api_key=self.gemini_key)
                self.model = genai.GenerativeModel('gemini-pro')
                self.provider = "gemini"
                print(f"[LLM] Initialized Gemini Pro.")
            except Exception as e:
                print(f"[LLM] Gemini Initialization failed: {e}")
        
        # Fallback to OpenAI
        if not self.provider and self.openai_key:
            try:
                self.client = openai.OpenAI(api_key=self.openai_key)
                self.provider = "openai"
                print("[LLM] Initialized OpenAI Client.")
            except Exception as e:
                print(f"[LLM] OpenAI Initialization failed: {e}")
        
        if not self.provider:
            print("[LLM] No valid LLM provider found (Check GEMINI_API_KEY or OPENAI_API_KEY).")

        # Session cache to avoid sending full persona every time
        self.session_cache = {}
        
        # Enhanced persona with rich character details
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

    def generate_response(self, text_input: str, history: list, intent: str, session_id: str = None) -> str:
        """
        Generates a response using the configured provider.
        """
        if not self.provider:
            return None

        # Build Context
        context = self.persona_instruction
        if intent != "UNKNOWN":
            context += f"\n\nCURRENT INTENT DETECTED: {intent} (React to this specific threat/scenario)"
            
        conversation_text = ""
        for msg in history:
            sender = "Scammer" if msg.get("sender") == "scammer" else "You"
            conversation_text += f"{sender}: {msg.get('text', '')}\n"
        
        conversation_text += f"Scammer: {text_input}\nYou:"
        
        full_prompt = f"{context}\n\nCONVERSATION HISTORY:\n{conversation_text}"

        try:
            if self.provider == "gemini":
                # Gemini Call
                response = self.model.generate_content(full_prompt)
                reply = response.text.replace("You:", "").strip()
                print(f"[LLM-Gemini] Generated: {reply[:50]}...")
                return reply
                
            elif self.provider == "openai":
                # OpenAI Call
                messages = [{"role": "system", "content": context}]
                # Convert history to messages... (simplified for brevity, full logic usually better)
                messages.append({"role": "user", "content": f"Conversation:\n{conversation_text}"})
                
                chat_completion = self.client.chat.completions.create(
                    messages=messages,
                    model="gpt-3.5-turbo",
                    temperature=0.7,
                    max_tokens=150
                )
                reply = chat_completion.choices[0].message.content.strip()
                print(f"[LLM-OpenAI] Generated: {reply[:50]}...")
                return reply
                
        except Exception as e:
            print(f"[LLM] Generation failed: {e}")
            return None

    def generate_insight(self, conversation_text: str) -> dict:
        """
        Generates concise agent notes and scam classification.
        Returns: {"agentNotes": str, "scamType": str, "confidence": float}
        """
        if not self.provider:
            return {}

        prompt = f"""
        Analyze this conversation between a scammer and a potential victim (honeypot).
        
        CONVERSATION:
        {conversation_text}
        
        TASK:
        1. Identify the 'scamType' (e.g., bank_fraud, upi_fraud, phishing, kyc_fraud, tech_support).
        2. Write 'agentNotes' summarizing the scammer's tactics (urgency, threats, kindness) and what they asked for.
        
        OUTPUT FORMAT (JSON):
        {{
            "scamType": "...",
            "agentNotes": "...",
            "confidence": 0.0-1.0
        }}
        """
        
        try:
            if self.provider == "gemini":
                response = self.model.generate_content(prompt)
                # Clean markdown json blocks if present
                clean_text = response.text.replace("```json", "").replace("```", "").strip()
                import json
                return json.loads(clean_text)
            
            elif self.provider == "openai":
                messages = [{"role": "system", "content": "You are a scam analysis expert. Output JSON only."}]
                messages.append({"role": "user", "content": prompt})
                
                resp = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    temperature=0.3
                )
                clean_text = resp.choices[0].message.content.strip()
                import json
                return json.loads(clean_text)
                
        except Exception as e:
            print(f"[LLM] Insight generation failed: {e}")
            return {
                "scamType": "unknown",
                "agentNotes": "Automated extraction failed. Scammer used typical social engineering tactics.",
                "confidence": 0.0
            }
