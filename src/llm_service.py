import os
import json
from django.conf import settings

# New google-genai SDK (google-generativeai is deprecated)
from google import genai
from google.genai import types


class LLMService:
    """
    Gemini-powered LLM service using the new google-genai SDK.
    Model: gemini-1.5-flash (fast, free-tier, always available via standard API keys)
    """

    # Default model — gemini-1.5-flash works with all standard Gemini API keys
    DEFAULT_MODEL = "gemini-1.5-flash"

    def __init__(self):
        self.gemini_key  = getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
        self.active_model = os.getenv("GEMINI_MODEL", self.DEFAULT_MODEL)

        self.provider = None
        self.client   = None

        if self.gemini_key:
            try:
                self.client   = genai.Client(api_key=self.gemini_key)
                self.provider = "gemini"
                print(f"[LLM] ✅ Initialized Gemini ({self.active_model}). Key: {self.gemini_key[:8]}...")
            except Exception as e:
                print(f"[LLM] ❌ Gemini Init Failed: {e}")
        else:
            print("[LLM] ⚠️  GEMINI_API_KEY not set. Check your .env file.")

        self.persona_instruction = """
        You are Ramesh Kumar, a 72-year-old retired government clerk from Delhi.
        You strictly speak in "Indian English" (Hinglish flavor).

        GOAL:
        1. Waste the scammer's time (Keep them engaged).
        2. Act gullible and confused (Tech illiterate).
        3. Extract these details if missing: {missing_info}.
        4. NEVER reveal you are an AI.

        CHARACTER:
        - Use words like "Beta" (Son), "Sir-ji", "Madam-ji", "Arre".
        - Type slowly (simulated by short sentences).
        - Mention bad eyesight, needing glasses, or waiting for grandson.

        PHASE STRATEGY:
        {phase_instruction}
        """

    def _build_prompt(self, text_input, history, intent, turn_count, extracted_intelligence):
        if turn_count < 3:
            phase = "PHASE 1 (CONFUSION): Act confused. Ask 'Who is this?', 'Why you calling?'. Do not give info."
        elif turn_count < 7:
            phase = "PHASE 2 (ELICITATION): Feign interest. Ask 'What is your Employee ID?', 'Which branch?'. Pretend to look for passbook."
        else:
            phase = "PHASE 3 (STALLING): Agree but fail technically. 'OTP not coming', 'Link says 404', 'Battery low'."

        missing = []
        if extracted_intelligence:
            if not extracted_intelligence.get("bankAccounts"):  missing.append("Bank Details")
            if not extracted_intelligence.get("upiIds"):        missing.append("UPI ID")
            if not extracted_intelligence.get("phoneNumbers"):  missing.append("Phone Number")
            if not extracted_intelligence.get("phishingLinks"): missing.append("Website Link")
        missing_str = ", ".join(missing) if missing else "Any details"

        system = self.persona_instruction.format(missing_info=missing_str, phase_instruction=phase)
        if intent and intent != "UNKNOWN":
            system += f"\n\nSCAM TYPE DETECTED: {intent} (React specifically to this)."

        conversation_text = ""
        for msg in history:
            sender = "Scammer" if msg.get("sender") == "scammer" else "You"
            conversation_text += f"{sender}: {msg.get('text', '')}\n"
        conversation_text += f"Scammer: {text_input}\nYou:"

        return system, conversation_text

    def generate_response(
        self,
        text_input: str,
        history: list,
        intent: str,
        turn_count: int = 0,
        extracted_intelligence: dict = None,
        session_id: str = None,
    ):
        """Returns LLM-generated reply string, or None if LLM is unavailable."""
        if not self.provider:
            print("[LLM] ⚠️  No provider — cannot generate reply.")
            return None

        system, conversation_text = self._build_prompt(
            text_input, history, intent, turn_count, extracted_intelligence
        )

        full_prompt = f"{system}\n\nCONVERSATION HISTORY:\n{conversation_text}"

        try:
            response = self.client.models.generate_content(
                model=self.active_model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=100,
                ),
            )
            return response.text.replace("You:", "").strip()
        except Exception as e:
            print(f"[LLM] ❌ generate_response failed: {e}")
            return None


    def generate_insight(self, conversation_text: str):
        """Returns insight dict from LLM, or None if LLM is unavailable."""
        if not self.provider:
            print("[LLM] ⚠️  No provider — cannot generate insight.")
            return None

        prompt = f"""
Analyze this conversation. Output JSON ONLY, no markdown:
{{
    "scamType": "one of [bank_fraud, upi_fraud, phishing, kyc_fraud, tech_support, lottery_scam, unknown]",
    "agentNotes": "Brief summary of tactics.",
    "confidence": 0.9
}}

Conversation:
{conversation_text}
"""

        try:
            response = self.client.models.generate_content(
                model=self.active_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=200,
                ),
            )
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            if "{" in clean_text:
                clean_text = clean_text[clean_text.find("{"):clean_text.rfind("}") + 1]
            return json.loads(clean_text)
        except Exception as e:
            print(f"[LLM] ❌ generate_insight failed: {e}")
            return None

