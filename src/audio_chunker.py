import wave
import time
import threading
from queue import Queue
from typing import Generator, Optional
from .models import AudioChunk

try:
    import sounddevice as sd
    SD_AVAILABLE = True
except ImportError:
    SD_AVAILABLE = False
    print("[AudioChunker] Warning: 'sounddevice' not found. Live mic not available.")

class AudioChunker:
    """
    Splits an audio stream (or file) into fixed-duration chunks for processing.
    
    This component ensures that the downstream components (ASR, Paralinguistics)
    receive data in manageable windows (e.g., 0.5s to 2.0s) to maintain low latency.
    """
    
    def __init__(self, chunk_duration: float = 1.0, overlap: float = 0.0):
        """
        Initialize the AudioChunker.

        Args:
            chunk_duration (float): Length of each chunk in seconds.
            overlap (float): Overlap between chunks (not yet implemented in this simple version).
        """
        self.chunk_duration = chunk_duration
        self.overlap = overlap
        self.queue = Queue()
        self.is_running = False
        
    def process_file_stream(self, file_path: str) -> Generator[AudioChunk, None, None]:
        """
        Simulates a live stream by reading a WAV file chunk by chunk with real-time delays.
        
        Args:
            file_path (str): Path to the WAV file to stream.
            
        Yields:
            AudioChunk: Sequential audio chunks as if they were arriving in real-time.
        """
        try:
            with wave.open(file_path, 'rb') as wf:
                sample_rate = wf.getframerate()
                channels = wf.getnchannels()
                width = wf.getsampwidth()
                
                # Calculate bytes per chunk
                # bytes_per_sample = width * channels
                # samples_per_chunk = int(sample_rate * self.chunk_duration)
                # chunk_size = samples_per_chunk * bytes_per_sample
                
                # For simplicity, we assume we want to read 'chunk_duration' worth of frames
                frames_per_chunk = int(sample_rate * self.chunk_duration)
                
                print(f"[AudioChunker] Streaming file: {file_path}")
                print(f"[AudioChunker] Sample Rate: {sample_rate}, Channels: {channels}")
                
                while True:
                    data = wf.readframes(frames_per_chunk)
                    if not data:
                        break
                        
                    # Calculate actual duration of this chunk (last chunk might be shorter)
                    # duration = len(data) / (sample_rate * width * channels)
                    actual_frames = len(data) // (width * channels)
                    duration = actual_frames / sample_rate
                    
                    chunk = AudioChunk(
                        data=data,
                        timestamp=time.time(),
                        duration=duration,
                        sample_rate=sample_rate
                    )
                    
                    yield chunk
                    
                    # Simulate real-time latency
                    # We sleep for the duration of the chunk to mimic a live stream
                    # In a real system, this would be blocked by hardware input
                    time.sleep(duration)
                    
        except FileNotFoundError:
            print(f"[AudioChunker] Error: File not found at {file_path}")
        except Exception as e:
            print(f"[AudioChunker] Error processing file: {e}")

    def stop(self):
        """Stops the chunking process."""
        self.is_running = False

    def process_microphone_stream(self) -> Generator[AudioChunk, None, None]:
        """
        Captures audio from the system microphone in real-time.
        """
        if not SD_AVAILABLE:
            print("[AudioChunker] Error: sounddevice not installed.")
            return

        sample_rate = 16000
        channels = 1
        block_size = int(sample_rate * self.chunk_duration) # Frames per chunk
        dtype = 'int16'
        
        print(f"[AudioChunker] Starting microphone stream ({sample_rate}Hz, Mono)...")
        print("[AudioChunker] Speak now! (Ctrl+C to stop)")
        
        try:
            with sd.InputStream(samplerate=sample_rate, channels=channels, dtype=dtype, blocksize=block_size) as stream:
                while True:
                     data, overflowed = stream.read(block_size)
                     if overflowed:
                         print("[AudioChunker] Warning: Audio buffer overflow")
                     
                     raw_bytes = data.tobytes()
                     chunk = AudioChunk(
                        data=raw_bytes,
                        timestamp=time.time(),
                        duration=self.chunk_duration,
                        sample_rate=sample_rate
                     )
                     yield chunk
        except Exception as e:
            print(f"[AudioChunker] Microphone error: {e}")
