from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from src.honeypot import HoneypotAgent
from .serializers import HoneypotRequestSerializer
from src.models import CallState
import uuid

# Initialize agent globally or per request depending on state requirements.
# For this simple tester, a global instance or per-request is fine.
# Note: HoneypotAgent is stateful (is_active). 
# We might need to ensure it's activated for the test.

class HoneypotEndpoint(APIView):
    """
    API Endpoint to interact with the Honeypot Agent.
    """
    
    def post(self, request):
        api_key = request.headers.get("x-api-key")
        
        # Basic validation - in real app, check against DB or env
        if not api_key:
            return Response(
                {"error": "Missing x-api-key header"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        # For the purpose of the tester, we accept any key or specific one.
        # Let's log it.
        print(f"Received API Key: {api_key}")

        # Get input text
        data = request.data
        text_input = data.get("text", "")
        
        # Initialize/Get Agent
        agent = HoneypotAgent()
        
        # Force activate for the test if needed, or check logic
        # agent.activate(CallState(call_id="test-call")) 
        # The generate_response method checks self.is_active.
        # Let's activate it to ensure we get a response.
        agent.activate(CallState(call_id=str(uuid.uuid4())))
        
        response_text = agent.generate_response(text_input)
        
        return Response({
            "response": response_text,
            "status": "active",
            "agent": agent.persona
        })
