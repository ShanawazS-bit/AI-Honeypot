
import re

def extract_intelligence(text_input):
    intelligence = {
        "bankAccounts": set(),
        "upiIds": set(),
        "phishingLinks": set(),
        "phoneNumbers": set(),
        "suspiciousKeywords": set()
    }
    # Logic copied from api/views.py (Refined Version)
    # 1. Use word boundaries to avoid matching substrings inside other numbers
    phone_pattern = r"(?:(?:\+91[\-\s]?)?[6-9]\d{9})\b" 
    # Note: \b is crucial at the end. At the start, +91 prevents \b, but (?:...) allows it?
    # Actually, simpler: r"(?:\+91[\-\s]?)?[6-9]\d{9}\b"
    # But + doesn't match \b. 
    # Let's try: r"(?:\b|\+91)[6-9]\d{9}\b" ? No.
    # The issue was matching "67890..." inside "1234567890..."
    # "12345" ends with digit. "6" starts with digit. No boundary.
    # So if we require \b at start of phone number OR +91, it won't match inside another number.
    phone_pattern = r"(?:(?:\+91[\-\s]?)|(?<!\d))[6-9]\d{9}\b"
    
    upi_pattern = r"[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}"
    url_pattern = r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+"
    acc_pattern = r"\b\d{9,18}\b" 

    found_phones = set(re.findall(phone_pattern, text_input))
    found_upis = set(re.findall(upi_pattern, text_input))
    found_links = set(re.findall(url_pattern, text_input))
    found_accounts = set(re.findall(acc_pattern, text_input))
    
    # Filter
    clean_accounts = set()
    for acc in found_accounts:
        # Check if this account is actually a phone number (or part of one)
        is_phone = False
        for ph in found_phones:
            # If acc is present in ph (substring), it's likely the same number
            if acc in ph:
                is_phone = True
                break
        
        if not is_phone:
             clean_accounts.add(acc)
    
    intelligence["phoneNumbers"].update(found_phones)
    intelligence["upiIds"].update(found_upis)
    intelligence["phishingLinks"].update(found_links)
    intelligence["bankAccounts"].update(clean_accounts)
    
    return intelligence

def test_extraction():
    # Test Case 1: Mixed content
    sample_text = "This is a security alert from your bank; we have detected suspicious activity on your account 1234567890123456, please verify. Call us at +91-9876543210 or pay via scam@upi."
    
    print(f"Input: {sample_text}")
    data = extract_intelligence(sample_text)
    
    print("\n--- Extracted Data ---")
    for key, val in data.items():
        print(f"{key}: {val}")

    print("\n--- Verification ---")
    
    # 1. Phone Number should be found
    # Note: re.findall(phone_pattern) returns the group(1) if present? No, findall behavior depends on groups.
    # The regex r"(\+91[\-\s]?)?[6-9]\d{9}" has one capturing group (\+91...).
    # If a group exists, findall returns the group. If the group is optional and missing, it returns empty string?
    # This might be why the user sees issues.
    
    # Actually, let's see what happens.
    
    # 2. Bank Account should be 1234567890123456
    # 3. Bank Account should NOT include the phone number digits (9876543210)
    
    if "1234567890123456" in data["bankAccounts"]:
        print("✅ Bank Account Found")
    else:
        print("❌ Bank Account MISSING")

    # Check for Phone Number in Bank Accounts (The Bug)
    # The phone number digits are 9876543210.
    if any("9876543210" in s for s in data["bankAccounts"]):
         print("❌ BUG DETECTED: Phone number identified as Bank Account!")
    else:
         print("✅ Phone number correctly excluded from Bank Accounts")

if __name__ == "__main__":
    test_extraction()
