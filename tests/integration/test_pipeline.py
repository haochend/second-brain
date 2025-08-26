"""Integration tests for end-to-end processing pipeline"""

import pytest
import json
import time
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.memory.storage import Database, Memory
from src.memory.capture import Queue, TextCapture
from src.memory.processing import MemoryProcessor
from src.memory.query import MemorySearch, SemanticSearch


@pytest.mark.integration
class TestProcessingPipeline:
    """Test complete processing pipeline"""
    
    def test_text_capture_to_storage(self, test_db, test_queue, mock_ollama):
        """Test full pipeline from text capture to storage"""
        # Initialize capture
        capture = TextCapture(queue=test_queue, db=test_db)
        
        # Capture text
        text = "Remember to review the API design with Sarah tomorrow"
        item_id = capture.capture(text)
        
        assert item_id is not None
        
        # Check queue has the item
        item = test_queue.get_item(item_id)
        assert item is not None
        assert item['content'] == text
        
        # Check database has pending memory
        pending = test_db.get_pending_memories(1)
        assert len(pending) == 1
        assert pending[0].status == "pending"
    
    @patch('src.memory.embeddings.generator.ollama')
    @patch('src.memory.processing.extraction.ollama')
    def test_processing_text_memory(self, mock_extraction, mock_embedding, 
                                   test_db, test_queue, test_vector_store):
        """Test processing a text memory through the pipeline"""
        # Setup mocks
        mock_extraction.chat.return_value = {
            'message': {
                'content': json.dumps({
                    'thought_type': 'action',
                    'summary': 'Review API design with Sarah',
                    'actions': [
                        {'text': 'Review API design', 'priority': 'high'}
                    ],
                    'people': ['Sarah'],
                    'topics': ['API', 'design']
                })
            }
        }
        
        mock_embedding.embeddings.return_value = {
            'embedding': [0.1] * 768
        }
        
        # Add mock list response
        mock_list = MagicMock()
        mock_list.models = [MagicMock(name='nomic-embed-text')]
        mock_embedding.list.return_value = mock_list
        
        # Create processor with mocked dependencies
        from src.memory.processing import LLMExtractor
        from src.memory.embeddings import EmbeddingGenerator
        
        processor = MemoryProcessor(
            queue=test_queue,
            db=test_db,
            extractor=LLMExtractor(),
            embedding_generator=EmbeddingGenerator(),
            vector_store=test_vector_store
        )
        
        # Add item to queue
        text = "Review API design with Sarah tomorrow"
        memory = Memory(raw_text=text, status="pending")
        memory_id = test_db.add_memory(memory)
        
        # Get the UUID for queue item
        cursor = test_db.conn.execute(
            "SELECT uuid FROM memories WHERE id = ?", (memory_id,)
        )
        memory_uuid = cursor.fetchone()['uuid']
        
        # Add to queue
        item_id = test_queue.add(
            item_type="text",
            content=text,
            metadata={"memory_uuid": memory_uuid}
        )
        
        # Process the batch
        stats = processor.process_batch(limit=1)
        
        assert stats['processed'] == 1
        assert stats['failed'] == 0
        
        # Check memory was updated
        updated = test_db.get_memory_by_uuid(memory_uuid)
        assert updated.status == "completed"
        assert updated.thought_type == "action"
        assert updated.summary == "Review API design with Sarah"
        assert "Sarah" in updated.extracted_data['people']
        
        # Check embedding was stored
        assert test_vector_store.count() == 1
        vector_memory = test_vector_store.get_memory(memory_uuid)
        assert vector_memory is not None
    
    @patch('src.memory.processing.transcription_mlx.mlx_whisper')
    @patch('src.memory.embeddings.generator.ollama')
    @patch('src.memory.processing.extraction.ollama')
    def test_voice_processing_pipeline(self, mock_extraction, mock_embedding, 
                                      mock_whisper, test_db, test_queue, 
                                      test_vector_store, sample_audio_file):
        """Test processing voice memory through pipeline"""
        # Setup mocks
        mock_whisper.transcribe.return_value = {
            'text': 'Remember to buy groceries tomorrow'
        }
        
        mock_extraction.chat.return_value = {
            'message': {
                'content': json.dumps({
                    'thought_type': 'action',
                    'summary': 'Buy groceries',
                    'actions': [
                        {'text': 'Buy groceries', 'priority': 'medium'}
                    ],
                    'temporal': {'tomorrow': True}
                })
            }
        }
        
        mock_embedding.embeddings.return_value = {
            'embedding': [0.2] * 768
        }
        
        mock_list = MagicMock()
        mock_list.models = [MagicMock(name='nomic-embed-text')]
        mock_embedding.list.return_value = mock_list
        
        # Create memory and queue item
        memory_uuid = "voice-test-uuid"
        memory = Memory(
            uuid=memory_uuid,
            raw_text="[Voice recording - pending transcription]",
            source="voice",
            status="pending"
        )
        test_db.add_memory(memory)
        
        # Add voice item to queue
        item_id = test_queue.add(
            item_type="voice",
            content="",
            metadata={
                "audio_path": str(sample_audio_file),
                "memory_uuid": memory_uuid
            }
        )
        
        # Process with mocked transcription
        from src.memory.processing import LLMExtractor
        from src.memory.processing.transcription_mlx import MLXWhisperTranscriber
        from src.memory.embeddings import EmbeddingGenerator
        
        processor = MemoryProcessor(
            queue=test_queue,
            db=test_db,
            extractor=LLMExtractor(),
            transcriber=MLXWhisperTranscriber(),
            embedding_generator=EmbeddingGenerator(),
            vector_store=test_vector_store
        )
        
        stats = processor.process_batch(limit=1)
        
        assert stats['processed'] == 1
        
        # Check memory was transcribed and updated
        updated = test_db.get_memory_by_uuid(memory_uuid)
        assert updated.raw_text == "Remember to buy groceries tomorrow"
        assert updated.source == "voice"
        assert updated.thought_type == "action"
        assert updated.status == "completed"
    
    def test_search_after_processing(self, test_db, test_vector_store, mock_embedding_generator):
        """Test that search works after processing"""
        # Add processed memories to database
        memories = [
            Memory(
                uuid="mem1",
                raw_text="Buy groceries from the store",
                thought_type="action",
                summary="Buy groceries",
                status="completed",
                extracted_data={'actions': [{'text': 'Buy groceries'}]}
            ),
            Memory(
                uuid="mem2",
                raw_text="Review code with the team",
                thought_type="action", 
                summary="Code review",
                status="completed",
                extracted_data={'actions': [{'text': 'Review code'}]}
            ),
            Memory(
                uuid="mem3",
                raw_text="Interesting idea about caching",
                thought_type="idea",
                summary="Caching idea",
                status="completed",
                extracted_data={'ideas': ['Use Redis for caching']}
            )
        ]
        
        for memory in memories:
            test_db.add_memory(memory)
            # Add to vector store
            test_vector_store.add_memory(
                memory_id=memory.uuid,
                embedding=[0.1] * 768,
                metadata={'thought_type': memory.thought_type},
                document=memory.raw_text
            )
        
        # Test keyword search
        search = MemorySearch(db=test_db)
        results = search.search("groceries")
        assert len(results) > 0
        assert "groceries" in results[0].raw_text.lower()
        
        # Test semantic search
        semantic = SemanticSearch(
            db=test_db,
            embedding_generator=mock_embedding_generator,
            vector_store=test_vector_store
        )
        
        results = semantic.search("shopping tasks", limit=2)
        assert len(results) <= 2
    
    def test_error_recovery(self, test_db, test_queue):
        """Test that pipeline handles errors gracefully"""
        # Add item with invalid data
        memory = Memory(raw_text="Test", status="pending")
        memory_id = test_db.add_memory(memory)
        
        cursor = test_db.conn.execute(
            "SELECT uuid FROM memories WHERE id = ?", (memory_id,)
        )
        memory_uuid = cursor.fetchone()['uuid']
        
        item_id = test_queue.add(
            item_type="invalid_type",  # Invalid type
            content="Test",
            metadata={"memory_uuid": memory_uuid}
        )
        
        # Create processor (will use real dependencies, but should handle error)
        from src.memory.processing import LLMExtractor
        processor = MemoryProcessor(
            queue=test_queue,
            db=test_db,
            extractor=LLMExtractor()
        )
        
        # Process should handle the error
        stats = processor.process_batch(limit=1)
        
        assert stats['skipped'] == 1 or stats['failed'] == 1
        
        # Item should be in failed state
        item = test_queue.get_item(item_id)
        assert item['status'] == 'failed' or item['status'] == 'pending'