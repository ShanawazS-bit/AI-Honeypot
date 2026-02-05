from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from .serializers import ScamInputSerializer
import requests
import re
import threading

# Global Semantic Analyzer for Lazy Loading
sem_analyzer = None
gemini_service = None

def run_callback(session_id, intelligence, messages_count):
    """
    Sends the mandatory callback to GUVI evaluation endpoint.
    """
    url = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    
    # Format intelligence as list of strings as per example
    payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": messages_count,
        "extractedIntelligence": {
            "bankAccounts": list(intelligence.get("bankAccounts", [])),
            "upiIds": list(intelligence.get("upiIds", [])),
            "phishingLinks": list(intelligence.get("phishingLinks", [])),
            "phoneNumbers": list(intelligence.get("phoneNumbers", [])),
            "suspiciousKeywords": list(intelligence.get("suspiciousKeywords", []))
        },
        "agentNotes": "Scammer used urgency tactics and payment redirection. Automated extraction."
    }
    
    try:
        print(f"Sending Callback for {session_id}...")
        resp = requests.post(url, json=payload, timeout=5)
        print(f"Callback Status: {resp.status_code}, Body: {resp.text}")
    except Exception as e:
        print(f"Callback Failed: {e}")

class HoneypotEndpoint(APIView):
    """
    API Endpoint for Agentic Honey-Pot Problem Statement.
    """
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get(self, request):
        """
        Health Check for Browser Access.
        """
        return Response({
            "status": "online", 
            "message": "Honeypot API is running. Send POST requests to this endpoint for scam detection."
        })

    def post(self, request):
        api_key = request.headers.get("x-api-key")
        print(f"Headers: {request.headers}")
        
        if not api_key:
            return Response(
                {"status": "error", "message": "Missing Valid API Key"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Parse Input
        serializer = ScamInputSerializer(data=request.data)
        if not serializer.is_valid():
            print(f"Serializer Errors: {serializer.errors}")
            # Fallback for simple "text" input if the tester uses the OLD format initially
            # But the problem statement says "Request Body Format" is strict.
            # We will try to handle graceful degradation.
            text_input = request.data.get("text") or request.data.get("input", "")
            if text_input:
                 session_id = "fallback-session"
                 history = []
            else:
                 return Response({"status": "error", "message": "Invalid Request Format"}, status=400)
        else:
            data = serializer.validated_data
            session_id = data.get("sessionId")
            msg_obj = data.get("message", {})
            text_input = msg_obj.get("text", "")
            history = data.get("conversationHistory", [])
        
        print(f"Processing Session: {session_id}, Input: '{text_input}'")
        
        # --- Logic Core ---
        
        # 1. Try Gemini (LLM) First - FAST PATH
        print(f"headers: {request.headers}")
        
        reply = None
        global gemini_service
        if gemini_service is None:
             try:
                 from src.llm_service import GeminiService
                 gemini_service = GeminiService()
             except Exception as e:
                 print(f"Failed to load LLM Service: {e}")
                 gemini_service = None

        if gemini_service:
             # Try dynamic response
             reply = gemini_service.generate_response(text_input, history, "UNKNOWN") # Risk unknown initially
        
        # 2. Background Processing (Heavy Lifting)
        # We spawn a thread to do Semantic Analysis + Callback so we don't block the User Response
        def process_background(session_id, text_input, history, intent_label=None):
            global sem_analyzer
            if sem_analyzer is None:
                 from src.semantic import SemanticAnalyzer
                 sem_analyzer = SemanticAnalyzer()
            
            # Analyze Deeply
            intent = sem_analyzer.analyze(text_input)
            print(f"  [Background] Intent: {intent.label} ({intent.confidence:.2f})")
            
            # Intelligence Extraction (Regex + Semantic)
            intelligence = {
                "bankAccounts": set(),
                "upiIds": set(),
                "phishingLinks": set(),
                "phoneNumbers": set(),
                "suspiciousKeywords": set(intent.keywords_detected)
            }
            
            full_text = text_input + " " + " ".join([m.get("text", "") for m in history])
            
            phone_pattern = r"(\+91[\-\s]?)?[6-9]\d{9}"
            upi_pattern = r"[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}"
            url_pattern = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+"
            acc_pattern = r"\b\d{9,18}\b" 

            intelligence["phoneNumbers"].update(re.findall(phone_pattern, full_text))
            intelligence["upiIds"].update(re.findall(upi_pattern, full_text))
            intelligence["phishingLinks"].update(re.findall(url_pattern, full_text))
            intelligence["bankAccounts"].update(re.findall(acc_pattern, full_text))
            
            scam_keywords = ["block", "suspend", "kyc", "verify", "urgent", "link", "pan", "aadhar", "otp"]
            for kw in scam_keywords:
                if kw in full_text.lower():
                    intelligence["suspiciousKeywords"].add(kw)

            # Fire Callback if suspicious
            if intelligence["suspiciousKeywords"] or intent.label in ["PAYMENT", "URGENCY", "FEAR"]:
                 total_messages = len(history) + 1
                 run_callback(session_id, intelligence, total_messages)

        # Start Background Task
        t = threading.Thread(target=process_background, args=(session_id, text_input, history))
        t.daemon = True # Allow main program to exit even if thread is running
        t.start()

        # 3. Fallback Response (If Gemini Failed) - Slow Path
        debug_intent = "UNKNOWN"
        debug_risk = "UNKNOWN"

        if reply is None:
            print("  » Gemini failed/skipped. Waiting for Semantic Analysis (Blocking)...")
            # We strictly need to wait for semantic analysis here to generate a fallback reply
            # But the user wants speed. We will use a regex-based lightweight fallback for speed if possible,
            # Or accept the blocking hit only when Gemini fails.
            
            # Re-run semantic logic inline only if we absolutely need it for the reply
            global sem_analyzer
            if sem_analyzer is None:
                 from src.semantic import SemanticAnalyzer
                 sem_analyzer = SemanticAnalyzer()
            intent = sem_analyzer.analyze(text_input) # This loads the model (Slow)
            debug_intent = intent.label

            # Re-calculate risk for fallback if needed (not explicitly in instruction, but good practice)
            from src.models import CallState, ParalinguisticFeatures
            from src.sequencer import BehavioralSequencer
            from src.scorer import FraudRiskScorer
            sequencer = BehavioralSequencer()
            scorer = FraudRiskScorer()
            call_state = CallState(call_id=session_id)
            sequencer.update_state(call_state, intent)
            dummy_para = ParalinguisticFeatures()
            risk_score = scorer.calculate_score(call_state, dummy_para, intent)
            debug_risk = risk_score.level
            
            lower_input = text_input.lower()
            if intent.label == "GREETING":
                reply = "Hello? Who is this calling?"
            # ... (Rest of fallback logic matches existing)
            elif intent.label == "AUTHORITY":
                reply = "Oh, from the headquarters? I didn't know there was an issue."
            elif intent.label == "FEAR":
                reply = "Oh my god, am I in trouble? I am very scared!"
            elif intent.label == "URGENCY":
                reply = "I'm trying to find my glasses, please wait a moment... don't rush me."
            elif intent.label == "PAYMENT":
                reply = "My grandson usually handles the money. Which card do you need? The blue one?"
            elif intent.label == "NEUTRAL":
                if "otp" in lower_input:
                    reply = "I didn't receive any OTP. Can you send it again?"
                elif "bank" in lower_input:
                    reply = "Oh no! My account is in which bank? I have many."
                else:
                    reply = "I didn't quite catch that. What did you say?"
            else:
                reply = "I am a bit confused, could you explain that?"

        # 4. Response
        return Response({
            "status": "success",
            "reply": reply,
            "debug_intent": debug_intent,
            "debug_risk": debug_risk
        })
