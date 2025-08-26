"""Voice capture module for memory system"""

import pyaudio
import wave
import tempfile
import os
from datetime import datetime
from pathlib import Path
import uuid
from typing import Optional
import threading
import time


class VoiceCapture:
    """Handle voice recording and capture"""
    
    def __init__(self, audio_dir: Optional[str] = None):
        """Initialize voice capture"""
        if audio_dir is None:
            memory_home = os.path.expanduser(os.getenv("MEMORY_HOME", "~/.memory"))
            audio_dir = os.path.join(memory_home, "audio")
        
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        # Audio settings
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000  # 16kHz is good for speech
        self.record_seconds = 60  # Max recording time
        
        self.p = None
        self.stream = None
        self.frames = []
        self.recording = False
    
    def start_recording(self) -> str:
        """Start recording audio"""
        self.p = pyaudio.PyAudio()
        
        # Find the default input device
        try:
            default_device = self.p.get_default_input_device_info()
            print(f"🎤 Recording from: {default_device['name']}")
        except:
            print("⚠️  No microphone found. Using default device 0")
        
        self.stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        self.frames = []
        self.recording = True
        
        print("🔴 Recording... Press Enter to stop")
        
        # Start recording in background thread
        recording_thread = threading.Thread(target=self._record)
        recording_thread.start()
        
        # Wait for Enter key
        input()
        
        # Stop recording
        self.recording = False
        recording_thread.join()
        
        # Save the audio
        audio_path = self._save_audio()
        
        print(f"✅ Recording saved: {audio_path}")
        return audio_path
    
    def _record(self):
        """Background recording thread"""
        while self.recording:
            try:
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                self.frames.append(data)
            except Exception as e:
                print(f"Recording error: {e}")
                break
        
        # Clean up
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()
    
    def _save_audio(self) -> str:
        """Save recorded audio to file"""
        audio_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"voice_{timestamp}_{audio_id[:8]}.wav"
        audio_path = self.audio_dir / filename
        
        # Save as WAV file
        wf = wave.open(str(audio_path), 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.format))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        
        return str(audio_path)
    
    def record_with_silence_detection(self, silence_duration: float = 2.0) -> str:
        """Record with automatic stop on silence (simplified version)"""
        # For now, just use the manual stop version
        # VAD can be added later for automatic silence detection
        return self.start_recording()


class SimpleVAD:
    """Simple Volume-based Activity Detection"""
    
    def __init__(self, threshold: int = 1000):
        """Initialize VAD with volume threshold"""
        self.threshold = threshold
    
    def is_speech(self, audio_chunk: bytes) -> bool:
        """Check if audio chunk contains speech based on volume"""
        # Convert bytes to integers
        import struct
        
        if len(audio_chunk) == 0:
            return False
        
        # Calculate RMS (Root Mean Square) for volume
        count = len(audio_chunk) / 2  # 16-bit audio
        format = "%dh" % count
        
        try:
            shorts = struct.unpack(format, audio_chunk)
            sum_squares = sum(s**2 for s in shorts)
            rms = (sum_squares / count) ** 0.5
            return rms > self.threshold
        except:
            return False