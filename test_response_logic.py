import sys
import os

# Add root dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.risk_engine import RiskEngine
from src.response_strategy import ResponseStrategy

def test_logic():
    print("--- Testing Risk Engine ---")
    scam_text = "Urgent! Police will arrest you if you dont pay immediately via UPI."
    flags = RiskEngine.analyze(scam_text)
    print(f"Input: {scam_text}")
    print(f"Detected Flags: {flags}")
    
    assert "Urgency/Deadline Pressure" in flags
    assert "Authority Impersonation/Threats" in flags
    print("✅ Risk Engine Passed")
    
    print("\n--- Testing Response Strategy ---")
    
    # Case 1: Bank Fraud
    resp_bank = ResponseStrategy.generate_response("bank_fraud", "block your account")
    print(f"Scenario: Bank Fraud (Block)")
    print(f"Response: {resp_bank}")
    assert "branch" in resp_bank or "bank" in resp_bank
    
    # Case 2: UPI Fraud
    resp_upi = ResponseStrategy.generate_response("upi_fraud", "scan this qr code")
    print(f"Scenario: UPI Fraud (Scan)")
    print(f"Response: {resp_upi}")
    assert "PIN" in resp_upi or "VPA" in resp_upi or "money" in resp_upi
    
    print("✅ Response Strategy Passed")

if __name__ == "__main__":
    test_logic()
