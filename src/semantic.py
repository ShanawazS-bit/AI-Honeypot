from typing import List, Dict
import numpy as np
from .models import SemanticIntent

import os
# Fix for Railway Read-Only File System
os.environ["HF_HOME"] = "/tmp"

try:
    from sentence_transformers import SentenceTransformer, util
    TRANSFORMER_AVAILABLE = True
except ImportError as e:
    TRANSFORMER_AVAILABLE = False
    print(f"[Semantic] Warning: 'sentence-transformers' import failed: {e}")

class SemanticAnalyzer:
    """
    Analyzes the meaning/intent of the transcript text.
    
    Uses Semantic Search (Sentence-BERT) to compare the caller's text
    against a database of known scam phrases and fraud archetypes.
    """
    
    SCAM_PROTOTYPES = {
        "GREETING": [
            "Hello", "Good morning", "How are you today?",
            "Namaste", "Kya haal hai", "Kaise hain aap"
        ],
        "AUTHORITY": [
            "I am calling from the police", "This is the IRS", "Social Security Administration",
            "Microsoft Technical Support", "Bank Security Department",
            "Main police station se bol raha hoon", "Hum bank se bol rahe hain", "RBI se call kar rahe hain"
        ],
        "FEAR": [
            "Your account has been compromised", "Suspicious activity detected",
            "Warrant for your arrest", "You will be taken into custody",
            "Legal action against you",
            "Aapka account band ho jayega", "Aap par case darj hua hai", "Police aapko arrest karegi"
        ],
        "URGENCY": [
            "You must act immediately", "Right now", "Do not hang up",
            "Before it is too late", "Within the next hour",
            "Abhi kijiye", "Jaldi kariye", "Phone mat katiye"
        ],
        "PAYMENT": [
            "Buy a gift card", "Target gift card", "Google Play card",
            "Bitcoin machine", "Wire transfer", "Verify your credit card number",
            "Paise transfer karein", "OTP batayein", "Gift card kharidiye"
        ]
    }

    def __init__(self, model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        self.model = None
        self.prototype_embeddings = {}
        
        if TRANSFORMER_AVAILABLE:
            try:
                print(f"[Semantic] Loading Sentence-BERT model: {model_name}...")
                self.model = SentenceTransformer(model_name)
                self._precompute_prototypes()
                print("[Semantic] Model loaded and prototypes embedded.")
            except Exception as e:
                print(f"[Semantic] Failed to load model: {e}")
                self.model = None

    def _precompute_prototypes(self):
        """
        Pre-computes embeddings for the scam prototype phrases for fast comparison.
        """
        for intent, phrases in self.SCAM_PROTOTYPES.items():
            self.prototype_embeddings[intent] = self.model.encode(phrases, convert_to_tensor=True)

    def analyze(self, text: str) -> SemanticIntent:
        """
        Classifies the intent of the given text.
        """
        if not text.strip():
            return SemanticIntent("SILENCE", 0.0)

        # Heuristic: Ignore very short utterances (1-2 words) for complex intents
        # to avoid false positives like "Right" -> URGENCY
        word_count = len(text.split())
        if word_count < 3 and "hello" not in text.lower() and "hi" not in text.lower():
             return SemanticIntent("NEUTRAL", 0.0)

        # Fallback to keyword matching if model is missing
        if not self.model:
            return self._keyword_fallback(text)
            
        try:
            # Encode input text
            input_embedding = self.model.encode(text, convert_to_tensor=True)
            
            best_intent = "UNKNOWN"
            best_score = 0.0
            
            # Compare against all categories
            for intent, proto_embeddings in self.prototype_embeddings.items():
                # Compute cosine similarities
                cosine_scores = util.cos_sim(input_embedding, proto_embeddings)
                # Take the max score for this category (closest match)
                max_score = float(cosine_scores.max())
                
                if max_score > best_score:
                    best_score = max_score
                    best_intent = intent
            
            # Threshold for relevance
            if best_score < 0.25:
                best_intent = "NEUTRAL"
                
            return SemanticIntent(
                label=best_intent,
                confidence=best_score,
                keywords_detected=[text] # Simplify for now
            )
            
        except Exception as e:
            print(f"[Semantic] Error analyzing text: {e}")
            return SemanticIntent("ERROR", 0.0)

    def _keyword_fallback(self, text: str) -> SemanticIntent:
        """
        Simple keyword matching if ML model fails.
        """
        text_lower = text.lower()
        for intent, phrases in self.SCAM_PROTOTYPES.items():
            for phrase in phrases:
                if phrase.lower() in text_lower:
                    return SemanticIntent(intent, 0.8, [phrase])
        return SemanticIntent("NEUTRAL", 0.0)
