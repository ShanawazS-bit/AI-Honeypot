import requests
import time

URL = "http://127.0.0.1:8000/api/chat"
API_KEY = "testing_api_key_team_hacksmiths10000"

def test_api():
    print(f"Testing {URL}...")
    try:
        # Test without key
        print("1. Testing without key...")
        res = requests.post(URL, json={"text": "Hello"})
        if res.status_code == 401:
            print("   PASS: Got 401 as expected.")
        else:
            print(f"   FAIL: Expected 401, got {res.status_code}")

        # Test with key - User Format - Multiple variations
        test_messages = [
            "Your bank account is blocked",
            "Please send the OTP immediately",
            "Click this link now",
            "Hello how are you"
        ]
        
        for msg in test_messages:
            print(f"\nTesting input: '{msg}'")
            payload = {
                "sessionId": "test-session-123",
                "message": {
                    "sender": "scammer",
                    "text": msg,
                    "timestamp": 1770005528731
                },
                "conversationHistory": [],
                "metadata": {
                    "channel": "SMS",
                    "language": "English",
                    "locale": "IN"
                }
            }
            res = requests.post(URL, json=payload, headers={"x-api-key": API_KEY})
            if res.status_code == 200:
                print(f"   Response: {res.json()['reply']}")
            else:
                print(f"   FAIL: Expected 200, got {res.status_code}")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_api()
