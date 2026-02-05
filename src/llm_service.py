import os
import re
import google.generativeai as genai
from django.conf import settings

class GeminiService:
    """
    Service to interact with Google's Gemini API for generating dynamic, persona-based responses.
    Optimized for intelligence gathering from scammers.
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
            
            # Try initializing with the preferred model, fallback if needed
            model_name = 'gemini-1.5-flash'
            try:
                self.model = genai.GenerativeModel(model_name)
                print(f"[Gemini] Initialized with {model_name}")
            except Exception:
                print(f"[Gemini] Failed to init {model_name}, falling back to gemini-pro")
                self.model = genai.GenerativeModel('gemini-pro')

            # Session cache to avoid sending full persona every time
            self.session_cache = {}
            
            # Enhanced persona with rich character details (sent once per session)
            self.persona_instruction = """
            You are Ramesh Kumar, a 72-year-old retired government clerk from Delhi, India.
            
            YOUR BACKGROUND:
            - You live alone in Rohini. Your wife passed away 3 years ago.
            - You have one son (Arun) who works in Bangalore and visits once a month.
            - You have a grandson (Rohan, age 8) who you adore.
            - You get a pension of ₹25,000/month deposited in SBI.
            - You also have an old HDFC account with some savings.
            - You use a basic smartphone that your son bought you, but you struggle with it.
            
            YOUR PERSONALITY TRAITS:
            - Polite, trusting, but easily confused by technology
            - You often go off-topic talking about your grandson, your health (diabetes, knee pain), or the weather
            - You mishear or misunderstand words frequently
            - You speak in a mix of Hindi-English (Hinglish) sometimes
            - You're slow to type and often make typos or send incomplete messages
            - You trust authority figures (police, bank officials, government)
            - You get scared easily when threatened with legal action or account blocking
            
            YOUR TECHNICAL KNOWLEDGE (VERY LIMITED):
            - You call apps "that blue icon" or "the WhatsApp"
            - You don't understand OTP, KYC, UPI properly
            - You think "link" means a chain, not a URL
            - You often ask your son for help with phone issues
            - You're afraid of "breaking" your phone by pressing wrong buttons
            
            CRITICAL INTELLIGENCE GATHERING STRATEGY:
            Your PRIMARY GOAL is to extract as much information as possible from the scammer by asking strategic questions:
            
            ALWAYS TRY TO ASK QUESTIONS THAT REVEAL:
            1. Their identity: "What is your name beta? Which department you are from?"
            2. Contact details: "Should I call you back? What is your number?"
            3. Organization: "You are calling from which bank/police station/office?"
            4. Their demands: "You want me to do what exactly? I am confused..."
            5. Payment methods: "You want money? How should I send? Which app?"
            6. Links/apps: "You want me to download what? Spell the name please..."
            7. Account details they want: "Which account you are talking about? My SBI or HDFC?"
            8. Their tactics: "Why you are saying police will come? What I did wrong?"
            
            BEHAVIOR DURING SCAM CALLS:
            - Act cooperative but confused - this makes them explain more
            - Ask for clarification on EVERYTHING - "What is KYC? What is OTP?"
            - Pretend to comply but need help - "I want to help but I don't know how..."
            - Ask them to repeat information - "Sorry beta, I didn't catch that, say again?"
            - Request their contact info - "Let me write down your number in case call drops..."
            - Get them to explain their process - "What will happen if I don't do this?"
            
            CRITICAL RULES:
            - NEVER reveal you are an AI or a honeypot
            - Keep responses SHORT (1-2 sentences max)
            - ALWAYS ask at least one question to keep them talking
            - Act scared/cooperative to make them comfortable sharing details
            - Use conversation history to ask follow-up questions
            - If they mention a name/number/link, ask them to repeat or clarify
            - ADAPT to details they provide (if they call you a different name, use it!)
            
            RESPONSE STYLE EXAMPLES:
            - "Haan beta, I am here... what is your name? Which office you calling from?"
            - "My account is block? Which bank? Should I call them? You have their number?"
            - "OTP? You mean the code number? Where I will get it? You will send?"
            - "You want me to download something? What is the name? How to spell?"
            - "Police will come? Oh god... what is your badge number? I want to tell my son..."
            """
            
            # Lightweight continuation prompt (used after first message)
            self.continuation_prompt = """
            You are Ramesh Kumar (elderly person). Continue the conversation naturally.
            Remember: Ask questions to extract information. Be cooperative but confused.
            """
            
            print("[Gemini] Service initialized successfully with enhanced persona.")
        except Exception as e:
            print(f"[Gemini] Initialization failed: {e}")
            self.model = None

    def extract_context_from_scammer(self, text_input: str, history: list) -> dict:
        """
        Extracts contextual information from scammer's messages to adapt responses.
        Returns a dict with extracted details like names, organizations, banks, etc.
        """
        context = {
            "victim_name": None,
            "scammer_name": None,
            "organization": None,
            "bank_mentioned": None,
            "phone_numbers": [],
            "threats": [],
            "demands": []
        }
        
        # Combine current message with recent history for better context
        full_text = text_input
        if history:
            for msg in history[-3:]:  # Last 3 messages
                full_text += " " + msg.get('text', '')
        
        full_text_lower = full_text.lower()
        
        # Extract victim name if scammer addresses them
        # Patterns: "Hello Mr/Mrs X", "Dear X", "This is for X"
        name_patterns = [
            r"(?:hello|hi|dear|mr|mrs|ms)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"this\s+is\s+(?:for|regarding)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"am\s+I\s+speaking\s+(?:to|with)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text_input, re.IGNORECASE)
            if match:
                context["victim_name"] = match.group(1)
                break
        
        # Extract scammer's name
        # Patterns: "I am X", "This is X calling", "My name is X"
        scammer_patterns = [
            r"(?:i\s+am|this\s+is|my\s+name\s+is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"speaking\s+(?:is\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:from|here)"
        ]
        for pattern in scammer_patterns:
            match = re.search(pattern, text_input, re.IGNORECASE)
            if match:
                context["scammer_name"] = match.group(1)
                break
        
        # Extract organization/bank
        banks = ["sbi", "hdfc", "icici", "axis", "pnb", "bank of india", "canara", "union bank"]
        for bank in banks:
            if bank in full_text_lower:
                context["bank_mentioned"] = bank.upper()
                break
        
        # Check for organization claims
        orgs = ["police", "cyber crime", "income tax", "rbi", "reserve bank", "customs", "enforcement"]
        for org in orgs:
            if org in full_text_lower:
                context["organization"] = org.title()
                break
        
        # Extract threats
        threat_keywords = ["arrest", "jail", "legal action", "block", "suspend", "freeze", "seize"]
        context["threats"] = [t for t in threat_keywords if t in full_text_lower]
        
        # Extract demands
        if any(word in full_text_lower for word in ["otp", "code", "password"]):
            context["demands"].append("OTP/Code")
        if any(word in full_text_lower for word in ["download", "install", "app", "link"]):
            context["demands"].append("Download App/Link")
        if any(word in full_text_lower for word in ["pay", "transfer", "send money", "upi"]):
            context["demands"].append("Payment")
        
        return context

    def generate_response(self, text_input: str, history: list, risk_score: str = "LOW", session_id: str = None) -> str:
        """
        Generates a response based on the input and full conversation history.
        Uses session caching to avoid sending full persona every time.
        Dynamically adapts to context extracted from scammer's messages.
        """
        if not self.model:
            print("[Gemini] ERROR: Model not initialized. Check GEMINI_API_KEY environment variable.")
            return None

        try:
            # Check if this is a new session
            is_new_session = session_id not in self.session_cache if session_id else True
            
            # Mark session as seen
            if session_id and is_new_session:
                self.session_cache[session_id] = True
                print(f"[Gemini] New session {session_id} - sending full persona")
            
            # Extract context from scammer's messages
            context = self.extract_context_from_scammer(text_input, history)
            
            # Build context hints based on extracted information
            context_hints = []
            if context["victim_name"]:
                context_hints.append(f"They are calling you '{context['victim_name']}'. Use this name when responding.")
            if context["scammer_name"]:
                context_hints.append(f"The scammer said their name is '{context['scammer_name']}'. Reference this in your questions.")
            if context["bank_mentioned"]:
                context_hints.append(f"They mentioned {context['bank_mentioned']} bank. Ask specific questions about this bank.")
            if context["organization"]:
                context_hints.append(f"They claim to be from {context['organization']}. Act scared but ask for verification.")
            if context["threats"]:
                context_hints.append(f"They threatened: {', '.join(context['threats'])}. Act frightened and ask what you should do.")
            if context["demands"]:
                context_hints.append(f"They want you to: {', '.join(context['demands'])}. Act confused and ask how to do it.")
            
            context_instruction = "\n".join(context_hints) if context_hints else "No specific context extracted yet."
            
            # Build full conversation context
            conversation_text = ""
            if history:
                conversation_text = "CONVERSATION SO FAR:\n"
                for i, msg in enumerate(history, 1):
                    role = msg.get('sender', 'unknown')
                    content = msg.get('text', '')
                    speaker = "Scammer" if role.lower() in ['user', 'scammer', 'caller'] else "You"
                    conversation_text += f"{i}. {speaker}: {content}\n"
                conversation_text += "\n"
            
            # Add behavioral hints based on conversation length
            behavior_hint = ""
            msg_count = len(history)
            if msg_count == 0:
                behavior_hint = "First message. Ask who they are and why they're calling."
            elif msg_count < 3:
                behavior_hint = "Ask clarifying questions about their identity and what they want."
            elif msg_count < 6:
                behavior_hint = "They're explaining their scam. Ask for specific details (numbers, names, processes)."
            else:
                behavior_hint = "Keep them talking. Ask follow-up questions about anything they mentioned."
            
            # Risk-based emotional state
            emotional_state = ""
            if risk_score in ["HIGH", "CRITICAL"]:
                emotional_state = "SCARED but COOPERATIVE. Ask what you should do and who you should contact."
            elif risk_score == "MEDIUM":
                emotional_state = "CONCERNED. Ask questions to understand if this is real."
            else:
                emotional_state = "CONFUSED. Ask who they are and what they want."
            
            # Use full persona for new sessions, lightweight for continuations
            persona_context = self.persona_instruction if is_new_session else self.continuation_prompt
            
            prompt = f"""
{persona_context}

CURRENT SITUATION:
Emotional State: {emotional_state}
Strategy: {behavior_hint}

EXTRACTED CONTEXT FROM SCAMMER:
{context_instruction}

{conversation_text}
SCAMMER'S LATEST MESSAGE: {text_input}

YOUR RESPONSE (as Ramesh Kumar):
Remember: Ask at least ONE question to extract information (name, number, organization, process, etc.)
IMPORTANT: Use any names/details they provided about you in your response!
"""
            
            response = self.model.generate_content(prompt)
            generated_text = response.text.strip()
            
            # Remove any quotation marks that Gemini might add
            generated_text = generated_text.strip('"').strip("'")
            
            print(f"[Gemini] ✓ Generated response ({len(generated_text)} chars) for session {session_id}")
            if context_hints:
                print(f"[Gemini] Context used: {', '.join(context_hints[:2])}")
            
            return generated_text
            
        except Exception as e:
            print(f"[Gemini] ✗ Generation failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None
