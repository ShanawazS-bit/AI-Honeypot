# Honeypot API

## Description

An AI-powered honeypot that pretends to be a gullible bank customer — keeping scammers engaged while silently extracting intelligence from their messages. The system uses a Gemini LLM to generate convincing Hinglish responses and regex-based extraction to capture phone numbers, bank accounts, UPI IDs, phishing links, and email addresses in real time.

---

## Tech Stack

- **Framework**: Django + Django REST Framework
- **LLM**: `gemma-3-4b-it` via Google Gemini API (`google-genai` SDK)
- **Key Libraries**: `django-cors-headers`, `requests`, `python-dotenv`, `google-genai`
- **Deployment**: Railway (Procfile + `gunicorn`/`daphne`)

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
   # Edit .env and fill in GEMINI_API_KEY and HONEYPOT_API_KEY
   ```

4. **Run the application**
   ```bash
   python manage.py migrate
   python manage.py runserver 0.0.0.0:8000
   ```

---

## API Endpoint

- **URL**: `https://your-deployed-url.railway.app/api/chat`
- **Method**: `POST`
- **Authentication**: `x-api-key` header

### Request Body

```json
{
  "sessionId": "abc123-session-id",
  "scenarioId": "bank_fraud_001",
  "message": {
    "sender": "scammer",
    "text": "Your account is blocked. Share OTP to unblock.",
    "timestamp": "1700000000"
  },
  "conversationHistory": [],
  "metadata": {}
}
```

### Response

```json
{
  "status": "success",
  "reply": "Arre... who is this? Beta, my eyes are not good...",
  "sessionId": "abc123-session-id",
  "scamDetected": true,
  "scamType": "bank_fraud",
  "confidenceLevel": 0.95,
  "totalMessagesExchanged": 2,
  "engagementDurationSeconds": 0,
  "extractedIntelligence": {
    "phoneNumbers": ["+91-9876543210"],
    "bankAccounts": ["1234567890123456"],
    "upiIds": ["scammer.fraud@fakebank"],
    "phishingLinks": ["http://malicious-site.com"],
    "emailAddresses": ["scammer@fake.com"]
  },
  "redFlags": ["Authority Impersonation/Threats", "Credential/OTP Request"],
  "agentNotes": "Scammer claimed to be from SBI fraud department..."
}
```

---

## Approach

### How Scams Are Detected

Every message is passed through a two-layer detection pipeline:

1. **Regex extraction** (`src/intelligence_extraction.py`) — identifies phone numbers, bank accounts (11–18 digits), UPI handles (`name@bank`), phishing URLs, and email addresses with zero false positives.
2. **LLM classification** (`src/llm_service.py`) — `gemma-3-4b-it` classifies the scam type (`bank_fraud`, `upi_fraud`, `phishing`, `kyc_fraud`, etc.) and generates agent notes explaining the tactic.

### How Intelligence Is Extracted

| Field | Detection method |
|-------|-----------------|
| `phoneNumbers` | Regex: 10-digit Indian numbers, preserves `+91-` prefix |
| `bankAccounts` | Regex: 11–18 digit sequences |
| `upiIds` | Regex: `handle@bankname` (no TLD), email false-positives filtered |
| `phishingLinks` | Regex: `http://` / `https://` / `www.` URLs |
| `emailAddresses` | Regex: full RFC-style email addresses |

All intelligence is accumulated across the full conversation history, so partial data shared across multiple turns is still captured.

### How Engagement Is Maintained

The honeypot uses a phase-based persona — **Ramesh Kumar, 72-year-old retired government clerk** — with three behavioural phases:

| Phase | Turns | Strategy |
|-------|-------|----------|
| **Confusion** | 1–2 | "Who is this beta? Which department?" |
| **Elicitation** | 3–6 | "What is your employee ID?", asks for scammer's credentials |
| **Stalling** | 7+ | "OTP not coming", "Link shows 404", "Battery low" |

The LLM is prompted to naturally ask for any intelligence not yet collected (UPI ID, phone, bank account) while staying in character.
