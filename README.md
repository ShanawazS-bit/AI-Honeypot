# Honeypot API

## Description

The Honeypot API is an AI-powered decoy system that poses as a gullible bank customer to engage scammers in conversation, keep them occupied, and silently extract intelligence from their messages.

**Persona:** "Ramesh Kumar" — a 72-year-old retired government clerk who is confused by technology, easily stalled, and responds in Hinglish. This profile maximises engagement duration because scammers believe they have an easy target.

**Strategy — Three Phases:**
1. **Confusion (turns 1–2):** Asks who is calling, requests employee ID, buys time
2. **Elicitation (turns 3–6):** Probes for scammer credentials (bank account, UPI ID, phone number), pretends to fetch documents
3. **Stalling (turns 7+):** "OTP not coming", "link says 404", "battery low" — indefinite delay

Every incoming message is passed through two pipelines simultaneously:
- **Regex extraction** (`src/intelligence_extraction.py`) — pulls phone numbers, bank accounts, UPI IDs, phishing links, email addresses, case IDs, policy numbers, and order numbers
- **LLM classification + reply generation** (`src/llm_service.py`) — `gemma-3-4b-it` classifies the scam type and generates a natural Hinglish response in character

After generating the reply, the full extracted intelligence is reported asynchronously to the GUVI evaluation endpoint.

---

## Tech Stack

- **Language:** Python 3.11
- **Framework:** Django 4.x + Django REST Framework
- **LLM:** `gemma-3-4b-it` via Google Gemini API (`google-generativeai` SDK)
- **Intelligence Extraction:** Custom regex engine (`src/intelligence_extraction.py`)
- **Risk Detection:** Rule-based red flag engine (`src/risk_engine.py`)
- **Concurrency:** Python `threading` — LLM insight and reply run in parallel to halve latency
- **Production Server:** Gunicorn / Daphne (ASGI)
- **Deployment:** Railway (`railway.json`, `Procfile`)
- **Key Libraries:** `google-generativeai`, `djangorestframework`, `channels`, `daphne`, `django-cors-headers`, `requests`, `python-dotenv`

---

## Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/AI-Honeypot.git
   cd AI-Honeypot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   ```env
   SECRET_KEY=your-django-secret-key
   DEBUG=False
   ALLOWED_HOSTS=localhost,127.0.0.1,.railway.app
   GEMINI_API_KEY=your-gemini-api-key      # https://aistudio.google.com/app/apikey
   HONEYPOT_API_KEY=your-api-key
   # Optional: GEMINI_MODEL=gemini-2.0-flash  (default: gemma-3-4b-it)
   ```

4. **Run the application**
   ```bash
   python manage.py migrate
   python manage.py runserver 0.0.0.0:8000
   ```
   For production:
   ```bash
   daphne -b 0.0.0.0 -p 8000 honeypot_site.asgi:application
   ```

---

## API Endpoint

### `POST /api/chat`

**Headers:**
```
Content-Type: application/json
x-api-key: <your-api-key>
```

**Request Body:**
```json
{
  "sessionId": "uuid-v4-string",
  "message": {
    "sender": "scammer",
    "text": "URGENT: Your account has been compromised...",
    "timestamp": "2025-02-11T10:30:00Z"
  },
  "conversationHistory": [
    {
      "sender": "scammer",
      "text": "Previous message...",
      "timestamp": "1739266200000"
    },
    {
      "sender": "user",
      "text": "Your previous response...",
      "timestamp": "1739266230000"
    }
  ],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}
```

**Per-turn Response:**
```json
{
  "status": "success",
  "reply": "Arre beta... which department are you from? I want to note down your employee ID."
}
```

**Final Output** (submitted async to GUVI after every turn — final call contains full session data):
```json
{
  "sessionId": "uuid-v4-string",
  "scamDetected": true,
  "totalMessagesExchanged": 18,
  "engagementDurationSeconds": 345,
  "extractedIntelligence": {
    "phoneNumbers": ["+91-9876543210"],
    "bankAccounts": ["1234567890123456"],
    "upiIds": ["scammer.fraud@fakebank"],
    "phishingLinks": ["http://malicious-site.com"],
    "emailAddresses": ["scammer@fake.com"],
    "caseIds": ["CASE-5566-XYZ"],
    "policyNumbers": [],
    "orderNumbers": []
  },
  "agentNotes": "Scammer claimed to be from SBI fraud department, used urgency and OTP theft tactics.",
  "scamType": "bank_fraud",
  "confidenceLevel": 0.92
}
```

**Error Response (LLM unavailable):**
```json
{
  "status": "error",
  "message": "LLM service unavailable. Please retry."
}
```
HTTP status: `503 Service Unavailable`
