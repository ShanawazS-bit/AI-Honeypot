# Architecture — AI Honeypot API

## Overview

A Django REST API that acts as an AI-powered honeypot victim. It receives scammer messages, extracts intelligence (phone numbers, bank accounts, UPI IDs, phishing links, email addresses), and responds with a convincing human-like persona to keep the scammer engaged.

## Directory Structure

```
AI-Honeypot/
├── README.md                    # Setup and usage instructions
├── src/                         # Source code
│   ├── honeypot_agent.py        # Honeypot logic (core agent)
│   ├── llm_service.py           # LLM integration (Gemini via google-genai)
│   ├── intelligence_extraction.py  # Regex-based intel extraction
│   ├── risk_engine.py           # Red flag detection
│   ├── response_strategy.py     # Phase-based engagement logic
│   └── ...
├── api/                         # Django app
│   ├── views.py                 # HTTP endpoint handlers
│   ├── urls.py                  # URL routing
│   └── serializers.py           # Request validation
├── honeypot_site/               # Django project config
│   └── settings.py
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
├── Procfile                     # Deployment (Railway/Heroku)
└── docs/
    └── architecture.md          # This file
```

## Component Diagram

```
Scammer
  │
  ▼
POST /api/chat
  │
  ▼
HoneypotEndpoint (api/views.py)
  │
  ├──► HoneypotAgent (src/honeypot_agent.py)
  │         │
  │         ├──► IntelligenceExtractor   →  bankAccounts, phoneNumbers,
  │         │    (regex-based)               upiIds, phishingLinks, emailAddresses
  │         │
  │         ├──► RiskEngine              →  redFlags list
  │         │
  │         └──► LLMService             →  reply + scamType + agentNotes
  │               (gemma-3-4b-it via
  │                google-genai SDK)
  │
  └──► Callback Thread → POST to GUVI evaluation endpoint
```

## Engagement Strategy (Phase-based)

| Turn | Phase | Behaviour |
|------|-------|-----------|
| 1–2  | CONFUSION | "Who is this? Which department beta?" |
| 3–6  | ELICITATION | "What is your employee ID?", "Which branch?" |
| 7+   | STALLING | "OTP not coming", "Link says 404", "Battery low" |

## LLM Model

- **Default**: `gemma-3-4b-it` (Gemini API, always available)  
- **Override**: Set `GEMINI_MODEL=gemini-2.0-flash` in `.env` if you have quota
- **SDK**: `google-genai` (new, replaces deprecated `google-generativeai`)
