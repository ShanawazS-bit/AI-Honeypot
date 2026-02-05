# Testing Documentation - Agentic Honeypot API

This guide provides instructions on how to test the deployed Agentic Honeypot API.

## 1. API Details

- **Base URL**: `https://web-production-9b449.up.railway.app`
- **Endpoint**: `/api/chat`
- **Method**: `POST`
- **Authentication**: Requires `x-api-key` header.

## 2. Testing Tools

You can test using:
1.  **cURL** (Command Line)
2.  **Postman** / **Insomnia**
3.  **Official Honeypot Tester**

---

## 3. Test Cases

### Case A: Official "Scam" Test (Triggers Callback)
This payload simulates a scammer sending a message. The system should detect keywords like "blocked" or "verify", respond as a vulnerable person, and trigger the background callback to GUVI.

**cURL Command:**
```bash
curl -X POST "https://web-production-9b449.up.railway.app/api/chat" \
     -H "Content-Type: application/json" \
     -H "x-api-key: test-key-123" \
     -d '{
           "sessionId": "test-session-001",
           "message": {
             "text": "Your bank account will be blocked today. Verify immediately at http://fake-bank.com",
             "sender": "scammer",
             "timestamp": 1770005528731
           },
           "conversationHistory": []
         }'
```

**Expected Response:**
```json
{
    "status": "success",
    "reply": "Oh no! My account is in which bank? I have many."
}
```

### Case B: Normal Conversation
Simulate a non-scam message.

**cURL Command:**
```bash
curl -X POST "https://web-production-9b449.up.railway.app/api/chat" \
     -H "Content-Type: application/json" \
     -H "x-api-key: test-key-123" \
     -d '{
           "sessionId": "test-session-002",
           "message": {
             "text": "Hello, how are you today?",
             "sender": "user"
           }
         }'
```

**Expected Response:**
```json
{
    "status": "success",
    "reply": "I am confused. Why do I need to do this?"
}
```

---

## 4. Verification

1.  **Status Code**: You should receive `200 OK`.
2.  **Response Body**: Must contain `status` and `reply`.
3.  **Callback**: If the message contained scam keywords (Case A), checking the Railway logs will show:
    ```
    Sending Callback for test-session-001...
    Callback Status: 200, Body: ...
    ```

## 5. Using the Official Tester

1.  Open the **Honeypot Endpoint Tester** provided by the hackathon.
2.  **API URL**: `https://web-production-9b449.up.railway.app/api/chat`
3.  **API Key**: `my-secret-key` (Any string works).
4.  Click **Test Endpoint**.
