"""ChromaDB vector store for semantic search"""

import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional, Any
from datetime import datetime
import json


class VectorStore:
    """Manage vector storage with ChromaDB"""
    
    def __init__(self, persist_directory: Optional[str] = None):
        """Initialize ChromaDB vector store
        
        Args:
            persist_directory: Directory to persist ChromaDB data
        """
        # Use the same directory structure as SQLite database
        if persist_directory is None:
            persist_directory = os.path.expanduser("~/.memory/chroma")
        
        # Ensure directory exists
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,  # Disable telemetry
                allow_reset=True,
            )
        )
        
        # Get or create collection for memories
        self.collection = self.client.get_or_create_collection(
            name="memories",
            metadata={"description": "Second Brain memory embeddings"}
        )
        
        print(f"📊 Vector store initialized at: {persist_directory}")
    
    def add_memory(self, memory_id: str, embedding: List[float], 
                   metadata: Optional[Dict[str, Any]] = None, 
                   document: Optional[str] = None):
        """Add a memory embedding to the vector store
        
        Args:
            memory_id: Unique identifier for the memory
            embedding: Embedding vector
            metadata: Additional metadata to store
            document: Text content of the memory
        """
        # Ensure metadata is JSON-serializable
        if metadata:
            # Convert datetime objects to strings
            clean_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, datetime):
                    clean_metadata[key] = value.isoformat()
                elif isinstance(value, (str, int, float, bool, type(None))):
                    clean_metadata[key] = value
                else:
                    # Convert complex types to JSON string
                    clean_metadata[key] = json.dumps(value)
        else:
            clean_metadata = {}
        
        # Add to collection
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            metadatas=[clean_metadata] if clean_metadata else None,
            documents=[document] if document else None
        )
    
    def search(self, query_embedding: List[float], 
               limit: int = 10,
               where: Optional[Dict] = None) -> List[Dict]:
        """Search for similar memories
        
        Args:
            query_embedding: Query embedding vector
            limit: Number of results to return
            where: Optional filter conditions
            
        Returns:
            List of search results with id, score, metadata
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where
        )
        
        # Format results
        formatted_results = []
        if results['ids'] and len(results['ids']) > 0:
            ids = results['ids'][0]
            distances = results['distances'][0] if results['distances'] else []
            metadatas = results['metadatas'][0] if results['metadatas'] else []
            documents = results['documents'][0] if results['documents'] else []
            
            for i in range(len(ids)):
                # ChromaDB returns L2 distances
                distance = distances[i] if i < len(distances) else 0
                
                # Convert L2 distance to cosine similarity approximation
                # For normalized vectors, we can use: similarity = 1 - (distance^2 / 4)
                # But our vectors may not be normalized, so we'll use exponential decay
                # with a scaling factor appropriate for 768-dim embeddings
                
                # Typical distances for 768-dim vectors range from ~300-600
                # We'll use exp decay with appropriate scaling
                import math
                similarity = math.exp(-distance / 200.0)  # Scale factor of 200 works well for these distances
                
                result = {
                    'id': ids[i],
                    'score': similarity,
                    'metadata': metadatas[i] if i < len(metadatas) else {},
                    'document': documents[i] if i < len(documents) else None
                }
                formatted_results.append(result)
        
        return formatted_results
    
    def update_memory(self, memory_id: str, embedding: Optional[List[float]] = None,
                     metadata: Optional[Dict[str, Any]] = None,
                     document: Optional[str] = None):
        """Update an existing memory in the vector store
        
        Args:
            memory_id: ID of memory to update
            embedding: New embedding vector (optional)
            metadata: New metadata (optional)
            document: New document text (optional)
        """
        update_args = {'ids': [memory_id]}
        
        if embedding is not None:
            update_args['embeddings'] = [embedding]
        
        if metadata is not None:
            # Clean metadata
            clean_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, datetime):
                    clean_metadata[key] = value.isoformat()
                elif isinstance(value, (str, int, float, bool, type(None))):
                    clean_metadata[key] = value
                else:
                    clean_metadata[key] = json.dumps(value)
            update_args['metadatas'] = [clean_metadata]
        
        if document is not None:
            update_args['documents'] = [document]
        
        self.collection.update(**update_args)
    
    def delete_memory(self, memory_id: str):
        """Delete a memory from the vector store
        
        Args:
            memory_id: ID of memory to delete
        """
        self.collection.delete(ids=[memory_id])
    
    def get_memory(self, memory_id: str) -> Optional[Dict]:
        """Get a specific memory by ID
        
        Args:
            memory_id: ID of memory to retrieve
            
        Returns:
            Memory data or None if not found
        """
        try:
            result = self.collection.get(ids=[memory_id])
            if result['ids'] and len(result['ids']) > 0:
                return {
                    'id': result['ids'][0],
                    'metadata': result['metadatas'][0] if result['metadatas'] else {},
                    'document': result['documents'][0] if result['documents'] else None,
                    'embedding': result['embeddings'][0] if result.get('embeddings') else None
                }
        except Exception:
            pass
        return None
    
    def count(self) -> int:
        """Get total number of memories in vector store
        
        Returns:
            Number of memories
        """
        return self.collection.count()
    
    def reset(self):
        """Clear all memories from the vector store (use with caution!)"""
        self.client.delete_collection("memories")
        self.collection = self.client.create_collection(
            name="memories",
            metadata={"description": "Second Brain memory embeddings"}
        )