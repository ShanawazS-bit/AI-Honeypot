import numpy as np
import tempfile
import os
from .models import AudioChunk, ParalinguisticFeatures

# Try importing opensmile
try:
    import opensmile
    OPENSMILE_AVAILABLE = True
except ImportError as e:
    OPENSMILE_AVAILABLE = False
    print(f"[Paralinguistic] Warning: 'opensmile' import failed: {e}")

class ParalinguisticAnalyzer:
    """
    Analyzes audio for non-verbal cues (prosody, emotion indicators) using OpenSMILE.
    
    Extracts features like:
    - F0 (Fundamental Frequency/Pitch): High pitch can indicate stress/urgency.
    - Jitter/Shimmer: Micro-tremors in voice indicating nervousness or synthetic nature.
    - Loudness: Aggression or dominance.
    """
    
    def __init__(self):
        if OPENSMILE_AVAILABLE:
            # Initialize OpenSMILE with eGeMAPSv02 (Geneva Minimalistic Acoustic Parameter Set)
            # This is a standard set for affective computing.
            self.smile = opensmile.Smile(
                feature_set=opensmile.FeatureSet.eGeMAPSv02,
                feature_level=opensmile.FeatureLevel.Functionals,
            )
            print("[Paralinguistic] OpenSMILE initialized with eGeMAPSv02.")
        else:
            self.smile = None

    def analyze(self, chunk: AudioChunk) -> ParalinguisticFeatures:
        """
        Extracts features from the audio chunk.
        """
        if not self.smile or len(chunk.data) == 0:
            return ParalinguisticFeatures()

        try:
            # Convert raw bytes to numpy array (assumes 16-bit PCM)
            # data is bytes, need to convert to float32 or int16
            audio_data = np.frombuffer(chunk.data, dtype=np.int16)
            
            # OpenSMILE expects float audio [-1, 1] or file
             # Normalizing to float [-1, 1]
            audio_data_norm = audio_data.astype(np.float32) / 32768.0
            
            # process_signal expects (channels, samples) or (samples,)
            # We assume mono for now.
            result_df = self.smile.process_signal(
                audio_data_norm,
                chunk.sample_rate
            )
            
            if result_df.empty:
                return ParalinguisticFeatures()
             
            # Extract key metrics mapping from eGeMAPS
            # Note: actual feature names in eGeMAPS are complex (e.g., F0semitoneFrom27.5Hz_sma3nz_amean)
            # We map a few key ones.
            
            # F0 (Pitch)
            pitch = result_df.get('F0semitoneFrom27.5Hz_sma3nz_amean', [0])
            pitch = pitch.iloc[0] if hasattr(pitch, 'iloc') else pitch[0]
            
            pitch_var = result_df.get('F0semitoneFrom27.5Hz_sma3nz_stddevNorm', [0])
            pitch_var = pitch_var.iloc[0] if hasattr(pitch_var, 'iloc') else pitch_var[0]
            
            # Loudness
            loudness = result_df.get('loudness_sma3_amean', [0])
            loudness = loudness.iloc[0] if hasattr(loudness, 'iloc') else loudness[0]
            
            # Jitter/Shimmer (Voice Quality)
            jitter = result_df.get('jitterLocal_sma3nz_amean', [0])
            jitter = jitter.iloc[0] if hasattr(jitter, 'iloc') else jitter[0]

            shimmer = result_df.get('shimmerLocaldB_sma3nz_amean', [0])
            shimmer = shimmer.iloc[0] if hasattr(shimmer, 'iloc') else shimmer[0]
            
            # Rate (Simulation/Approximation as opensmile 'rate' features are specific)
            # We use `temporal` features if available, otherwise 0
            
            return ParalinguisticFeatures(
                pitch_mean=float(pitch),
                pitch_variance=float(pitch_var),
                intensity_mean=float(loudness),
                speaking_rate=0.0, # Not directly in standard function level without setup
                jitter=float(jitter),
                shimmer=float(shimmer)
            )
            
        except Exception as e:
            print(f"[Paralinguistic] Error processing chunk: {e}")
            return ParalinguisticFeatures()
