"""Transcription module using Whisper"""

import whisper
import torch
import os
from typing import Optional
from pathlib import Path


class WhisperTranscriber:
    """Transcribe audio using OpenAI Whisper"""
    
    # Class-level model cache to avoid reloading
    _model_cache = {}
    
    def __init__(self, model_name: Optional[str] = None):
        """Initialize Whisper transcriber"""
        self.model_name = model_name or os.getenv("WHISPER_MODEL", "base")
        self.model = None
        self._determine_device()
        self._load_model()
    
    def _determine_device(self):
        """Determine best available device"""
        if torch.cuda.is_available():
            self.device = "cuda"
            print("🚀 Using CUDA GPU acceleration")
        else:
            # MPS has compatibility issues with Whisper, use CPU
            self.device = "cpu"
            if torch.backends.mps.is_available():
                print("💻 Using CPU (MPS available but not compatible with Whisper)")
            else:
                print("💻 Using CPU")
    
    def _load_model(self):
        """Load Whisper model with caching"""
        cache_key = f"{self.model_name}_{self.device}"
        
        # Check cache first
        if cache_key in self._model_cache:
            self.model = self._model_cache[cache_key]
            print(f"✅ Whisper {self.model_name} loaded from cache (instant)")
            return
        
        # Load new model
        print(f"Loading Whisper model: {self.model_name} (first time, ~5 seconds)")
        try:
            import time
            start = time.time()
            self.model = whisper.load_model(self.model_name, device=self.device)
            elapsed = time.time() - start
            
            # Cache the model
            self._model_cache[cache_key] = self.model
            print(f"✅ Whisper {self.model_name} loaded in {elapsed:.1f}s and cached")
        except Exception as e:
            print(f"⚠️  Error loading Whisper model: {e}")
            print("Falling back to 'base' model on CPU")
            self.device = "cpu"
            self.model = whisper.load_model("base", device=self.device)
            self._model_cache[f"base_{self.device}"] = self.model
    
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