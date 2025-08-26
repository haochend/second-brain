"""Generate embeddings using Ollama"""

import os
import ollama
from typing import List, Optional


class EmbeddingGenerator:
    """Generate embeddings using Ollama models"""
    
    def __init__(self, model_name: Optional[str] = None):
        """Initialize embedding generator
        
        Args:
            model_name: Ollama model to use for embeddings (default: nomic-embed-text)
        """
        # Use nomic-embed-text as it's optimized for embeddings
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
        self._ensure_model()
    
    def _ensure_model(self):
        """Ensure the embedding model is available"""
        try:
            # Check if model exists
            response = ollama.list()
            if hasattr(response, 'models'):
                models = response.models
            else:
                models = response.get('models', [])
            
            model_names = [m.get('name', '') if isinstance(m, dict) else getattr(m, 'name', '') 
                          for m in models]
            
            if not any(self.model_name in name for name in model_names):
                print(f"📥 Pulling embedding model: {self.model_name}")
                ollama.pull(self.model_name)
                print(f"✅ Model {self.model_name} ready")
        except Exception as e:
            print(f"⚠️  Could not verify embedding model: {e}")
    
    def generate(self, text: str) -> List[float]:
        """Generate embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            response = ollama.embeddings(
                model=self.model_name,
                prompt=text
            )
            return response['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 768  # nomic-embed-text uses 768 dimensions
    
    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            embedding = self.generate(text)
            embeddings.append(embedding)
        return embeddings