import time
import uuid
import threading
from typing import Optional

from .models import CallState, AudioChunk
from .audio_chunker import AudioChunker, VADAudioChunker
from .audio_chunker import AudioChunker
from .asr_service import VoskASRService, MockASRService, MultiVoskASRService, FasterWhisperASRService
from .paralinguistic import ParalinguisticAnalyzer
from .paralinguistic import ParalinguisticAnalyzer
from .semantic import SemanticAnalyzer
from .sequencer import BehavioralSequencer
from .scorer import FraudRiskScorer
from .honeypot import HoneypotAgent
from .utils import text_to_digits
from .intelligence_extraction import IntelligenceExtractor
import json
from .intelligence_extraction import IntelligenceExtractor
from .audio_stream import AudioStreamService
import json
import os

class DetectionPipeline:
    """
    Orchestrates the real-time detection flow.
    
    Data Flow:
    Audio -> [Chunker] -> [ASR] & [Paralinguistic] -> [Semantic] -> [Sequencer] -> [Scorer] -> Decision
    """
    
    def __init__(self, backend="mock", language="en", transcript_callback=None):
        self.call_state = CallState(call_id=str(uuid.uuid4()))
        self.transcript_callback = transcript_callback
        
        # Initialize Components
        print(f"[Pipeline] Initializing components (Backend: {backend}, Language: {language})...")
        
        self.audio_stream = AudioStreamService()
        # Use VAD Chunker for ASR
        # Aggressiveness 1 (filtering non-speech) instead of 3 (strict) for better capture
        self.chunker = VADAudioChunker(frame_duration_ms=30, padding_duration_ms=300, vad_aggressiveness=1)
        self.agent_client = None # Will be initialized in _run_agent_mode
        
        if backend == "mock":
            self.asr = MockASRService()
        elif backend == "whisper":
            try:
                # User requested 'small' with high accuracy settings
                self.asr = FasterWhisperASRService(model_size="small")
            except ImportError as e:
                print(f"[Pipeline] Whisper failed to load: {e}")
                self.asr = MockASRService()
        else: # vosk or default
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
        
        try:
            for chunk in chunk_gen:
                self._process_single_chunk(chunk)
                
                # If Honeypot takes over, we might divert logic here
                if self.honeypot.is_active:
                    print("[Pipeline] Risk Threshold Met (File Sim). Switching to ElevenLabs Agent...")
                    break
        except Exception as e:
            print(f"[Pipeline] Error in file simulation loop: {e}")

        # Phase 2: Active Honeypot (ElevenLabs Agent)
        if self.honeypot.is_active:
             self._run_agent_mode()
                
    def process_microphone_simulation(self):
        """
        Runs the pipeline on live microphone input using Unified Audio Stream.
        """
        print(f"\n[Pipeline] Starting LIVE microphone capture (Unified Stream)...")
        
        # Start the background stream
        self.audio_stream.start()
        
        # Subscribe ASR to the stream
        asr_queue = self.audio_stream.subscribe()
        
        try:
            chunk_gen = self.chunker.process_queue_stream(asr_queue)
            
            # Phase 1: Passive Listening (Vosk/Whisper)
            try:
                for chunk in chunk_gen:
                    self._process_single_chunk(chunk)
                    
                    if self.honeypot.is_active:
                        print("[Pipeline] Risk Threshold Met. Switching to ElevenLabs Agent...")
                        # We continue holding the stream open!
                        break
            except Exception as e:
                print(f"[Pipeline] Error in passive loop: {e}")
                
            # Phase 2: Active Honeypot (ElevenLabs Agent)
            if self.honeypot.is_active:
                 # We might want to keep ASR running? Ideally yes, for logging user intent while Agent speaks.
                 # But for now, let's switch mode.
                 # self.audio_stream is STILL RUNNING.
                 self._run_agent_mode()
        finally:
            # Cleanup if we exit
            self.audio_stream.stop()

    def _process_single_chunk(self, chunk: AudioChunk):
        """
        Core logic for one window of audio.
        """
        # 1. ASR
        transcript_segment = self.asr.process_chunk(chunk)
        
        # 2. Paralinguistics (still useful if we have audio)
        para_features = self.para_analyzer.analyze(chunk)
        
        if transcript_segment:
            if self.transcript_callback:
                self.transcript_callback(transcript_segment.text)
            self._process_transcript_text(transcript_segment.text, para_features)
        
    def _process_transcript_text(self, text: str, para_features=None):
        """
        Shared logic for processing text from either Vosk or ElevenLabs Agent.
        """
        # Normalize: convert "one two three" to "1 2 3"
        normalized_text = text_to_digits(text)
        print(f"  » Transcript: '{normalized_text}' (Original: '{text}')")
        
        # 2. Semantic Analysis
        intent = self.sem_analyzer.analyze(normalized_text)
        print(f"  » Intent: {intent.label} ({intent.confidence:.2f})")
        
        # 3. Sequencing
        self.sequencer.update_state(self.call_state, intent)
        
        # Update Transcript History
        # We create a pseudo-segment for text-only inputs if not coming from ASR directly
        from .models import TranscriptSegment
        seg = TranscriptSegment(
            text=text, 
            start_time=time.time(), 
            end_time=time.time(), 
            confidence=1.0, 
            is_final=True
        )
        self.call_state.transcript_history.append(seg)
        
        # 4. Scoring
        if para_features is None:
             # If coming from Agent, we might not have raw audio features easily synced
             # Create dummy/neutral features or ignore
             from .models import ParalinguisticFeatures
             para_features = ParalinguisticFeatures()
             
        risk_score = self.scorer.calculate_score(self.call_state, para_features, intent)
        self.call_state.risk_history.append(risk_score)
        
        print(f"  » Risk Score: {risk_score.score:.2f} [{risk_score.level}]")
        if risk_score.trigger_factors:
            print(f"    ⚠ Triggers: {', '.join(risk_score.trigger_factors)}")
            
        # 5. Escalation Decision
        if risk_score.level in ["HIGH", "CRITICAL"]:
            if not self.honeypot.is_active:
                self.honeypot.activate(self.call_state)

    def _run_agent_mode(self):
        """
        Starts the ElevenLabs Agent using the existing AudioStream.
        """
        from .elevenlabs_agent import ElevenLabsAgentClient
        import os
        
        # Updated ID provided by user
        agent_id = os.getenv("ELEVENLABS_AGENT_ID", "agent_1201kh0syxkperjbb301chj9vfm7")
        
        # Subscribe Agent to the stream (Fast queue)
        agent_queue = self.audio_stream.subscribe()
        
        # Callback for Agent Transcripts
        def on_transcript(role, text):
            if role == "user":
                # Feed back into our fraud detection logic
                print(f"[Pipeline] Analyng Agent Transcript: {text}")
                self._process_transcript_text(text)
        
        self.agent_client = ElevenLabsAgentClient(agent_id=agent_id, input_queue=agent_queue, on_transcript=on_transcript)
        self.agent_client.start()
        
        print(f"[Pipeline] ElevenLabs Agent ({agent_id}) is ACTIVE.")
        print("[Pipeline] Streaming low-latency audio to Agent...")
        print("[Pipeline] Ctrl+C to stop.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("[Pipeline] Stopping Agent...")
            if self.agent_client:
                self.agent_client.stop()
            self.audio_stream.unsubscribe(agent_queue)
            raise # Re-raise to trigger save_session_log in main.py

    def save_session_log(self):
        """
        Saves the full session log and extracted intelligence to a JSON file.
        """
        print(f"\n[Pipeline] Saving session log for {self.call_state.call_id}...")
        
        # 1. Aggregate Transcript
        # We need to make sure we are capturing transcripts in the call_state
        # Currently _process_transcript_text doesn't explicitly modify transcript_history for text inputs?
        # Let's check call_state definition. It has transcript_history.
        # We should ensure we append to it in _process_transcript_text if not already.
        
        full_transcript = []
        full_text = ""
        
        # Collect from history (if populated) or we might need to rely on what we have.
        # For now, let's assume risk_history is populated, but transcript_history might need updates.
        # Actually, let's just use what we can.
        
        # If transcript_history is empty, we might have missed adding them.
        # Let's fix _process_transcript_text to append to history first.
        
        for seg in self.call_state.transcript_history:
            full_transcript.append({
                "timestamp": seg.start_time,
                "text": seg.text,
                "confidence": seg.confidence
            })
            full_text += seg.text + " "
            
        # 2. Fetch ElevenLabs Summary (if Agent was active)
        summary_text = ""
        agent_analysis = {}
        
        if self.agent_client:
            print("[Pipeline] Fetching official ElevenLabs Conversation Summary...")
            # We assume the agent thread has stopped or we can call this concurrently?
            # Ideally called after stop.
            analysis = self.agent_client.get_conversation_analysis()
            if analysis:
                agent_analysis = analysis
                # Extract summary/analysis text
                # Logic: analysis.get("analysis") can be None (if processing), so defaulting to {} via .get(..., {}) fails if the key exists but is None.
                analysis_data = analysis.get("analysis") or {}
                summary_text = analysis_data.get("transcript_summary", "")
                
                if not summary_text:
                     # Fallback to evaluation or other fields if available
                     summary_text = str(analysis.get("analysis", ""))
                
                print(f"[Pipeline] ElevenLabs Summary: {summary_text}")
            else:
                print("[Pipeline] No analysis returned from ElevenLabs.")
        
        # 3. Combine Texts for Intelligence Extraction
        # We prefer the summary for extraction as requested, but we should also check the raw text
        combined_text = full_text + " " + summary_text
        
        # 4. Extract Intelligence
        intelligence = IntelligenceExtractor.extract(combined_text)
        
        # 5. Create Report
        report = {
            "session_id": self.call_state.call_id,
            "timestamp": time.time(),
            "risk_level": self.call_state.risk_history[-1].level if self.call_state.risk_history else "UNKNOWN",
            "extracted_intelligence": {k: list(v) for k, v in intelligence.items()}, # Convert sets to lists
            "elevenlabs_analysis": agent_analysis,
            "transcript": full_transcript
        }
        
        # 6. Write to File
        os.makedirs("scam_logs", exist_ok=True)
        filename = f"scam_logs/session_{self.call_state.call_id}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"[Pipeline] Log saved to {filename}")
        print("---------------------------------------------------")
        print("EXTRACTED INTELLIGENCE (Initial):")
        for k, v in intelligence.items():
            if v:
                print(f"  {k}: {list(v)}")
        print("---------------------------------------------------")

        # 7. Delayed Update (User Request: Check again after 10s)
        # If we didn't get a good summary, or just to be sure we get the final one.
        if not summary_text or agent_analysis is None:
            print("\n[Pipeline] Waiting 10s for final ElevenLabs summary update...")
            time.sleep(10)
            
            print("[Pipeline] Re-fetching summary...")
            final_analysis = self.agent_client.get_conversation_analysis()
            
            if final_analysis:
                # Extract new summary
                analysis_data = final_analysis.get("analysis") or {}
                new_summary = analysis_data.get("transcript_summary", "")
                
                if new_summary:
                    print(f"[Pipeline] FINAL Summary received: {new_summary}")
                    
                    # Re-run extraction with new data
                    combined_text = full_text + " " + new_summary
                    new_intelligence = IntelligenceExtractor.extract(combined_text)
                    
                    # Update Report
                    report["elevenlabs_analysis"] = final_analysis
                    report["extracted_intelligence"] = {k: list(v) for k, v in new_intelligence.items()}
                    
                    # Re-save
                    with open(filename, 'w') as f:
                        json.dump(report, f, indent=2)
                        
                    print(f"[Pipeline] Log UPDATED with final summary at {filename}")
                    print("---------------------------------------------------")
                    print("EXTRACTED INTELLIGENCE (Final):")
                    for k, v in new_intelligence.items():
                        if v:
                            print(f"  {k}: {list(v)}")
                    print("---------------------------------------------------")
                else:
                    print("[Pipeline] Still no summary available after wait.")
            else:
                 print("[Pipeline] Re-fetch failed.")
