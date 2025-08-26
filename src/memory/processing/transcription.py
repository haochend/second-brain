"""Transcription module using Whisper"""

import whisper
import os
from typing import Optional
from pathlib import Path


class WhisperTranscriber:
    """Transcribe audio using OpenAI Whisper"""
    
    def __init__(self, model_name: Optional[str] = None):
        """Initialize Whisper transcriber"""
        self.model_name = model_name or os.getenv("WHISPER_MODEL", "base")
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load Whisper model"""
        print(f"Loading Whisper model: {self.model_name}")
        try:
            self.model = whisper.load_model(self.model_name)
            print(f"✅ Whisper {self.model_name} model loaded")
        except Exception as e:
            print(f"⚠️  Error loading Whisper model: {e}")
            print("Falling back to 'base' model")
            self.model = whisper.load_model("base")
    
    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text"""
        if not self.model:
            raise RuntimeError("Whisper model not loaded")
        
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            # Transcribe with Whisper
            result = self.model.transcribe(
                audio_path,
                language="en",  # Force English for now
                fp16=False  # Disable FP16 for CPU compatibility
            )
            
            # Return the transcribed text
            text = result["text"].strip()
            return text
            
        except Exception as e:
            print(f"Transcription error: {e}")
            raise
    
    def transcribe_with_timestamps(self, audio_path: str) -> dict:
        """Transcribe audio with word-level timestamps"""
        if not self.model:
            raise RuntimeError("Whisper model not loaded")
        
        try:
            # Transcribe with detailed output
            result = self.model.transcribe(
                audio_path,
                language="en",
                fp16=False,
                word_timestamps=True
            )
            
            return {
                "text": result["text"].strip(),
                "segments": result.get("segments", []),
                "language": result.get("language", "en")
            }
            
        except Exception as e:
            print(f"Transcription error: {e}")
            raise