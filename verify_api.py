import requests
import time

URL = "http://127.0.0.1:8000/api/chat"
API_KEY = "test-key-123"

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

        # Test with key
        print("2. Testing with key...")
        res = requests.post(URL, json={"text": "Hello scammer"}, headers={"x-api-key": API_KEY})
        if res.status_code == 200:
            print(f"   PASS: Got 200. Response: {res.json()}")
        else:
            print(f"   FAIL: Expected 200, got {res.status_code}. Body: {res.text}")

    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_api()
