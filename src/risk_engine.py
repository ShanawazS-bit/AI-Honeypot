from typing import List, Dict

class RiskEngine:
    """
    Analyzes text for specific "Red Flags" beyond just keywords.
    Identifies tactics like Urgency, threats, and Secrecy.
    """
    
    @staticmethod
    def analyze(text_input: str) -> List[str]:
        red_flags = []
        lower_text = text_input.lower()
        
        # 1. Urgency Tactics
        if any(w in lower_text for w in ["immediately", "urgent", "right now", "within 24 hours", "expires in", "block your", "suspend your"]):
            red_flags.append("Urgency/Deadline Pressure")
            
        # 2. Authority/Threats
        if any(w in lower_text for w in ["police", "arrest", "court", "legal action", "jail", "cbi", "rbi", "cyber crime"]):
            red_flags.append("Authority Impersonation/Threats")
            
        # 3. Financial Requests
        if any(w in lower_text for w in ["pay", "transfer", "deposit", "send money", "upi", "qr code", "fees", "fine"]):
            red_flags.append("Financial Request")
            
        # 4. Credential Theft
        if any(w in lower_text for w in ["otp", "password", "pin", "cvv", "card number", "login"]):
            red_flags.append("Credential/OTP Request")
            
        # 5. Technical Manipulation
        if any(w in lower_text for w in ["download", "install", "anydesk", "teamviewer", "screen share", "apk", "link"]):
            red_flags.append("Malicious Download/Link")
            
        # 6. Secrecy
        if any(w in lower_text for w in ["don't tell anyone", "confidential", "secret", "private"]):
            red_flags.append("Enforced Secrecy")
            
        return list(set(red_flags))
