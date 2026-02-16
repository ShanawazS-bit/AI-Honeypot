import json
import uuid
import asyncio
import struct
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
import os
import time
from asgiref.sync import sync_to_async

class AudioStreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for receiving real-time audio streams from Android app.
    Processes audio through the detection pipeline and sends fraud alerts back.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id = None
        self.pipeline = None
        self.audio_buffer = bytearray()
        self.phone_number = "Unknown"
        
    async def connect(self):
        """Handle WebSocket connection"""
        # Accept the connection
        await self.accept()
        
        # Generate session ID
        self.session_id = str(uuid.uuid4())
        
        print(f"[AudioStreamConsumer] WebSocket connected. Session ID: {self.session_id}")
        
        # Send session ID to client
        await self.send(text_data=json.dumps({
            'type': 'session_started',
            'session_id': self.session_id
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        print(f"[AudioStreamConsumer] WebSocket disconnected. Session: {self.session_id}, Code: {close_code}")
        
        # Save session log if pipeline was initialized
        if self.pipeline:
            await sync_to_async(self.pipeline.save_session_log)()
        
    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming messages (text or binary audio data)"""
        
        if text_data:
            # Handle JSON control messages
            try:
                data = json.loads(text_data)
                message_type = data.get('type')
                
                if message_type == 'setup':
                    # Initialize session with metadata
                    self.phone_number = data.get('phone_number', 'Unknown')
                    await self._initialize_pipeline()
                    
                    await self.send(text_data=json.dumps({
                        'type': 'setup_complete',
                        'status': 'ready'
                    }))
                    
                elif message_type == 'end_session':
                    # Finalize session
                    if self.pipeline:
                        await sync_to_async(self.pipeline.save_session_log)()
                    
                    await self.send(text_data=json.dumps({
                        'type': 'session_ended',
                        'session_id': self.session_id
                    }))
                    
            except json.JSONDecodeError as e:
                print(f"[AudioStreamConsumer] JSON decode error: {e}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Invalid JSON format'
                }))
        
        elif bytes_data:
            # Handle binary audio data
            if not self.pipeline:
                await self._initialize_pipeline()
            
            # Process audio chunk
            await self._process_audio_chunk(bytes_data)
    
    async def _initialize_pipeline(self):
        """Initialize the detection pipeline"""
        if self.pipeline is not None:
            return
        
        print(f"[AudioStreamConsumer] Initializing pipeline for session {self.session_id}")
        
        # Import here to avoid circular imports
        from src.pipeline import DetectionPipeline
        from src.models import CallState
        
        loop = asyncio.get_running_loop()

        # Create pipeline with callback for fraud alerts
        def fraud_alert_callback(risk_score):
            """Callback to send fraud alerts to client"""
            if risk_score.level in ["HIGH", "CRITICAL"]:
                asyncio.run_coroutine_threadsafe(self.send(text_data=json.dumps({
                    'type': 'fraud_alert',
                    'risk_level': risk_score.level,
                    'score': risk_score.score,
                    'triggers': risk_score.trigger_factors,
                    'session_id': self.session_id
                })), loop)
                
        def transcript_callback(text):
            """Callback to send transcripts to client"""
            print(f"[AudioStreamConsumer] Transcript callback triggered: '{text}'")
            asyncio.run_coroutine_threadsafe(self.send(text_data=json.dumps({
                'type': 'transcript',
                'transcript': text,
                'session_id': self.session_id
            })), loop)
            print(f"[AudioStreamConsumer] Transcript sent to client")
        
        # Initialize pipeline in a thread-safe way
        self.pipeline = await sync_to_async(DetectionPipeline)(
            backend='whisper',  # Changed from 'mock' to enable real ASR
            language='en',
            transcript_callback=transcript_callback
        )
        self.pipeline.call_state.call_id = self.session_id
        self.pipeline.fraud_alert_callback = fraud_alert_callback
        
        print(f"[AudioStreamConsumer] Pipeline initialized for {self.session_id}")
    
    async def _process_audio_chunk(self, audio_data):
        """Process incoming audio chunk through the pipeline"""
        try:
            print(f"[AudioStreamConsumer] Received audio chunk: {len(audio_data)} bytes")
            
            # Audio data is expected to be PCM 16-bit mono at 16kHz
            # Convert bytes to the format expected by the pipeline
            
            from src.models import AudioChunk
            
            # Create AudioChunk object
            chunk = AudioChunk(
                data=audio_data,
                sample_rate=16000,
                timestamp=time.time()
            )
            
            print(f"[AudioStreamConsumer] Processing chunk through pipeline...")
            # Process through pipeline (run in thread pool to avoid blocking)
            await sync_to_async(self.pipeline._process_single_chunk)(chunk)
            print(f"[AudioStreamConsumer] Chunk processed successfully")
            
        except Exception as e:
            print(f"[AudioStreamConsumer] Error processing audio chunk: {e}")
            import traceback
            traceback.print_exc()
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Audio processing error: {str(e)}'
            }))
