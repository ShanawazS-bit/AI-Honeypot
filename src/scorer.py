from typing import List
from .models import RiskScore, CallState, ParalinguisticFeatures, SemanticIntent
from .sequencer import BehavioralSequencer

class FraudRiskScorer:
    """
    Calculates the probability that the current call is a scam.
    
    Aggregates inputs from:
    1. Behavioral Sequencer (How far along the scam script are we?)
    2. Semantic Analyzer (Did they ask for money or use threats?)
    3. Paralinguistic Analyzer (Are they sounding urgent/stressed/robotic?)
    """
    
    # Thresholds
    RISK_THRESHOLD_MEDIUM = 0.4
    RISK_THRESHOLD_HIGH = 0.7
    RISK_THRESHOLD_CRITICAL = 0.9

    def __init__(self):
        self.sequencer_ref = BehavioralSequencer() # Just for accessing constant STATES

    def calculate_score(self, 
                        call_state: CallState, 
                        para_features: ParalinguisticFeatures, 
                        last_intent: SemanticIntent) -> RiskScore:
        """
        Computes the real-time risk score.
        """
        score = 0.0
        triggers = []
        
        # 1. Sequence-based scoring (40% weight)
        # Being in 'ACTION_REQUEST' is inherently risky.
        seq_progress = 0.0
        try:
            seq_idx = self.sequencer_ref.STATES.index(call_state.current_phase)
            seq_max = len(self.sequencer_ref.STATES) - 1
            seq_progress = seq_idx / seq_max
        except ValueError:
            pass
            
        score += seq_progress * 0.4
        if seq_progress > 0.6:
            triggers.append(f"Deep in Scam Script ({call_state.current_phase})")
            
        # 2. Intent-based scoring (30% weight)
        # Specific risky intents add immediate score
        if last_intent.label == "PAYMENT":
            score += 0.5 # Huge jump
            triggers.append("Payment Demand")
        elif last_intent.label in ["THREAT", "URGENCY", "FEAR", "AUTHORITY"]:
            score += 0.2
            triggers.append(f"High Risk Intent: {last_intent.label}")
            
        # 3. Paralinguistic-based scoring (30% weight)
        # High pitch/jitter indicates stress or artificiality
        # Normalize pitch (very rough heuristic, assuming 100-300Hz range)
        # eGeMAPS returns semitones sometimes, but let's assume raw or normalized
        # We'll use the 'jitter' and 'pitch_variance' as stress indicators
        
        stress_score = 0.0
        if para_features.pitch_variance > 0.5: # Arbitrary threshold for demo
            stress_score += 0.1
        if para_features.jitter > 0.05:
            stress_score += 0.1
        if para_features.speaking_rate > 4: # Very fast talking
            stress_score += 0.1
            
        score += stress_score
        if stress_score > 0.1:
            triggers.append("Vocal Stress/Urgency Detected")

        # Clamp score
        score = min(max(score, 0.0), 1.0)
        
        # Determine Level
        if score >= self.RISK_THRESHOLD_CRITICAL:
            level = "CRITICAL"
        elif score >= self.RISK_THRESHOLD_HIGH:
            level = "HIGH"
        elif score >= self.RISK_THRESHOLD_MEDIUM:
            level = "MEDIUM"
        else:
            level = "LOW"
            
        return RiskScore(
            score=score,
            level=level,
            trigger_factors=triggers
        )
