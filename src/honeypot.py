import time
from .models import CallState

class HoneypotAgent:
    """
    Autonomous Adversarial Agent (The 'Honeypot').
    
    Activated when Risk Score triggers the threshold.
    Goal:
    1. Waste scammer time (stall)
    2. Extract intelligence
    3. Protect the user (take over audio output)
    """
    
    def __init__(self):
        self.is_active = False
        self.persona = "Vulnerable Elderly Person"
        
    def activate(self, call_state: CallState):
        """
        Triggers the agent to take over the call.
        """
        if self.is_active:
            return
            
        self.is_active = True
        print("\n" + "="*60)
        print(f"🚨 HONEYPOT AGENT ACTIVATED 🚨")
        print(f"Persona: {self.persona}")
        print(f"Taking control of Call ID: {call_state.call_id}")
        print("="*60 + "\n")
        
    def generate_response(self, text_input: str) -> str:
        """
        Generates a stalling response. 
        (In full system, this would use LLM generation).
        """
        if not self.is_active:
             return ""
             
        # Simple simulated responses for the demo
        print(f"[Honeypot] Hearing: '{text_input}'")
        response = "Oh dear, I'm not very good with computers... can you say that again slower?"
        print(f"[Honeypot] Speaking: '{response}'")
        return response
