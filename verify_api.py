import requests
import time

URL = "https://web-production-f4c25.up.railway.app/api/chat"
API_KEY = "testing_api_key_team_hacksmiths10000"

def test_api():
    print(f"Testing {URL}...")
    try:
        # Test with key
        print("2. Testing with key...")
        start_time = time.time()
        res = requests.post(URL, json={"text": "Hello scammer"}, headers={"x-api-key": API_KEY})
        duration = time.time() - start_time
        print(f"   Duration: {duration:.2f} seconds")
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
