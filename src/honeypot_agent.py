"""
honeypot_agent.py — Core honeypot persona and engagement logic.

This module is the brain of the honeypot:
- Builds the Ramesh Kumar persona
- Manages phase-based engagement strategy
- Delegates LLM generation and intelligence extraction
"""

from .llm_service import LLMService
from .intelligence_extraction import IntelligenceExtractor
from .risk_engine import RiskEngine


class HoneypotAgent:
    """
    Stateless agent that processes a single scammer turn and returns
    a reply plus extracted intelligence.

    Usage:
        agent = HoneypotAgent()
        result = agent.process(session_id, scammer_text, history)
    """

    def __init__(self):
        self.llm = LLMService()

    def process(
        self,
        session_id: str,
        text: str,
        history: list,
        metadata: dict = None,
    ) -> dict:
        """
        Process one scammer message and return a full intelligence + reply dict.

        Args:
            session_id: Unique conversation identifier
            text:       Latest scammer message
            history:    Previous turns [{'sender': 'scammer'|'victim', 'text': '...'}]
            metadata:   Optional extra fields from request

        Returns:
            dict with reply, scamType, confidenceLevel, extractedIntelligence,
            redFlags, agentNotes
        """
        turn_count = len(history)

        # 1. Extract intelligence from full conversation so far
        full_text = text + " " + " ".join(m.get("text", "") for m in history)
        intelligence = IntelligenceExtractor.extract(full_text)
        red_flags = RiskEngine.analyze(full_text)

        # 2. Classify scam type + generate agent notes
        insight = self.llm.generate_insight(full_text)
        scam_type   = insight.get("scamType",   "suspected_fraud")
        agent_notes = insight.get("agentNotes", f"Detected {scam_type} attempt.")
        confidence  = insight.get("confidence", 0.8)

        # 3. Keyword-based scam type fallback
        if scam_type in ("suspected_fraud", "unknown"):
            if intelligence["phishingLinks"]: scam_type = "phishing"
            elif intelligence["bankAccounts"]: scam_type = "bank_fraud"
            elif intelligence["upiIds"]: scam_type = "upi_fraud"

        # 4. Generate honeypot reply
        reply = self.llm.generate_response(
            text_input=text,
            history=history,
            intent=scam_type,
            turn_count=turn_count,
            extracted_intelligence=intelligence,
            session_id=session_id,
        )

        return {
            "reply":                reply,
            "scamType":             scam_type,
            "confidenceLevel":      confidence,
            "extractedIntelligence": intelligence,
            "redFlags":             red_flags,
            "agentNotes":           agent_notes,
        }
