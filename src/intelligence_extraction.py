import re
from typing import Dict, Set, Any

class IntelligenceExtractor:
    """
    Extracts valuable intelligence (Bank details, UPI, Phone, Links) from text
    using regex patterns.
    """
    
    @staticmethod
    def extract(text_input: str) -> Dict[str, Set[str]]:
        intelligence = {
            "bankAccounts": set(),
            "upiIds": set(),
            "emails": set(),
            "phishingLinks": set(),
            "phoneNumbers": set(),
            "suspiciousKeywords": set()
        }
        
        # Regex Patterns
        phone_pattern = r"(?:(?:\+91[\-\s]?)|(?<!\d))[6-9]\d{9}\b"
        upi_pattern = r"[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}"
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        url_pattern = r"https?://[a-zA-Z0-9.-]+(?:\.[a-zA-Z]{2,})+(?:[/?][\w\-.~!$&'()*+,;=:@%]*)*"
        acc_pattern = r"\b\d{9,18}\b" 

        found_phones = set(re.findall(phone_pattern, text_input))
        found_upis = set(re.findall(upi_pattern, text_input))
        found_emails = set(re.findall(email_pattern, text_input))
        found_links = set(re.findall(url_pattern, text_input))
        found_accounts = set(re.findall(acc_pattern, text_input))
        
        clean_accounts = set()
        for acc in found_accounts:
            is_phone = False
            for ph in found_phones:
                if acc in ph:
                    is_phone = True
                    break
            
            if not is_phone:
                clean_accounts.add(acc)
        
        clean_upis = set()
        for upi in found_upis:
            if upi not in found_emails:
                clean_upis.add(upi)

        intelligence["phoneNumbers"].update(found_phones)
        intelligence["upiIds"].update(clean_upis)
        intelligence["emails"].update(found_emails)
        intelligence["phishingLinks"].update(found_links)
        intelligence["bankAccounts"].update(clean_accounts)
        
        scam_keywords = ["block", "suspend", "kyc", "verify", "urgent", "link", "pan", "aadhar", "otp",
                         "arrest", "police", "legal", "pay", "account", "upi", "bank", "card"]
        
        lower_text = text_input.lower()
        for kw in scam_keywords:
            if kw in lower_text:
                intelligence["suspiciousKeywords"].add(kw)
                
        return intelligence
