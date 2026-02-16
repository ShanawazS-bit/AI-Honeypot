from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from .serializers import ScamInputSerializer
import requests
import re
import threading
import json

# Global Gemini Service for Lazy Loading
gemini_service = None

def run_callback(session_id, intelligence, messages_count, agent_notes, scam_type, metadata=None):
    """
    Sends the mandatory callback to GUVI evaluation endpoint.
    """
    url = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    
    # Format intelligence as list of strings as per example
    payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "scamType": scam_type,
        "totalMessagesExchanged": messages_count,
        "extractedIntelligence": {
            "bankAccounts": list(intelligence.get("bankAccounts", [])),
            "upiIds": list(intelligence.get("upiIds", [])),
            "phishingLinks": list(intelligence.get("phishingLinks", [])),
            "phoneNumbers": list(intelligence.get("phoneNumbers", [])),
            "suspiciousKeywords": list(intelligence.get("suspiciousKeywords", []))
        },
        "agentNotes": agent_notes
    }
    
    if metadata:
        payload["metadata"] = metadata
    
    try:
        print(f"Sending Callback for {session_id}...")
        # print(json.dumps(payload, indent=2)) # Debug
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
        # print(f"Headers: {request.headers}")
        
        if not api_key:
            return Response(
                {"status": "error", "message": "Missing Valid API Key"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Parse Input
        serializer = ScamInputSerializer(data=request.data)
        if not serializer.is_valid():
            print(f"Serializer Errors: {serializer.errors}")
            text_input = request.data.get("text") or request.data.get("input", "")
            if text_input:
                 session_id = "fallback-session"
                 scenario_id = "unknown"
                 history = []
                 metadata = {}
            else:
                 return Response({"status": "error", "message": "Invalid Request Format"}, status=400)
        else:
            data = serializer.validated_data
            session_id = data.get("sessionId")
            scenario_id = data.get("scenarioId", "unknown")
            msg_obj = data.get("message", {})
            text_input = msg_obj.get("text", "")
            history = data.get("conversationHistory", [])
            metadata = data.get("metadata", {})
        
        print(f"Processing Session: {session_id}, Scenario: {scenario_id}, Input: '{text_input}'")
        
        # --- Logic Core ---
        
        # 1. Try Gemini (LLM) First - FAST PATH
        # SKIPPED AS PER USER REQUEST - Falling back to logic
        reply = None
        
        # 2. Intelligence Extraction (Regex + Keywords)
        intelligence = {
            "bankAccounts": set(),
            "upiIds": set(),
            "phishingLinks": set(),
            "phoneNumbers": set(),
            "suspiciousKeywords": set()
        }
        
        # Combine text for analysis
        full_text = text_input + " " + " ".join([m.get("text", "") for m in history])
        
        # Improved Regex Patterns
        phone_pattern = r"(?:(?:\+91[\-\s]?)|(?<!\d))[6-9]\d{9}\b"
        upi_pattern = r"[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}"
        url_pattern = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+"
        acc_pattern = r"\b\d{9,18}\b" 

        found_phones = set(re.findall(phone_pattern, full_text))
        found_upis = set(re.findall(upi_pattern, full_text))
        found_links = set(re.findall(url_pattern, full_text))
        found_accounts = set(re.findall(acc_pattern, full_text))
        
        # Filter: Remove phone numbers from bank accounts
        clean_accounts = set()
        for acc in found_accounts:
            is_phone = False
            for ph in found_phones:
                if acc in ph:
                    is_phone = True
                    break
            if not is_phone:
                    clean_accounts.add(acc)
        
        intelligence["phoneNumbers"].update(found_phones)
        intelligence["upiIds"].update(found_upis)
        intelligence["phishingLinks"].update(found_links)
        intelligence["bankAccounts"].update(clean_accounts)
        
        scam_keywords = ["block", "suspend", "kyc", "verify", "urgent", "link", "pan", "aadhar", "otp",
                            "arrest", "police", "legal", "pay", "account", "upi", "bank", "card"]
        for kw in scam_keywords:
            if kw in full_text.lower():
                intelligence["suspiciousKeywords"].add(kw)

        # 3. Determine Scam Type & Notes
        scam_type = scenario_id if scenario_id != "unknown" else "suspected_fraud"
        
        # If scenarioId is unknown, try to guess
        if scam_type == "suspected_fraud":
            if intelligence["phishingLinks"]:
                scam_type = "phishing"
            elif intelligence["bankAccounts"] or "bank" in intelligence["suspiciousKeywords"]:
                scam_type = "bank_fraud"
            elif intelligence["upiIds"] or "upi" in intelligence["suspiciousKeywords"]:
                scam_type = "upi_fraud"

        agent_notes = f"Detected {scam_type} attempt. "
        if intelligence["suspiciousKeywords"]:
            agent_notes += f"Keywords found: {', '.join(list(intelligence['suspiciousKeywords'])[:3])}. "
        if intelligence["bankAccounts"]:
             agent_notes += "Bank account details extracted. "
        if intelligence["phishingLinks"]:
             agent_notes += "Phishing link detected. "
        if not intelligence["suspiciousKeywords"] and not intelligence["bankAccounts"]:
             agent_notes = "Conversation analysis indicates potential social engineering."

        # 4. Fire Callback (Async)
        if intelligence["suspiciousKeywords"] or intelligence["phoneNumbers"] or intelligence["upiIds"]:
                 total_messages = len(history) + 1
                 t = threading.Thread(target=run_callback, args=(session_id, intelligence, total_messages, agent_notes, scam_type, metadata))
                 t.daemon = True
                 t.start()

        # 5. Fallback Response (Rule-based)
        if reply is None:
            lower_input = text_input.lower()
            if any(word in lower_input for word in ["hello", "hi", "hey"]):
                reply = "Hello... who is this?"
            elif any(word in lower_input for word in ["police", "officer"]):
                reply = "Police? What happened? What is your badge number?"
            elif any(word in lower_input for word in ["urgent", "block"]):
                reply = "Wait, I am old... tell me slowly. What is blocked?"
            elif any(word in lower_input for word in ["otp", "code"]):
                reply = "OTP? I didn't get any code... where it comes?"
            else:
                # Context-aware fallback based on scam type
                if scam_type == "bank_fraud":
                     reply = "My bank account? Oh god... which bank is this? SBI or HDFC?"
                elif scam_type == "upi_fraud":
                     reply = "Cashback? Really? How do I get it? I am not good with phone."
                elif scam_type == "phishing":
                     reply = "Click link? I cannot see properly... what is the website name?"
                else:
                     reply = "Sorry, I didn't understand. Can you repeat?"

        # 6. Response with ALL fields
        return Response({
            "status": "success",
            "sessionId": session_id,
            "reply": reply,
            "scamDetected": True,
            "scamType": scam_type,
            "extractedIntelligence": {k: list(v) for k, v in intelligence.items()},
            "agentNotes": agent_notes
        })

class CallSessionView(APIView):
    """
    API endpoint for managing call sessions from Android app.
    """
    parser_classes = [JSONParser]
    
    def post(self, request):
        """
        Start a new call session.
        Expected payload: {"phone_number": "1234567890"}
        Returns: {"session_id": "uuid", "status": "started"}
        """
        phone_number = request.data.get('phone_number', 'Unknown')
        session_id = str(__import__('uuid').uuid4())
        
        # Store session metadata (in production, use database)
        # For now, we'll rely on the WebSocket consumer to handle this
        
        return Response({
            "status": "success",
            "session_id": session_id,
            "message": "Session started. Connect to WebSocket for audio streaming."
        })

class CallReportView(APIView):
    """
    API endpoint for retrieving call analysis reports.
    """
    parser_classes = [JSONParser]
    
    def get(self, request, session_id):
        """
        Retrieve the analysis report for a completed call session.
        """
        import os
        import json
        from django.conf import settings
        
        # Construct report file path
        log_dir = getattr(settings, 'SESSION_LOG_DIR', os.path.join(settings.BASE_DIR, 'scam_logs'))
        report_path = os.path.join(log_dir, f'session_{session_id}.json')
        
        # Check if report exists
        if not os.path.exists(report_path):
            return Response({
                "status": "error",
                "message": "Report not found. Session may still be processing or does not exist."
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Read and return report
        try:
            with open(report_path, 'r') as f:
                report_data = json.load(f)
            
            return Response({
                "status": "success",
                "report": report_data
            })
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"Error reading report: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

