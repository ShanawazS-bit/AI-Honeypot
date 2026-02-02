from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from .serializers import ScamInputSerializer
import requests
import re
import threading

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
        
        # 1. Intelligence Extraction (Regex / Keywords)
        intelligence = {
            "bankAccounts": set(),
            "upiIds": set(),
            "phishingLinks": set(),
            "phoneNumbers": set(),
            "suspiciousKeywords": set()
        }
        
        full_text = text_input + " " + " ".join([m.get("text", "") for m in history])
        
        # Regex Patterns
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

        # 2. Agent Response Generation
        # Simple persona logic or use the existing HoneypotAgent logic if compatible.
        # For reliability, let's use a simple robust response generator based on keywords.
        
        reply = "I am confused. Why do I need to do this?"
        lower_input = text_input.lower()
        
        if "otp" in lower_input:
            reply = "I didn't receive any OTP. Can you send it again?"
        elif "bank" in lower_input or "account" in lower_input:
            reply = "Oh no! My account is in which bank? I have many."
        elif "upi" in lower_input:
            reply = "I don't know my UPI ID. Is it on the card?"
        elif "link" in lower_input:
            reply = "I am scared to click links. Can you tell me the website name?"
        elif "urgent" in lower_input:
            reply = "Please don't rush me, I am an old person. What should I do?"
            
        # 3. Callback Handling
        # The prompt says: "When Should This Be Sent? ... After Scam intent is confirmed ... engagement is finished"
        # Since we are request-response, we might strictly trigger it on every defined "scam" message 
        # OR we assume every request is a step.
        # To be safe and compliant, we will fire the callback asynchronously for every request that looks like a scam.
        
        total_messages = len(history) + 1
        if intelligence["suspiciousKeywords"]:
             # Fire and forget callback
             t = threading.Thread(target=run_callback, args=(session_id, intelligence, total_messages))
             t.start()

        # 4. Response
        return Response({
            "status": "success",
            "reply": reply
        })
