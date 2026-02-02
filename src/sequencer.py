from typing import List, Dict, Tuple
from .models import CallState, SemanticIntent

class BehavioralSequencer:
    """
    Finite State Machine (FSM) that tracks the narrative progression of the call.
    
    Scams typically follow a rigid script:
    1. START
    2. GREETING (Establish contact)
    3. AUTHORITY (Establish false credibility, e.g. "I'm from Amazon")
    4. FEAR (Create a problem, e.g. "Your account is hacked")
    5. URGENCY (Pressure to act fast, e.g. "Do it now")
    6. ACTION_REQUEST (The actual scam, e.g. "Buy cards")
    7. END
    
    This component validates if the call adheres to this dangerous trajectory.
    """
    
    STATES = [
        "START", "GREETING", "AUTHORITY", "FEAR", "URGENCY", "ACTION_REQUEST", "END"
    ]
    
    # Define valid forward transitions (skipping is allowed in real life, but we track the 'highest' state reached)
    # We mainly want to see if we are moving 'down' the funnel.
    
    def __init__(self):
        self.state_history = []
    
    def update_state(self, current_state: CallState, intent: SemanticIntent) -> str:
        """
        Updates the global call state based on the latest intent.
        
        Args:
            current_state (CallState): The current state object (modified in place or used for ref).
            intent (SemanticIntent): The latest detected intent.
            
        Returns:
            str: The new state of the call.
        """
        old_phase = current_state.current_phase
        new_phase = old_phase
        
        # Simple Logic: State Promotion
        # If we detect a signal that belongs to a 'later' stage in the scam script,
        # we promote the state. Scammers rarely go backwards (e.g. from Urgency back to Greeting).
        
        # Map intents to potential states
        intent_map = {
            "GREETING": "GREETING",
            "AUTHORITY": "AUTHORITY",
            "FEAR": "FEAR",
            "URGENCY": "URGENCY",
            "PAYMENT": "ACTION_REQUEST",
            "THREAT": "FEAR"  # Threat acts as fear
        }
        
        detected_phase_candidate = intent_map.get(intent.label)
        
        if detected_phase_candidate:
            # Check if this is a 'forward' or 'same' movement
            # We get indices to compare hierarchy
            try:
                old_idx = self.STATES.index(old_phase)
                new_idx = self.STATES.index(detected_phase_candidate)
                
                # We allow moving forward. 
                # We also assume that if we are in URGENCY, hearing AUTHORITY again keeps us in high alert/Urgency 
                # or maybe doesn't demote us.
                # Strictly speaking, we want to track the *highest* risk state reached.
                if new_idx > old_idx:
                    new_phase = detected_phase_candidate
                    print(f"[Sequencer] State escalation: {old_phase} -> {new_phase}")
                    
            except ValueError:
                pass # State not in list
        
        current_state.current_phase = new_phase
        self.state_history.append(new_phase)
        
        return new_phase

    def get_progress(self, current_phase: str) -> float:
        """
        Returns a 0.0 - 1.0 progress indicator of how deep into the scam script we are.
        """
        try:
            return self.STATES.index(current_phase) / (len(self.STATES) - 1)
        except ValueError:
            return 0.0
