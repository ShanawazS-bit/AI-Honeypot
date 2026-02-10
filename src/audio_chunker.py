import wave
import time
import threading
from queue import Queue
from typing import Generator, Optional
import collections
from .models import AudioChunk
from .models import AudioChunk

try:
    import sounddevice as sd
    SD_AVAILABLE = True
except ImportError:
    SD_AVAILABLE = False
    print("[AudioChunker] Warning: 'sounddevice' not found. Live mic not available.")

class AudioChunker:
    """
    initiallity splitting audio stream into fixed-duration chunks for processing
    
       """
    
    def __init__(self, chunk_duration: float = 1.0, overlap: float = 0.0):
        """
        Initialize the AudioChunker.

        Args:
            chunk_duration (float): Length of each chunk in seconds.
            overlap (float): Overlap between chunks (not yet implemented too much sar khau).
        """
        self.chunk_duration = chunk_duration
        self.overlap = overlap
        self.queue = Queue()
        self.is_running = False
        
    def process_file_stream(self, file_path: str) -> Generator[AudioChunk, None, None]:
        """

        codeblock implemented from official docs 

        Args:
            file_path (str): Path to the WAV file to stream.
            
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

    def process_queue_stream(self, input_queue: Queue) -> Generator[AudioChunk, None, None]:
        """
        Consumes audio bytes from a Queue by AudioStreamService
        """
        sample_rate = 16000
        bytes_per_sample = 2 # int16
        channels = 1
        
        target_bytes = int(sample_rate * self.chunk_duration * bytes_per_sample * channels)
        
        buffer = bytearray()
        
        print(f"[AudioChunker] processing queue stream...")
        
        while True:
            try:


                data = input_queue.get()
                if data is None:
                    break
                
                buffer.extend(data)
                
                while len(buffer) >= target_bytes:
                    # Extract one chunk
                    chunk_data = bytes(buffer[:target_bytes])
                    del buffer[:target_bytes]
                    
                    chunk = AudioChunk(
                        data=chunk_data,
                        timestamp=time.time(),
                        duration=self.chunk_duration,
                        sample_rate=sample_rate
                    )
                    yield chunk
                    
            except Exception as e:
                print(f"[AudioChunker] Queue processing error: {e}")
                break

class VADAudioChunker:
    """
    Splitting audio based on Voice Activity Detection (VAD).
    """
    def __init__(self, sample_rate=16000, frame_duration_ms=30, padding_duration_ms=300, vad_aggressiveness=3):
        try:
            import webrtcvad
        except ImportError:
            raise ImportError("webrtcvad not installed. Run 'pip install webrtcvad'.")
            
        self.vad = webrtcvad.Vad(vad_aggressiveness)
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.frame_bytes = self.frame_size * 2 # int16
        
        # Ring buffer for padding (silence before/after speech)
        num_padding_frames = int(padding_duration_ms / frame_duration_ms)
        self.padding_window = collections.deque(maxlen=num_padding_frames)
        
        self.triggered = False
        self.voiced_frames = []
        
    def process_queue_stream(self, input_queue: Queue) -> Generator[AudioChunk, None, None]:
        """
        Consumes bytes from queue, frames them, and yields chunks on speech segments.
        """
        import collections
        
        buffer = bytearray()
        
        print(f"[VADChunker] processing queue stream (VAD Mode)...")
        
        while True:
            try:
                # 1. Get data
                chunk_bytes = input_queue.get()
                if chunk_bytes is None:
                    break
                    
                buffer.extend(chunk_bytes)
                
                # 2. Process complete frames
                while len(buffer) >= self.frame_bytes:
                    frame = bytes(buffer[:self.frame_bytes])
                    del buffer[:self.frame_bytes]
                    
                    is_speech = self.vad.is_speech(frame, self.sample_rate)
                    
                    if not self.triggered:
                        # We are waiting for speech
                        self.padding_window.append((frame, is_speech))
                        
                        if is_speech:
                            self.triggered = True
                            # Add buffered lead-in
                            for f, _ in self.padding_window:
                                self.voiced_frames.append(f)
                            self.padding_window.clear()
                            
                    else:
                        # We are IN speech
                        self.voiced_frames.append(frame)
                        
                        # Add to silence buffer to check for end
                        self.padding_window.append((frame, is_speech))
                        
                        # End detection: if > 90% of window is silence?
                        num_unvoiced = len([f for f, speech in self.padding_window if not speech])
                        if num_unvoiced > 0.9 * self.padding_window.maxlen:
                            
                            self.triggered = False
                            
                            raw_data = b''.join(self.voiced_frames)
                            duration = len(raw_data) / (self.sample_rate * 2)
                            
                            if duration > 0.5: 
                                yield AudioChunk(
                                    data=raw_data,
                                    timestamp=time.time(),
                                    duration=duration,
                                    sample_rate=self.sample_rate
                                )
                            
                            self.voiced_frames = []
                            self.padding_window.clear()
                            
            except Exception as e:
                print(f"[VADChunker] Error: {e}")
                break

#ignore code below, its for reading audio files locally(generated for testing purpouses only)



    def process_file_stream(self, file_path: str) -> Generator[AudioChunk, None, None]:
        """
        """
        import wave
        try:
            with wave.open(file_path, 'rb') as wf:
                sample_rate = wf.getframerate()
                if sample_rate != self.sample_rate:
                    print(f"[VADChunker] Warning: File SR {sample_rate} != VAD SR {self.sample_rate}")
                
                print(f"[VADChunker] Streaming file: {file_path}")
                
                # Reset VAD State
                self.triggered = False
                self.voiced_frames = []
                self.padding_window.clear()
                
                while True:
                    data = wf.readframes(self.frame_size)
                    if not data:
                        break
                        
                    # Handle incomplete last frame
                    if len(data) < self.frame_bytes:
                        break
                        
                    is_speech = self.vad.is_speech(data, self.sample_rate)
                    
                    if not self.triggered:
                        self.padding_window.append((data, is_speech))
                        if is_speech:
                            self.triggered = True
                            for f, _ in self.padding_window:
                                self.voiced_frames.append(f)
                            self.padding_window.clear()
                    else:
                        self.voiced_frames.append(data)
                        self.padding_window.append((data, is_speech))
                        num_unvoiced = len([f for f, speech in self.padding_window if not speech])
                        if num_unvoiced > 0.9 * self.padding_window.maxlen:
                            self.triggered = False
                            
                            raw_data = b''.join(self.voiced_frames)
                            duration = len(raw_data) / (self.sample_rate * 2)
                            
                            if duration > 0.5:
                                yield AudioChunk(
                                    data=raw_data,
                                    timestamp=time.time(),
                                    duration=duration,
                                    sample_rate=self.sample_rate
                                )
                                # Simulate processing time / real-time if needed
                                # Start of next chunk is nowtime...
                                # For simulation, user might want speed. Let's not sleep too much.
                                # But pipeline expects real-time-ish behavior?
                                # Original AudioChunker slept. Let's sleep a bit less or same?
                                # Let's sleep for duration to simulate real-time.
                                time.sleep(duration)
                                
                            self.voiced_frames = []
                            self.padding_window.clear()
                            
        except Exception as e:
            print(f"[VADChunker] File Error: {e}")
