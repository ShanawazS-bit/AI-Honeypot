import asyncio
import websockets
import json
import base64
import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import queue
from typing import Optional, Callable
import os

class ElevenLabsAgentClient:
    """
    basic websocket to interact wiht the 11labs agent     
    this sends audio
    recieves audio and plays them
    
    1. Sending microbial audio to the agent.
    2. Receiving and playing agent audio responses.
    3. Receiving transcripts to feed the fraud detection system.
    """
    
    def __init__(self, agent_id: str, input_queue: queue.Queue, on_transcript: Optional[Callable[[str, str], None]] = None):
        self.agent_id = agent_id
        self.uri = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={agent_id}"
        self.on_transcript = on_transcript
        self.input_queue = input_queue
        self.running = False
        self.ws = None
        self.conversation_id = None
        
        # Audio Playback Handling
        self.playback_queue = queue.Queue()
        self.playback_thread: Optional[threading.Thread] = None

    def get_conversation_analysis(self):
        """
        Fetches the conversation analysis/summary from the ElevenLabs API.
        Retries for up to 5 seconds if the analysis is not yet ready.
        """
        if not self.conversation_id:
            print("[Agent] No conversation ID available to fetch summary.")
            return None
            
        import requests
        import time
        
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            print("[Agent] No API Key found. Cannot fetch summary.")
            return None
            
        url = f"https://api.elevenlabs.io/v1/convai/conversations/{self.conversation_id}"
        headers = {"xi-api-key": api_key}
        
        print(f"[Agent] Fetching summary for {self.conversation_id} (Polling up to 5s)...")
        
        for attempt in range(5):
            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    # Check if analysis is ready (non-null)
                    if data.get("analysis"):
                        return data
                    else:
                        print(f"[Agent] Analysis not ready yet... (Attempt {attempt+1}/5)")
                elif response.status_code == 401 or "missing_permissions" in response.text:
                    print(f"[Agent] PERMISSION ERROR: Your API Key cannot read conversations.")
                    print("       Please enable the 'convai_read' permission in your ElevenLabs API Key settings.")
                    return None
                else:
                    print(f"[Agent] Failed to fetch summary (Status {response.status_code}): {response.text}")
                    # Proceed to retry if it might be temporary, or break?
                    # Let's retry just in case
            except Exception as e:
                print(f"[Agent] API Request Error: {e}")
            
            time.sleep(1.0)
            
        print("[Agent] Timed out waiting for summary.")
        return None

    def _playback_worker(self):
        """
        Worker thread for playing audio from the queue.
        Uses a persistent OutputStream to avoid PortAudio conflicts.
        """
        print("[Agent] Playback worker started.")
        try:
            # opening a persistent output stream
            # assuming 16kHz mono int16 based on 11Labs output
            with sd.OutputStream(samplerate=16000, channels=1, dtype='int16') as stream:
                while self.running:
                    try:
                        audio_chunk = self.playback_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    
                    if audio_chunk is None: 
                        break
                        
                    try:
                        stream.write(audio_chunk)
                    except Exception as e:
                        print(f"[Agent] Playback Stream Error: {e}")
                        
        except Exception as e:
            print(f"[Agent] Failed to Initialize Output Stream: {e}")
            print("[Agent] Audio will not be played.")

    async def _send_audio(self):
        """Consumes (fast) audio chunks from queue and sends to WebSocket."""
        try:
            loop = asyncio.get_running_loop()
            print("[Agent] Audio sender started (waiting for queue data)...")
            
            while self.running:
                try:
                 
                    data = await loop.run_in_executor(None, self.input_queue.get)
                except Exception:
                    continue
                    
                if data is None: 
                    break
                    
                if self.ws:
                    # Convert to base64
                    b64_data = base64.b64encode(data).decode('utf-8')
                    
                    # Send
                    message = {
                        "user_audio_chunk": b64_data
                    }
                    try:
                        await self.ws.send(json.dumps(message))
                    except Exception as e:
                        print(f"[Agent] Send Error: {e}")
                        break
                        
        except Exception as e:
            print(f"[Agent] Audio Input Error: {e}")

    async def _handle_messages(self):
        """Receives messages from WebSocket (Audio + Events)."""
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    print(f"[Agent] Received non-JSON message: {message}")
                    continue
                
                if not isinstance(data, dict):
                     print(f"[Agent] Received non-dict message: {data}")
                     continue

                type_ = data.get("type")

                # Handle Init Metadata (Capture Conversation ID)
                if type_ == "conversation_initiation_metadata":
                    event = data.get("conversation_initiation_metadata_event")
                    if event:
                        self.conversation_id = event.get("conversation_id")
                        print(f"[Agent] Conversation ID detected: {self.conversation_id}")

                # Handle Audio Response
                elif data.get("audio_event"):
                    # Decode and queue for playback
                    audio_b64 = data["audio_event"]["audio_base_64"]
                    if audio_b64:
                        try:
                            audio_bytes = base64.b64decode(audio_b64)
                            # Convert to numpy array for sounddevice
                            audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
                            
                            # Put into playback queue
                            self.playback_queue.put(audio_array)
                            
                        except Exception as e:
                            print(f"[Agent] Audio Decode Error: {e}")

                # Handle Transcription
                elif type_ == "user_transcript":
                    event = data.get("user_transcript_event")
                    if isinstance(event, dict):
                         transcript_obj = event.get("user_transcript")
                         if isinstance(transcript_obj, dict):
                             transcript = transcript_obj.get("content")
                             if transcript and self.on_transcript:
                                 print(f"[Agent] User said: {transcript}")
                                 self.on_transcript("user", transcript)
                         
                elif type_ == "agent_response":
                    event = data.get("agent_response_event")
                    if isinstance(event, dict):
                         response_obj = event.get("agent_response")
                         if isinstance(response_obj, dict):
                             response = response_obj.get("content")
                             if response:
                                 print(f"[Agent] Agent said: {response}")
                                 
        except websockets.exceptions.ConnectionClosed:
            print("[Agent] Connection detected closed.")

    async def _run_loop(self):
        print(f"[Agent] Connecting to ElevenLabs Agent {self.agent_id}...")
        api_key = os.getenv("ELEVENLABS_API_KEY")
        
        # Build URL with Auth
        auth_uri = self.uri
        if api_key:
             auth_uri += f"&xi-api-key={api_key}"
        
        try:
            async with websockets.connect(auth_uri) as websocket:
                self.ws = websocket
                self.running = True
                print("[Agent] Connected!")
                
                self.playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
                self.playback_thread.start()
                
                mic_task = asyncio.create_task(self._send_audio())
                recv_task = asyncio.create_task(self._handle_messages())
                
                await asyncio.gather(mic_task, recv_task)
        except websockets.exceptions.ConnectionClosed as e:
             print(f"[Agent] Connection closed: {e.code} - {e.reason}")
        except Exception as e:
             print(f"[Agent] Connection Error: {e}")
        finally:
             if self.playback_thread:
                 self.playback_queue.put(None) 
    def start(self):
        """Starts the agent client in a separate thread (blocking wrapper for async)."""
        def runner():
            asyncio.run(self._run_loop())
            
        self.thread = threading.Thread(target=runner)
        self.thread.start()

    def stop(self):
        self.running = False
        # Signal playback thread to stop
        self.playback_queue.put(None) 
        
        if self.thread:
            self.thread.join()
        
        if self.playback_thread:
            self.playback_thread.join()
