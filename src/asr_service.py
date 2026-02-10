from abc import ABC, abstractmethod
import json
import os
import sys
from typing import Optional
from .models import AudioChunk, TranscriptSegment

# Try importing vosk, handle failure if not installed
try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError as e:
    VOSK_AVAILABLE = False
    print(f"[ASRService] Warning: 'vosk' import failed: {e}")

class ASRService(ABC):
    """
    Abstract Base Class for Automatic Speech Recognition services.
    Enables swapping between different ASR engines (Vosk, Whisper, Mock).
    """
    
    @abstractmethod
    def process_chunk(self, chunk: AudioChunk) -> Optional[TranscriptSegment]:
        """
        Process a chunk of audio and return a transcript if available.
        
        Args:
            chunk (AudioChunk): The audio data to process.
            
        Returns:
            Optional[TranscriptSegment]: The recognized text segment, or None if no result yet.
        """
        pass

class VoskASRService(ASRService):
    """
    Implementation of ASR using the offline Vosk engine.
    
    Latency Target components:
        - ASR Processing: 150-300ms typical for small models.
    """
    
    def __init__(self, language: str = "en"):
        """
        Initialize Vosk model.
        
        Args:
            language (str): 'en' or 'hi'.
        """
        if not VOSK_AVAILABLE:
            raise ImportError("Vosk library is not installed.")
            
        model_paths = {
            "en": "models/vosk-model-small-en-us-0.15",
            "hi": "models/vosk-model-small-hi-0.22"
        }
        
        model_path = model_paths.get(language, model_paths["en"])
            
        if not os.path.exists(model_path):
             raise FileNotFoundError(f"Vosk model not found at '{model_path}'. Please download it.")
             
        print(f"[ASRService] Loading Vosk model for '{language}' from {model_path}...")
        self.model = Model(model_path)
        # We don't initialize the recognizer here because it needs sample_rate
        # We will initialize it on the first chunk or require it in init.
        # For simplicity, we'll lazy init or assume 16k.
        self.recognizer = None
        self.sample_rate = 16000 # Default
        print("[ASRService] Vosk model loaded successfully.")

    def process_chunk(self, chunk: AudioChunk) -> Optional[TranscriptSegment]:
        """
        Feeds audio to Vosk and retrieves results.
        """
        # Initialize recognizer if sample rate changes or is first run
        if self.recognizer is None or self.sample_rate != chunk.sample_rate:
            self.sample_rate = chunk.sample_rate
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            
        # Vosk expects bytes
        # AcceptWaveform returns True if a result (silence pause) is available
        if self.recognizer.AcceptWaveform(chunk.data):
            res = json.loads(self.recognizer.Result())
            text = res.get("text", "")
            if text:
                return TranscriptSegment(
                    text=text,
                    start_time=chunk.timestamp, # Approx
                    end_time=chunk.timestamp + chunk.duration,
                    confidence=1.0, # Vosk basic result doesn't always have conf per word easily in this mode
                    is_final=True
                )
        else:
            # Partial result
            res = json.loads(self.recognizer.PartialResult())
            partial = res.get("partial", "")
            if partial:
                 return TranscriptSegment(
                    text=partial,
                    start_time=chunk.timestamp,
                    end_time=chunk.timestamp + chunk.duration,
                    confidence=0.5,
                    is_final=False
                )
        
        return None

        return None

class MultiVoskASRService(ASRService):
    """
    Runs English and Hindi ASR models in parallel to support mixed-language usage.
    """
    def __init__(self):
        print("[ASRService] Initializing Multi-Language Mode (En + Hi)...")
        # Initialize both sub-services
        self.service_en = VoskASRService(language='en')
        self.service_hi = VoskASRService(language='hi')
        
    def process_chunk(self, chunk: AudioChunk) -> Optional[TranscriptSegment]:
        # Run both processes
        # Note: Sequential for simplicity, but Vosk is fast enough.
        # Ideally this would be threaded.
        
        res_en = self.service_en.process_chunk(chunk)
        res_hi = self.service_hi.process_chunk(chunk)
        
        # Heuristic: Pick the one that has text.
        # If both have text, pick the longer one (usually correct model produces more coherent/longer words)
        
        text_en = res_en.text if res_en else ""
        text_hi = res_hi.text if res_hi else ""
        
        if not text_en and not text_hi:
            return None
            
        if text_en and not text_hi:
            return res_en
            
        if text_hi and not text_en:
            return res_hi
            
        # Conflict resolution
        if len(text_en) > len(text_hi):
            return res_en
        else:
             return res_hi

class MockASRService(ASRService):
    """
    Mock ASR for testing pipeline flow without heavy models.
    """
    def process_chunk(self, chunk: AudioChunk) -> Optional[TranscriptSegment]:
        # Dumb simulation: just return a fixed string every few chunks
        import random
        if random.random() > 0.8:
            return TranscriptSegment(
                start_time=chunk.timestamp,
                end_time=chunk.timestamp + chunk.duration,
                confidence=0.9,
                is_final=True
            )
        return None




class FasterWhisperASRService(ASRService):
    
   
    def __init__(self, model_size="tiny", device="cpu", compute_type="int8"):
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ImportError("faster-whisper not installed. pip install faster-whisper")
            
        print(f"[ASRService] Loading Faster-Whisper model '{model_size}' on {device}...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type, cpu_threads=4)
        self.last_text = "" # Context for next chunk
        print("[ASRService] Faster-Whisper model loaded.")
        
    def process_chunk(self, chunk: AudioChunk) -> Optional[TranscriptSegment]:
      
        import numpy as np
        
        # AudioChunk data is bytes, converting to float32 
        audio_int16 = np.frombuffer(chunk.data, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        
        # Transcribing with context CUZ SHITS TOO DUMB
        prompt = self.last_text[-200:] if self.last_text else None
        
        segments, info = self.model.transcribe(
            audio_float32, 
            beam_size=1, # Greedy decoding for speed AHAHHHHHHH(was 5)
            best_of=1,
            temperature=0.0,
            language="en", 
            task="transcribe",
            vad_filter=True,
            condition_on_previous_text=True,
            initial_prompt=prompt,
            no_speech_threshold=0.6,
            log_prob_threshold=-1.0, 
            compression_ratio_threshold=2.4
        )
        
        # Collecting and updating
        text_segments = [segment.text for segment in segments]
        full_text = " ".join(text_segments).strip()
        
        if full_text:
            self.last_text += " " + full_text
            self.last_text = self.last_text.strip()
            
            return TranscriptSegment(
                text=full_text,
                start_time=chunk.timestamp,
                end_time=chunk.timestamp + chunk.duration,
                confidence=0.9, 
                is_final=True
            )
        return None
