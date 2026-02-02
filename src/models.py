from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import time

@dataclass
class AudioChunk:
    """
    Represents a chunk of raw audio data captured from the stream.
    
    Attributes:
        data (bytes): The raw bytes of the audio chunk.
        timestamp (float): The system timestamp when this chunk was captured.
        duration (float): The duration of the chunk in seconds.
        sample_rate (int): The sample rate of the audio (e.g., 16000 Hz).
    """
    data: bytes
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0
    sample_rate: int = 16000

@dataclass
class TranscriptSegment:
    """
    Represents a recognized segment of speech from the ASR engine.
    
    Attributes:
        text (str): The recognized text content.
        start_time (float): Relative start time of the segment in the stream.
        end_time (float): Relative end time of the segment in the stream.
        confidence (float): The ASR model's confidence in this recognition (0.0 to 1.0).
        is_final (bool): Whether this result is final or partial.
    """
    text: str
    start_time: float
    end_time: float
    confidence: float
    is_final: bool = True

@dataclass
class ParalinguisticFeatures:
    """
    Container for vocal features extracted by OpenSMILE.
    
    Attributes:
        pitch_mean (float): Average pitch (F0) in the segment.
        pitch_variance (float): Variation in pitch (jitter/instability).
        intensity_mean (float): Average loudness/energy.
        speaking_rate (float): Estimated syllables or phonemes per second.
        jitter (float): Micro-fluctuations in pitch (stress indicator).
        shimmer (float): Micro-fluctuations in amplitude (stress indicator).
    """
    pitch_mean: float = 0.0
    pitch_variance: float = 0.0
    intensity_mean: float = 0.0
    speaking_rate: float = 0.0
    jitter: float = 0.0
    shimmer: float = 0.0

@dataclass
class SemanticIntent:
    """
    Classification of the speaker's intent based on the transcript.
    
    Attributes:
        label (str): The primary intent label (e.g., 'GREETING', 'URGENCY', 'THREAT').
        confidence (float): Probability score of the intent (0.0 to 1.0).
        keywords_detected (List[str]): Specific keywords that triggered this intent.
    """
    label: str
    confidence: float
    keywords_detected: List[str] = field(default_factory=list)

@dataclass
class RiskScore:
    """
    The aggregated fraud risk assessment for a specific point in time.
    
    Attributes:
        score (float): The normalized risk score (0.0 to 1.0).
        level (str): Categorical risk level ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL').
        trigger_factors (List[str]): Reasons why the risk is high (e.g., 'High Urgency', 'Threat Detected').
        timestamp (float): When this score was calculated.
    """
    score: float
    level: str
    trigger_factors: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

@dataclass
class CallState:
    """
    The global state of the current call processing.
    
    Attributes:
        call_id (str): Unique identifier for the call.
        current_phase (str): Current FSM state (e.g., 'GREETING').
        transcript_history (List[TranscriptSegment]): Full conversation log.
        risk_history (List[RiskScore]): History of risk assessments.
        is_active (bool): Whether the call is still valid/active.
    """
    call_id: str
    current_phase: str = "START"
    transcript_history: List[TranscriptSegment] = field(default_factory=list)
    risk_history: List[RiskScore] = field(default_factory=list)
    is_active: bool = True
