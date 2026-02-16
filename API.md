# AI Honeypot API Documentation

## Overview
The AI Honeypot API is designed to interact with scam callers/messages, extract intelligence, and provide red-flag analysis. It simulates a vulnerable persona ("Grandpapa") to elicit actionable details from scammers.

## Base URL
`http://localhost:8000` (Local)

## Authentication
All requests must include the `x-api-key` header.

## Endpoints

### 1. Scam Detection & Response
**POST** `/api/honeypot/`

Analyzes an incoming message and returns a context-aware response, extracted intelligence, and risk analysis.

#### Headers
| Key | Value | Description |
|---|---|---|
| `x-api-key` | `YOUR_API_KEY` | Required for authentication |
| `Content-Type` | `application/json` | |

#### Request Body
```json
{
  "sessionId": "unique-session-id",
  "scenarioId": "bank_fraud", // Optional: "bank_fraud", "upi_fraud", "phishing", "unknown"
  "message": {
    "text": "Your account is blocked. Click here to verify.",
    "sender": "scammer",
    "timestamp": 1708069412
  },
  "conversationHistory": [
    {"role": "user", "text": "Hello?"},
    {"role": "assistant", "text": "Who is this?"}
  ],
  "metadata": {
    "caller_id": "+919876543210"
  }
}
```

#### Response
```json
{
  "status": "success",
  "sessionId": "unique-session-id",
  "reply": "Blocked? Oh no! Which branch are you calling from?",
  "scamDetected": true,
  "scamType": "bank_fraud",
  "extractedIntelligence": {
    "bankAccounts": ["1234567890"],
    "upiIds": ["scam@upi"],
    "phishingLinks": ["http://fake-bank.com"],
    "phoneNumbers": ["+919876543210"],
    "suspiciousKeywords": ["block", "verify"]
  },
  "redFlags": [
    "Urgency/Deadline Pressure",
    "Financial Request"
  ],
  "agentNotes": "Detected bank_fraud attempt. Red Flags: Urgency/Deadline Pressure. Bank account details extracted."
}
```

### 2. Callback (Internal)
The system automatically sends a callback to the GUVI evaluation endpoint upon processing a message.

**URL**: `https://hackathon.guvi.in/api/updateHoneyPotFinalResult`

#### Payload
```json
{
  "sessionId": "unique-session-id",
  "scamDetected": true,
  "scamType": "bank_fraud",
  "totalMessagesExchanged": 5,
  "extractedIntelligence": { ... },
  "redFlags": ["Urgency/Deadline Pressure"],
  "agentNotes": "..."
}
```
