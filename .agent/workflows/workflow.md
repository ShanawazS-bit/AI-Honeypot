---
description: 
---

# AI Honeypot Detection System — Guides

## Proposed Solution

A **real-time audio fraud detection system** that escalates suspicious calls into an **autonomous adversarial conversational agent** that:

* Safely wastes scammer time
* Extracts actionable intelligence
* Minimizes risk to real users

---

## High-Level Architecture

```
Incoming Call (Android)
        ↓
Real-time Audio Stream
        ↓
Detection Pipeline (< 400 ms)
        ↓
Fraud Risk Score
        ↓
[If High Risk] → Autonomous AI Honeypot Agent
```

---

## Step 1: Detecting the Scam Call

### Input

* **Live incoming call audio stream** (Android device)

### Core Pipeline

1. **Audio Chunker**

   * Window size: **1–2 seconds**
   * Purpose: enable low-latency parallel processing

2. **Streaming ASR (Speech-to-Text)**

   * Options:

     * `vosk`
     * OpenAI Whisper (`small` / `medium`)
   * Output: incremental transcripts

3. **Paralinguistic Analyzer**
   Detects non-verbal vocal signals:

   * Pitch
   * Speed
   * Rhythm
   * Pauses
   * Stress
   * Breath patterns
   * Background noise signatures

   **Suggested Tool**:

   * `openSMILE`

4. **Semantic Analyzer**

   * Model: **Sentence-BERT**
   * Extracts intent & meaning from transcript chunks

5. **Behavioral Sequencer**

   * Model: **Finite State Machine (FSM)**
   * Tracks narrative progression of the caller

6. **Fraud Risk Scorer**

   * Aggregates all signals
   * Outputs real-time danger score

---

## Behavioral Sequencer (FSM)

### Motivation

Scam calls follow **predictable psychological story arcs**, not random dialogue.

### States

```
START
GREETING
AUTHORITY
FEAR
URGENCY
ACTION_REQUEST
END
```

### Example Timeline

| Time    | Event              |
| ------- | ------------------ |
| t = 6s  | authority_detected |
| t = 11s | fear_phrase        |
| t = 16s | urgency_spike      |
| t = 22s | payment_action     |

This **ordered escalation** is a strong fraud signal.

---

## Fraud Risk Scorer

### Key Question

> "Given the behavioral trajectory so far, how dangerous is this call right now?"

### Inputs

| Source                  | What it Contributes                                 |
| ----------------------- | --------------------------------------------------- |
| FSM                     | Current state + transition history                  |
| Semantic Analyzer       | Intent probabilities (payment, credentials, threat) |
| Paralinguistic Analyzer | Stress, urgency, dominance                          |
| Behavioral Sequencer    | Interruptions, pace, control patterns               |
| Metadata                | Call duration, language, silence gaps               |

### Output

* Continuous **risk score** (0–1 or 0–100)
* Threshold-based escalation trigger

---

## Latency Budget (Target < 400 ms)

| Component               | Latency    |
| ----------------------- | ---------- |
| Audio Chunking          | ~5 ms      |
| ASR                     | 150–300 ms |
| Paralinguistic Analysis | 20–40 ms   |
| Semantic Analysis       | 30–50 ms   |
| FSM Sequencing          | ~1 ms      |
| Scoring                 | ~1 ms      |

**Final Total:** `< 400 ms`

---

## Escalation Path

If **Risk Score ≥ Threshold**:

* Hand control to **AI Honeypot Agent**
* Agent behavior:

  * Acts like a vulnerable human
  * Prolongs conversation
  * Avoids real disclosures
  * Collects scam tactics & metadata

---

## Design Philosophy (Important)

* Detection is **behavioral + semantic**, not keyword-based
* FSM ensures **order matters**, not just presence of signals
* Low latency enables **real-time intervention**
* System is defensive, deceptive, and intelligence-driven

---

## What This Is NOT

* ❌ Simple spam keyword detector
* ❌ Offline batch fraud analysis
* ❌ One-model-fits-all classifier

This is a **real-time adversarial intelligence system**.

---

## End Goal

> Detect scams early, waste attacker resources, and turn fraud attempts into structured intelligence.
