"""Unit tests for embeddings and vector store"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.memory.embeddings import EmbeddingGenerator, VectorStore


class TestEmbeddingGenerator:
    """Test embedding generation"""
    
    @patch('src.memory.embeddings.generator.ollama')
    def test_generate_embedding(self, mock_ollama):
        """Test generating single embedding"""
        # Mock the embeddings response
        mock_ollama.embeddings.return_value = {
            'embedding': [0.1, 0.2, 0.3] * 256  # 768 dimensions
        }
        
        # Mock list response for model check
        mock_list = MagicMock()
        mock_list.models = [MagicMock(name='nomic-embed-text')]
        mock_ollama.list.return_value = mock_list
        
        generator = EmbeddingGenerator()
        embedding = generator.generate("Test text")
        
        assert len(embedding) == 768
        assert embedding[0] == 0.1
        assert embedding[1] == 0.2
        
        # Check ollama was called correctly
        mock_ollama.embeddings.assert_called_once_with(
            model='nomic-embed-text',
            prompt="Test text"
        )
    
    @patch('src.memory.embeddings.generator.ollama')
    def test_generate_batch_embeddings(self, mock_ollama):
        """Test generating batch embeddings"""
        # Mock responses for multiple texts
        mock_ollama.embeddings.side_effect = [
            {'embedding': [0.1] * 768},
            {'embedding': [0.2] * 768},
            {'embedding': [0.3] * 768}
        ]
        
        # Mock list response
        mock_list = MagicMock()
        mock_list.models = [MagicMock(name='nomic-embed-text')]
        mock_ollama.list.return_value = mock_list
        
        generator = EmbeddingGenerator()
        embeddings = generator.generate_batch(["Text 1", "Text 2", "Text 3"])
        
        assert len(embeddings) == 3
        assert embeddings[0][0] == 0.1
        assert embeddings[1][0] == 0.2
        assert embeddings[2][0] == 0.3
    
    @patch('src.memory.embeddings.generator.ollama')
    def test_embedding_error_handling(self, mock_ollama):
        """Test handling of embedding generation errors"""
        # Mock an error
        mock_ollama.embeddings.side_effect = Exception("API error")
        
        # Mock list response
        mock_list = MagicMock()
        mock_list.models = [MagicMock(name='nomic-embed-text')]
        mock_ollama.list.return_value = mock_list
        
        generator = EmbeddingGenerator()
        embedding = generator.generate("Test text")
        
        # Should return zero vector as fallback
        assert len(embedding) == 768
        assert all(x == 0.0 for x in embedding)


class TestVectorStore:
    """Test vector store operations"""
    
    def test_vector_store_initialization(self, test_vector_store):
        """Test vector store creates collection"""
        assert test_vector_store.collection is not None
        assert test_vector_store.collection.name == "memories"
        assert test_vector_store.count() == 0
    
    def test_add_memory_to_vector_store(self, test_vector_store):
        """Test adding memory with embedding"""
        memory_id = "test-uuid-123"
        embedding = [0.1] * 768
        metadata = {
            "thought_type": "action",
            "source": "text",
            "timestamp": datetime.now()
        }
        document = "Test memory content"
        
        test_vector_store.add_memory(
            memory_id=memory_id,
            embedding=embedding,
            metadata=metadata,
            document=document
        )
        
        assert test_vector_store.count() == 1
        
        # Retrieve and verify
        result = test_vector_store.get_memory(memory_id)
        assert result is not None
        assert result['id'] == memory_id
        assert result['document'] == document
    
    def test_search_vector_store(self, test_vector_store):
        """Test searching for similar vectors"""
        # Add multiple memories
        test_vector_store.add_memory(
            memory_id="mem1",
            embedding=[0.1] * 768,
            metadata={"thought_type": "action"},
            document="Buy groceries"
        )
        
        test_vector_store.add_memory(
            memory_id="mem2", 
            embedding=[0.2] * 768,
            metadata={"thought_type": "idea"},
            document="New feature idea"
        )
        
        test_vector_store.add_memory(
            memory_id="mem3",
            embedding=[0.15] * 768,  # Similar to mem1
            metadata={"thought_type": "action"},
            document="Buy coffee"
        )
        
        # Search with query embedding similar to mem1
        results = test_vector_store.search(
            query_embedding=[0.12] * 768,
            limit=2
        )
        
        assert len(results) == 2
        # First result should be most similar (mem1 or mem3)
        assert results[0]['id'] in ['mem1', 'mem3']
        assert 'score' in results[0]
    
    def test_search_with_filters(self, test_vector_store):
        """Test searching with metadata filters"""
        # Add memories with different types
        test_vector_store.add_memory(
            memory_id="action1",
            embedding=[0.1] * 768,
            metadata={"thought_type": "action", "priority": "high"},
            document="Important task"
        )
        
        test_vector_store.add_memory(
            memory_id="idea1",
            embedding=[0.1] * 768,
            metadata={"thought_type": "idea", "priority": "low"},
            document="Random idea"
        )
        
        test_vector_store.add_memory(
            memory_id="action2",
            embedding=[0.1] * 768,
            metadata={"thought_type": "action", "priority": "medium"},
            document="Regular task"
        )
        
        # Search only for actions
        results = test_vector_store.search(
            query_embedding=[0.1] * 768,
            limit=10,
            where={"thought_type": "action"}
        )
        
        assert len(results) == 2
        assert all(r['id'].startswith('action') for r in results)
    
    def test_update_memory(self, test_vector_store):
        """Test updating a memory in vector store"""
        memory_id = "test-memory"
        
        # Add initial memory
        test_vector_store.add_memory(
            memory_id=memory_id,
            embedding=[0.1] * 768,
            metadata={"thought_type": "idea"},
            document="Original content"
        )
        
        # Update memory
        test_vector_store.update_memory(
            memory_id=memory_id,
            embedding=[0.2] * 768,
            metadata={"thought_type": "action"},
            document="Updated content"
        )
        
        # Retrieve and verify
        result = test_vector_store.get_memory(memory_id)
        assert result['document'] == "Updated content"
        assert result['metadata']['thought_type'] == "action"
    
    def test_delete_memory(self, test_vector_store):
        """Test deleting a memory from vector store"""
        memory_id = "test-memory"
        
        # Add memory
        test_vector_store.add_memory(
            memory_id=memory_id,
            embedding=[0.1] * 768,
            document="Test content"
        )
        
        assert test_vector_store.count() == 1
        
        # Delete memory
        test_vector_store.delete_memory(memory_id)
        
        assert test_vector_store.count() == 0
        assert test_vector_store.get_memory(memory_id) is None
    
    def test_metadata_datetime_handling(self, test_vector_store):
        """Test that datetime objects are properly converted"""
        memory_id = "test-datetime"
        now = datetime.now()
        
        metadata = {
            "thought_type": "action",
            "timestamp": now,
            "processed": True,
            "score": 0.95
        }
        
        test_vector_store.add_memory(
            memory_id=memory_id,
            embedding=[0.1] * 768,
            metadata=metadata,
            document="Test"
        )
        
        # Retrieve and check datetime was converted to string
        result = test_vector_store.get_memory(memory_id)
        assert isinstance(result['metadata']['timestamp'], str)
        assert now.isoformat() == result['metadata']['timestamp']
    
    def test_reset_vector_store(self, test_vector_store):
        """Test resetting the vector store"""
        # Add some memories
        for i in range(3):
            test_vector_store.add_memory(
                memory_id=f"mem{i}",
                embedding=[float(i)] * 768,
                document=f"Memory {i}"
            )
        
        assert test_vector_store.count() == 3
        
        # Reset
        test_vector_store.reset()
        
        assert test_vector_store.count() == 0
    
    def test_similarity_scoring(self, test_vector_store):
        """Test that similarity scores are calculated correctly"""
        # Add memories with different embeddings
        test_vector_store.add_memory(
            memory_id="exact",
            embedding=[0.5] * 768,
            document="Exact match"
        )
        
        test_vector_store.add_memory(
            memory_id="similar",
            embedding=[0.48] * 768,
            document="Similar"
        )
        
        test_vector_store.add_memory(
            memory_id="different", 
            embedding=[0.1] * 768,
            document="Very different"
        )
        
        # Search with exact embedding
        results = test_vector_store.search(
            query_embedding=[0.5] * 768,
            limit=3
        )
        
        assert len(results) == 3
        # Exact match should have highest score
        assert results[0]['id'] == "exact"
        assert results[0]['score'] > results[1]['score']
        assert results[1]['score'] > results[2]['score']