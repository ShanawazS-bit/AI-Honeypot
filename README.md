# AI Honeypot Detection System

An advanced AI-powered Honeypot designed to detect, analyze, and extract intelligence from scam calls and messages. The system simulates a vulnerable persona ("Grandpapa") to keep scammers engaged while capturing critical details like bank accounts, UPI IDs, and phishing links.

## 🚀 Features

- **Intelligent Response System**: Uses a "Confused Persona" strategy to elicit more information from scammers.
- **Red Flag Analysis**: Automatically detects high-risk indicators (Urgency, Threats, Secrecy).
- **Intelligence Extraction**: Regex-based engine to capture Phones, UPIs, URLs (with query params), and Bank Accounts.
- **Modular Architecture**: 
  - `RiskEngine`: For threat analysis.
  - `ResponseStrategy`: For probing questions.
  - `IntelligenceExtractor`: For entity extraction.
- **REST API**: robust endpoint for integration with detailed JSON output.

## 🛠️ Tech Stack

- **Backend**: Python, Django, Django REST Framework
- **Architecture**: Modular Service-Oriented
- **Deployment**: Docker-ready

## 📦 Setup & Installation

### Prerequisites
- Python 3.8+
- pip

### 1. Clone the Repository
```bash
git clone https://github.com/ShanawazS-bit/AI-Honeypot.git
cd AI-Honeypot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Migrations
```bash
python manage.py migrate
```

### 4. Start the Server
```bash
python manage.py runserver
```
The API will be available at `http://localhost:8000/api/honeypot/`.

## 🧪 Testing

You can test the API using the provided test script or any API client (Postman).

```bash
python test_extraction.py
```

See [API.md](API.md) for full endpoint documentation and example payloads.

## 📂 Project Structure

```
AI-Honeypot/
├── api/
│   ├── views.py           # API Logic (Controller)
│   ├── serializers.py     # Data Validation
│   └── ...
├── src/
│   ├── risk_engine.py          # Red Flag Detection
│   ├── response_strategy.py    # Probing Question Logic
│   ├── intelligence_extraction.py # Regex Extraction
│   └── ...
├── API.md                 # API Documentation
├── main.py                # Entry point
└── manage.py              # Django CLI
```

## 🛡️ Security

- **API Key Authentication**: All endpoints require `x-api-key`.
- **Input Validation**: Strict typing via Serializers.
- **Safe Regex**: Optimized patterns to prevent ReDoS.
