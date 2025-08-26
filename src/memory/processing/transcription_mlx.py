"""MLX-based Whisper transcription for Apple Silicon GPUs"""

import os
import mlx_whisper
from typing import Optional, Dict
from pathlib import Path


class MLXWhisperTranscriber:
    """Transcribe audio using MLX Whisper (Apple GPU accelerated)"""
    
    # MLX model names map to Hugging Face paths
    MODEL_MAPPING = {
        "tiny": "mlx-community/whisper-tiny-mlx",
        "base": "mlx-community/whisper-base-mlx", 
        "small": "mlx-community/whisper-small-mlx",
        "medium": "mlx-community/whisper-medium-mlx",
        "large": "mlx-community/whisper-large-v3-mlx",
        "large-v3": "mlx-community/whisper-large-v3-mlx",
        "turbo": "mlx-community/whisper-large-v3-turbo-mlx"
    }
    
    def __init__(self, model_name: Optional[str] = None):
        """Initialize MLX Whisper transcriber"""
        self.model_name = model_name or os.getenv("WHISPER_MODEL", "base")
        self.mlx_model_path = self.MODEL_MAPPING.get(
            self.model_name, 
            f"mlx-community/whisper-{self.model_name}"
        )
        print(f"🚀 Using MLX Whisper on Apple GPU: {self.mlx_model_path}")
    
    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text using MLX"""
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            # MLX Whisper returns a dictionary with transcription results
            result = mlx_whisper.transcribe(
                audio_path,
                path_or_hf_repo=self.mlx_model_path,
                verbose=False,  # Suppress progress output
                fp16=True,  # Use float16 for efficiency
                language="en",  # Force English
            )
            
            # Extract text from result
            text = result.get("text", "").strip()
            return text
            
        except Exception as e:
            print(f"MLX transcription error: {e}")
            raise
    
    def transcribe_with_timestamps(self, audio_path: str) -> Dict:
        """Transcribe audio with word-level timestamps using MLX"""
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        try:
            # Transcribe with detailed output
            result = mlx_whisper.transcribe(
                audio_path,
                path_or_hf_repo=self.mlx_model_path,
                verbose=False,
                fp16=True,
                language="en",
                word_timestamps=True  # Enable word-level timestamps
            )
            
            return {
                "text": result.get("text", "").strip(),
                "segments": result.get("segments", []),
                "language": result.get("language", "en")
            }
            
        except Exception as e:
            print(f"MLX transcription error: {e}")
            raise