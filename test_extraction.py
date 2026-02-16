import re
import sys
import os

# Add root dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.intelligence_extraction import IntelligenceExtractor

def test_extraction():
    # Test Case 1: Mixed content with URL params
    sample_text = "Urgent! Click http://amaz0n-deals.fake-site.com/claim?id=12345 to verify account 1234567890123456. Call +91-9876543210."
    
    print(f"Input: {sample_text}")
    data = IntelligenceExtractor.extract(sample_text)
    
    print("\n--- Extracted Data ---")
    for key, val in data.items():
        print(f"{key}: {val}")

    print("\n--- Verification ---")
    
    # 1. URL check
    expected_url = "http://amaz0n-deals.fake-site.com/claim?id=12345"
    if any("claim?id=12345" in l for l in data["phishingLinks"]):
        print("✅ Phishing Link with Query Params Found")
    else:
        print(f"❌ Phishing Link Broken. Found: {data['phishingLinks']}")

    # 2. Bank Account
    if "1234567890123456" in data["bankAccounts"]:
        print("✅ Bank Account Found")
    else:
        print("❌ Bank Account MISSING")

    # 3. Phone Number safety
    if any("9876543210" in s for s in data["bankAccounts"]):
         print("❌ BUG: Phone identified as Account")
    else:
         print("✅ Phone correct")

if __name__ == "__main__":
    test_extraction()
