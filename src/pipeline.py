import time
import uuid
import threading
from typing import Optional

from .models import CallState, AudioChunk
from .audio_chunker import AudioChunker
from .audio_chunker import AudioChunker
from .asr_service import VoskASRService, MockASRService, MultiVoskASRService
from .paralinguistic import ParalinguisticAnalyzer
from .paralinguistic import ParalinguisticAnalyzer
from .semantic import SemanticAnalyzer
from .sequencer import BehavioralSequencer
from .scorer import FraudRiskScorer
from .honeypot import HoneypotAgent

class DetectionPipeline:
    """
    Orchestrates the real-time detection flow.
    
    Data Flow:
    Audio -> [Chunker] -> [ASR] & [Paralinguistic] -> [Semantic] -> [Sequencer] -> [Scorer] -> Decision
    """
    
    def __init__(self, use_mock_asr=False, language="en"):
        self.call_state = CallState(call_id=str(uuid.uuid4()))
        
        # Initialize Components
        print(f"[Pipeline] Initializing components (Language: {language})...")
        
        self.chunker = AudioChunker(chunk_duration=1.0) # 1 sec window
        
        if use_mock_asr:
            self.asr = MockASRService()
        else:
            try:
                if language == "mix":
                    self.asr = MultiVoskASRService()
                else:
                    self.asr = VoskASRService(language=language)
            except ImportError:
                 print("[Pipeline] Vosk failed to load, falling back to Mock ASR.")
                 self.asr = MockASRService()
            except FileNotFoundError as e:
                print(f"[Pipeline] {e}")
                print("[Pipeline] specific Vosk model not found. Falling back to Mock.")
                self.asr = MockASRService()
        
        self.para_analyzer = ParalinguisticAnalyzer()
        self.sem_analyzer = SemanticAnalyzer()
        self.sequencer = BehavioralSequencer()
        self.scorer = FraudRiskScorer()
        self.honeypot = HoneypotAgent()
        
        print("[Pipeline] Initialization complete.")
        
    def process_file_simulation(self, file_path: str):
        """
        Runs the pipeline on a file as if it were a live call.
        """
        print(f"\n[Pipeline] Starting simulation on {file_path}")
        
        chunk_gen = self.chunker.process_file_stream(file_path)
        
        for chunk in chunk_gen:
            self._process_single_chunk(chunk)
            
            # If Honeypot takes over, we might divert logic here
            if self.honeypot.is_active:
                # In a real system, we would stop processing input for detection
                # and start generating output.
                # For simulation, we just log that we are in honeypot mode.
                pass
                
    def process_microphone_simulation(self):
        """
        Runs the pipeline on live microphone input.
        """
        print(f"\n[Pipeline] Starting LIVE microphone capture...")
        
        chunk_gen = self.chunker.process_microphone_stream()
        
        for chunk in chunk_gen:
            self._process_single_chunk(chunk)
            
            if self.honeypot.is_active:
                # In real system, output audio here
                pass

    def _process_single_chunk(self, chunk: AudioChunk):
        """
        Core logic for one window of audio.
        """
        start_time = time.time()
        
        # 1. Parallel Analysis (ASR + Paralinguistics)
        # In python, GIL prevents true parallel CPU work without multiprocessing,
        # but for IO bound or C-extension libs (like Vosk/OpenSMILE) it might help.
        # For simplicity/clarity, we run sequential here as latency is low enough for 1s chunks.
        
        # ASR
        transcript_segment = self.asr.process_chunk(chunk)
        
        # Paralinguistics
        para_features = self.para_analyzer.analyze(chunk)
        
        if transcript_segment:
            print(f"  » Transcript: '{transcript_segment.text}' (Conf: {transcript_segment.confidence:.2f})")
            
            # 2. Semantic Analysis
            intent = self.sem_analyzer.analyze(transcript_segment.text)
            print(f"  » Intent: {intent.label} ({intent.confidence:.2f})")
            
            # 3. Sequencing
            new_stage = self.sequencer.update_state(self.call_state, intent)
            
            # 4. Scoring
            risk_score = self.scorer.calculate_score(self.call_state, para_features, intent)
            self.call_state.risk_history.append(risk_score)
            
            print(f"  » Risk Score: {risk_score.score:.2f} [{risk_score.level}]")
            if risk_score.trigger_factors:
                print(f"    ⚠ Triggers: {', '.join(risk_score.trigger_factors)}")
                
            # 5. Escalation Decision
            if risk_score.level in ["HIGH", "CRITICAL"]:
                if not self.honeypot.is_active:
                    self.honeypot.activate(self.call_state)
        
        else:
             # Even without text, paralinguistics might be relevant (e.g. heavy silence or noise)
             # But our FSM relies on intent currently.
             pass
             
        proc_time = (time.time() - start_time) * 1000
        # print(f"  [Perf] Chunk processed in {proc_time:.1f}ms") 
