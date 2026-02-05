from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from .serializers import ScamInputSerializer
import requests
import re
import threading

# Global Gemini Service for Lazy Loading
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
             # Try dynamic response with session awareness
             reply = gemini_service.generate_response(text_input, history, "UNKNOWN", session_id=session_id)
        
        # 2. Background Processing (Intelligence Extraction + Callback)
        def process_background(session_id, text_input, history):
            # Intelligence Extraction (Regex + Keywords)
            intelligence = {
                "bankAccounts": set(),
                "upiIds": set(),
                "phishingLinks": set(),
                "phoneNumbers": set(),
                "suspiciousKeywords": set()
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
            
            scam_keywords = ["block", "suspend", "kyc", "verify", "urgent", "link", "pan", "aadhar", "otp",
                             "arrest", "police", "legal", "pay", "account", "upi", "bank", "card"]
            for kw in scam_keywords:
                if kw in full_text.lower():
                    intelligence["suspiciousKeywords"].add(kw)

            # Fire Callback if suspicious
            if intelligence["suspiciousKeywords"] or intelligence["phoneNumbers"] or intelligence["upiIds"]:
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
            print("  » Gemini failed/skipped. Using intelligent keyword fallback.")
            
            lower_input = text_input.lower()
            
            # Intelligent keyword-based fallback with questions
            if any(word in lower_input for word in ["hello", "hi", "hey", "good morning", "good evening"]):
                reply = "Hello beta... who is this? Why you are calling me?"
            elif any(word in lower_input for word in ["police", "officer", "authority", "government", "department"]):
                reply = "Oh god, police? What happened? What is your name and badge number?"
            elif any(word in lower_input for word in ["arrest", "jail", "legal", "court", "case"]):
                reply = "Arrest? Oh my god I am very scared! What I did wrong? Should I call my son?"
            elif any(word in lower_input for word in ["urgent", "immediately", "now", "quick", "hurry"]):
                reply = "Wait wait, I am old person... what is so urgent? Tell me slowly please."
            elif any(word in lower_input for word in ["block", "suspend", "freeze", "deactivate"]):
                reply = "My account is block? Which bank? How to fix it? You have customer care number?"
            elif any(word in lower_input for word in ["kyc", "verify", "verification", "update"]):
                reply = "KYC? What is that? My son did all this when opening account... what I need to do?"
            elif any(word in lower_input for word in ["pay", "money", "amount", "rupees", "payment"]):
                reply = "Pay money? How much? Where to send? I don't know how to do online payment..."
            elif any(word in lower_input for word in ["account", "card", "upi", "bank"]):
                reply = "Which account you are talking? I have SBI and HDFC... which one?"
            elif any(word in lower_input for word in ["otp", "code", "password", "pin"]):
                reply = "OTP? You mean the number message? I didn't get any... where it will come?"
            elif any(word in lower_input for word in ["link", "download", "install", "app"]):
                reply = "Download what? I don't know how to download... can you tell my son? What is the name?"
            elif any(word in lower_input for word in ["name", "who", "speaking"]):
                reply = "Haan I am here... but who are you? Which company you calling from?"
            else:
                # Even the catch-all should ask a question
                reply = "Sorry beta, I didn't understand properly... can you repeat? Who is calling?"

        # 4. Response
        return Response({
            "status": "success",
            "reply": reply
        })
