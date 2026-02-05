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
        
        # --- Logic Core (AI Pipeline) ---
        
        # 1. Semantic Analysis
        # Use the global analyzer instance if available, otherwise fallback
        global sem_analyzer
        if sem_analyzer is None:
             # Lazy load if not ready (though it should be loaded at module level)
             from src.semantic import SemanticAnalyzer
             sem_analyzer = SemanticAnalyzer()

        intent = sem_analyzer.analyze(text_input)
        print(f"  » Intent: {intent.label} ({intent.confidence:.2f})")
        
        # 2. Sequencing & Scoring
        # We need to reconstruct or approximate state since we are stateless.
        # For this hackathon demo, we will use a fresh state populated with history logic if needed,
        # or just simply check the current frame's risk.
        
        from src.models import CallState, ParalinguisticFeatures
        from src.sequencer import BehavioralSequencer
        from src.scorer import FraudRiskScorer
        
        # Initialize helper components on the fly (lightweight)
        sequencer = BehavioralSequencer()
        scorer = FraudRiskScorer()
        
        # Create a transient CallState
        call_state = CallState(call_id=session_id)
        
        # approximate current phase based on intent
        new_phase = sequencer.update_state(call_state, intent)
        
        # Calculate Risk (Mocking paralinguistics as we only have text)
        dummy_para = ParalinguisticFeatures() # Defaults to 0
        risk_score = scorer.calculate_score(call_state, dummy_para, intent)
        
        print(f"  » Risk Score: {risk_score.score:.2f} [{risk_score.level}]")
        
        # 3. Agent Response Generation (Hybrid: LLM -> Semantic Fallback)
        global gemini_service
        if gemini_service is None:
             from src.llm_service import GeminiService
             gemini_service = GeminiService()
             
        # Try dynamic response
        reply = gemini_service.generate_response(text_input, history, risk_score.level)
        
        if reply is None:
            # Fallback to Semantic Templates if LLM fails (Rate Limit, etc.)
            print("  » LLM failed, using Semantic Fallback.")
            if intent.label == "GREETING":
                reply = "Hello? Who is this calling?"
            elif intent.label == "AUTHORITY":
                reply = "Oh, from the headquarters? I didn't know there was an issue."
            elif intent.label == "FEAR":
                reply = "Oh my god, am I in trouble? Please don't arrest me!"
            elif intent.label == "URGENCY":
                reply = "I'm trying to find my glasses, please wait a moment... don't rush me."
            elif intent.label == "PAYMENT":
                reply = "My grandson usually handles the money. Which card do you need? The blue one?"
            elif intent.label == "NEUTRAL":
                reply = "I didn't quite catch that. What did you say?"
            else:
                reply = "I am a bit confused, could you explain that?"

        print(f"  » Agent Reply: {reply}")

        # 4. Intelligence Extraction (for Callback)
        # We map the semantic intent/keywords to the output format
        
        intelligence = {
            "bankAccounts": [],
            "upiIds": [],
            "phishingLinks": [],
            "phoneNumbers": [],
            "suspiciousKeywords": intent.keywords_detected
        }

        # 5. Callback Handling
        # If risk is high or we detected scam patterns, send callback
        if risk_score.level in ["HIGH", "CRITICAL"] or intent.label in ["PAYMENT", "URGENCY", "FEAR"]:
             total_messages = len(history) + 1
             # Fire and forget callback
             t = threading.Thread(target=run_callback, args=(session_id, intelligence, total_messages))
             t.daemon = True
             t.start()

        # 6. Response
        return Response({
            "status": "success",
            "reply": reply,
            "debug_intent": intent.label,
            "debug_risk": risk_score.level
        })
