from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from src.honeypot import HoneypotAgent
from src.models import CallState
import uuid

class HoneypotEndpoint(APIView):
    """
    API Endpoint to interact with the Honeypot Agent.
    """
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    
    def get(self, request):
        """
        Health check endpoint.
        """
        return Response({"status": "honeyot_active", "message": "Send POST request to chat."})

    def post(self, request):
        api_key = request.headers.get("x-api-key")
        
        # Log headers for debugging
        print(f"Headers: {request.headers}")
        
        if not api_key:
            return Response(
                {"error": "Missing x-api-key header"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        print(f"Received API Key: {api_key}")

        # Get input text safely
        try:
            data = request.data
            print(f"Request Data: {data}")
            
            text_input = ""
            if isinstance(data, dict):
                text_input = data.get("text", "") or data.get("input", "") or data.get("message", "")
            elif isinstance(data, str):
                text_input = data
                
        except Exception as e:
            print(f"Error parsing data: {e}")
            text_input = ""
        
        # Initialize Agent
        agent = HoneypotAgent()
        agent.activate(CallState(call_id=str(uuid.uuid4())))
        
        response_text = agent.generate_response(text_input)
        
        return Response({
            "response": response_text,
            "status": "active",
            "agent": agent.persona
        })
