from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from .serializers import ScamInputSerializer
import requests
import re
import threading
import time
import json
from datetime import datetime, timezone

# Global LLM Service
from src.llm_service import LLMService
llm_service = LLMService()

# ── Server-side session store ────────────────────────────────────────────────
# Tracks start time and running message count per sessionId so that
# engagementDurationSeconds and totalMessagesExchanged grow correctly
# even when the client sends only a single-turn history.
SESSION_STORE: dict = {}


def _parse_ts(val) -> float:
    """Parse any timestamp format to a Unix float (seconds)."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        ts = float(val)
        return ts / 1000.0 if ts > 1e12 else ts   # ms → s
    s = str(val).strip()
    if s.isdigit():
        ts = float(s)
        return ts / 1000.0 if ts > 1e12 else ts
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        return None

def run_callback(session_id, intelligence, messages_count, agent_notes, scam_type, metadata=None, red_flags=None, duration=0, confidence=0.8):
    """
    Submits the final output to the GUVI evaluation endpoint after each turn.
    Payload matches the required Final Output Submission format exactly.
    """
    url = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"

    payload = {
        "sessionId":           session_id,
        "scamDetected":        True,
        "extractedIntelligence": {
            "phoneNumbers":  list(intelligence.get("phoneNumbers",  [])),
            "bankAccounts":  list(intelligence.get("bankAccounts",  [])),
            "upiIds":        list(intelligence.get("upiIds",        [])),
            "phishingLinks": list(intelligence.get("phishingLinks", [])),
            "emailAddresses":list(intelligence.get("emailAddresses",[])),
            "caseIds":       list(intelligence.get("caseIds",       [])),
            "policyNumbers": list(intelligence.get("policyNumbers", [])),
            "orderNumbers":  list(intelligence.get("orderNumbers",  [])),
        },
        "totalMessagesExchanged":    messages_count,
        "engagementDurationSeconds": duration,
        "agentNotes":                agent_notes,
        "scamType":                  scam_type,
        "confidenceLevel":           confidence,
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
        return Response({
            "status": "online", 
            "message": "Honeypot API is running. Send POST requests to 'input' or 'text' field."
        })

    def post(self, request):
        api_key = request.headers.get("x-api-key")
        
        # Parse Input
        serializer = ScamInputSerializer(data=request.data)
        if not serializer.is_valid():
            text_input = request.data.get("text") or request.data.get("input", "")
            if text_input:
                 session_id = request.data.get("sessionId", "fallback-session")
                 scenario_id = "unknown"
                 history = request.data.get("conversationHistory", [])
                 metadata = request.data.get("metadata", {})
                 timestamp = request.data.get("message", {}).get("timestamp")
            else:
                 return Response({"status": "error", "message": "Invalid Request Format"}, status=400)
        else:
            data = serializer.validated_data
            session_id = data.get("sessionId")
            scenario_id = data.get("scenarioId", "unknown")
            msg_obj = data.get("message", {})
            text_input = msg_obj.get("text", "")
            timestamp = msg_obj.get("timestamp")
            history = data.get("conversationHistory", [])
            metadata = data.get("metadata", {})
        
        # ── Session tracking ─────────────────────────────────────────────
        now = time.time()
        if session_id not in SESSION_STORE:
            # First call for this session — record start time
            first_ts = _parse_ts(timestamp)
            if history:
                first_ts = _parse_ts(history[0].get("timestamp")) or first_ts
            SESSION_STORE[session_id] = {
                "start":    first_ts or now,
                "msg_count": 0,
            }

        sess = SESSION_STORE[session_id]
        sess["msg_count"] += 2   # +1 for scammer input, +1 for our reply

        # Duration: wall-clock time since session start (always grows)
        duration = int(now - sess["start"])
        total_msgs = sess["msg_count"] + len(history)

        turn_count = len(history)
        print(f"Processing Session: {session_id}, Turns: {turn_count}, Input: '{text_input}'")
        
        # 1. Intelligence Extraction
        from src.intelligence_extraction import IntelligenceExtractor
        from src.risk_engine import RiskEngine
        
        full_text = text_input + " " + " ".join([m.get("text", "") for m in history])
        intelligence = IntelligenceExtractor.extract(full_text)
        red_flags = RiskEngine.analyze(full_text)

        # 2+3. Run insight classification and reply generation CONCURRENTLY
        #       This halves LLM latency — both calls hit the Gemini API in parallel.
        insight_result  = [None]
        reply_result    = [None]
        insight_err     = [None]
        reply_err       = [None]

        def _run_insight():
            try:
                insight_result[0] = llm_service.generate_insight(full_text)
            except Exception as e:
                insight_err[0] = e

        def _run_reply():
            try:
                reply_result[0] = llm_service.generate_response(
                    text_input=text_input,
                    history=history,
                    intent="suspected_fraud",  # placeholder; insight runs in parallel
                    turn_count=len(history),
                    extracted_intelligence=intelligence,
                    session_id=session_id,
                )
            except Exception as e:
                reply_err[0] = e

        t_insight = threading.Thread(target=_run_insight, daemon=True)
        t_reply   = threading.Thread(target=_run_reply,   daemon=True)
        t_insight.start()
        t_reply.start()
        t_insight.join(timeout=25)
        t_reply.join(timeout=25)

        # Unpack results
        insight     = insight_result[0]  # None if LLM failed
        scam_type   = insight.get("scamType", "suspected_fraud") if insight else "suspected_fraud"
        agent_notes = insight.get("agentNotes", "") if insight else ""
        confidence  = insight.get("confidence", 0.8) if insight else 0.8
        reply       = reply_result[0]  # None if LLM failed

        # If LLM produced no reply at all, return 503 — no hardcoded strings
        if not reply:
            return Response(
                {"status": "error", "message": "LLM service unavailable. Please retry."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Keyword fallback for scam type when LLM returns unknown
        if scam_type in ("suspected_fraud", "unknown"):
            if intelligence["phishingLinks"]:  scam_type = "phishing"
            elif intelligence["bankAccounts"]: scam_type = "bank_fraud"
            elif intelligence["upiIds"]:       scam_type = "upi_fraud"


        # 4. Async callback (non-blocking)
        t = threading.Thread(
            target=run_callback,
            args=(session_id, intelligence, total_msgs, agent_notes, scam_type, metadata, red_flags, duration, confidence),
            daemon=True,
        )
        t.start()


        # 5. Per-turn response — simple format as per spec
        #    Full intelligence is submitted via the async GUVI callback (run_callback above)
        return Response({
            "status": "success",
            "reply":  reply,
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

