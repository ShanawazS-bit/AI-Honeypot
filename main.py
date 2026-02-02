import argparse
import sys
import wave
import struct
import math
import os
from src.pipeline import DetectionPipeline

def generate_dummy_wav(filename: str, duration: float = 10.0):
    """Generates a dummy WAV file with sine wave tone."""
    print(f"Generating dummy audio to {filename}...")
    sample_rate = 16000
    n_samples = int(sample_rate * duration)
    
    with wave.open(filename, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        
        # specific 440Hz sine wave
        for i in range(n_samples):
            value = int(32767.0 * 0.5 * math.sin(2 * math.pi * 440 * i / sample_rate))
            data = struct.pack('<h', value)
            wf.writeframes(data)

def main():
    parser = argparse.ArgumentParser(description="AI Honeypot Detection System Demo")
    parser.add_argument("--file", type=str, help="Path to a WAV file to simulate (16kHz mono recommended).")
    parser.add_argument("--backend", choices=['vosk', 'mock'], default='mock', help="ASR backend to use.")
    parser.add_argument("--live", action='store_true', help="Use live microphone input instead of file.")
    parser.add_argument("--language", choices=['en', 'hi', 'mix'], default='en', help="Language code (en, hi, or mix).")
    args = parser.parse_args()
    
    # Initialize Pipeline
    use_mock_asr = (args.backend == 'mock')
    
    try:
        pipeline = DetectionPipeline(use_mock_asr=use_mock_asr, language=args.language)
        
        if args.live:
            pipeline.process_microphone_simulation()
        else:
            # Setup Audio File
            target_file = args.file
            if not target_file:
                target_file = "dummy_call.wav"
                if not os.path.exists(target_file):
                    generate_dummy_wav(target_file)
                    print("No file provided. Generated 'dummy_call.wav' for simulation.")
            
            pipeline.process_file_simulation(target_file)
        
    except KeyboardInterrupt:
        print("\nStopping simulation.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
