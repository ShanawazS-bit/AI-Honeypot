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
            "emailAddresses": set(),
            "phishingLinks": set(),
            "phoneNumbers": set(),
            "caseIds": set(),
            "policyNumbers": set(),
            "orderNumbers": set(),
            "suspiciousKeywords": set()
        }
        
        # Phone: capture full number including +91- prefix when present
        phone_pattern = r"(?:(?:\+|00)91[\-\s]?[6-9]\d{9}|(?<![\d])[6-9]\d{9}(?![\d]))"

        # UPI: username@bankhandle  (2-256 chars before @, 2-64 alpha after — no dot-TLD)
        upi_pattern = r"\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b"

        # Email: full email with TLD
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

        # URL: http/https and www.
        url_pattern = r"(?:https?://|www\.)[a-zA-Z0-9.-]+(?:\.[a-zA-Z]{2,})+(?:[/?][\w\-.~!$&'()*+,;=:@%]*)*"

        # Bank Account: 11-18 digits (avoids 10-digit phone overlap)
        acc_pattern = r"\b\d{11,18}\b"

        # Case / Ref IDs
        case_id_pattern = r"(?i)(?:case|ref|complaint|file|ticket)(?:\s*(?:id|no|num|number))?[\s\-\.#:]+([a-z0-9\-\/]{4,15})"

        # Policy Numbers
        policy_pattern = r"(?i)(?:policy|insurance)(?:\s*(?:id|no|num|number))?[\s\-\.#:]+([a-z0-9\-\/]{5,20})"

        # Order Numbers
        order_pattern = r"(?i)(?:order|tracking|shipment)(?:\s*(?:id|no|num|number))?[\s\-\.#:]+([a-z0-9\-\/]{5,20})"

        found_phones   = set(re.findall(phone_pattern, text_input))
        found_emails   = set(re.findall(email_pattern, text_input))
        found_upis     = set(re.findall(upi_pattern, text_input))
        found_links    = set(re.findall(url_pattern, text_input))
        found_accounts = set(re.findall(acc_pattern, text_input))
        found_case_ids = set(re.findall(case_id_pattern, text_input))
        found_policies = set(re.findall(policy_pattern, text_input))
        found_orders   = set(re.findall(order_pattern, text_input))

        # Bank Accounts: already filtered to 11-18 digits so no phone overlap
        clean_accounts = found_accounts
        
        # Filter UPIs: remove anything that is (or is a prefix of) a known email address
        clean_upis = set()
        for upi in found_upis:
            is_email_or_email_prefix = any(
                email == upi or email.startswith(upi + ".") or email.startswith(upi)
                for email in found_emails
            )
            if not is_email_or_email_prefix:
                clean_upis.add(upi)

        intelligence["phoneNumbers"].update(found_phones)
        intelligence["upiIds"].update(clean_upis)
        intelligence["emailAddresses"].update(found_emails)
        intelligence["phishingLinks"].update(found_links)
        intelligence["bankAccounts"].update(clean_accounts)
        intelligence["caseIds"].update(found_case_ids)
        intelligence["policyNumbers"].update(found_policies)
        intelligence["orderNumbers"].update(found_orders)
        
        scam_keywords = ["block", "suspend", "kyc", "verify", "urgent", "link", "pan", "aadhar", "otp",
                         "arrest", "police", "legal", "pay", "account", "upi", "bank", "card", "refund", "cashback"]
        
        lower_text = text_input.lower()
        for kw in scam_keywords:
            if kw in lower_text:
                intelligence["suspiciousKeywords"].add(kw)
                
        return intelligence
