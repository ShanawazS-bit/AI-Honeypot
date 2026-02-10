import sounddevice as sd
import threading
import queue
import asyncio
from typing import List, Optional

class AudioStreamService:

    """
    capturing system ka  microphone
    and distributes the raw audio stream to multiple subscribers (Queues).
    
    abhi going to ASR Model(large chunks) and elevenlabs(smaller chunks)
    cuz dono ko need the voicemodel 
    
    """
    
    def __init__(self, sample_rate=16000, channels=1, blocksize=512): # approx 32ms
        self.sample_rate = sample_rate
        self.channels = channels
        self.blocksize = blocksize
        self.subscribers: List[queue.Queue] = []
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        """
        Returns a Queue that will receive audio bytes.
        """
        q = queue.Queue()
        with self._lock:
            self.subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._lock:
            if q in self.subscribers:
                self.subscribers.remove(q)

    def _stream_callback(self, indata, frames, time, status):
        """
        Callback from sounddevice. Runs in a separate thread.
        """
        if status:
            print(f"[AudioStream] Status: {status}")
            
        audio_bytes = indata.tobytes()
        
        with self._lock:
            for q in self.subscribers:
                try:
                    q.put_nowait(audio_bytes)
                except queue.Full:
                    pass # Drop frames if consumer is too slow, to prevent memory leak

    def start(self):
        """Starts the microphone capture in a background thread."""
        if self.running:
            return
            
        self.running = True
        
        def runner():
            print(f"[audiostream] starting capture {self.sample_rate}hz, blocksize={self.blocksize}...")
            try:
                with sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype='int16',
                    blocksize=self.blocksize,
                    callback=self._stream_callback
                ):
                    while self.running:
                        sd.sleep(100)
            except Exception as e:
                print(f"[audiostream] error: {e}")
                self.running = False

        self.thread = threading.Thread(target=runner, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join()
        print("[audiostream] stopped")
