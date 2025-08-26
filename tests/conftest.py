"""Shared test fixtures and configuration"""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.memory.storage import Database, Memory
from src.memory.capture import Queue
from src.memory.embeddings import VectorStore, EmbeddingGenerator
from src.memory.processing import MemoryProcessor, LLMExtractor


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_dir = tempfile.mkdtemp(prefix="memory_test_")
    yield Path(temp_dir)
    # Cleanup after test
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_db(temp_dir):
    """Create an isolated test database"""
    db_path = temp_dir / "test_memories.db"
    db = Database(db_path=str(db_path))
    yield db
    # Close connection after test
    if db.conn:
        db.conn.close()


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for fast unit tests"""
    db = Database(db_path=":memory:")
    yield db
    if db.conn:
        db.conn.close()


@pytest.fixture
def test_queue(temp_dir):
    """Create an isolated test queue"""
    queue_dir = temp_dir / "test_queue"
    queue = Queue(queue_dir=str(queue_dir))
    yield queue


@pytest.fixture
def test_vector_store(temp_dir):
    """Create an isolated vector store"""
    chroma_dir = temp_dir / "test_chroma"
    vector_store = VectorStore(persist_directory=str(chroma_dir))
    yield vector_store


@pytest.fixture
def mock_embedding_generator():
    """Mock embedding generator to avoid loading models"""
    with patch('src.memory.embeddings.generator.EmbeddingGenerator') as mock_class:
        mock_instance = Mock(spec=EmbeddingGenerator)
        # Return consistent 768-dim embeddings for testing
        mock_instance.generate.return_value = [0.1] * 768
        mock_instance.generate_batch.return_value = [[0.1] * 768, [0.2] * 768]
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_ollama():
    """Mock Ollama API calls"""
    with patch('src.memory.processing.extraction.ollama') as mock_ollama:
        # Mock chat response for extraction
        mock_ollama.chat.return_value = {
            'message': {
                'content': json.dumps({
                    'thought_type': 'action',
                    'summary': 'Test summary',
                    'actions': [
                        {'text': 'Test action', 'priority': 'medium'}
                    ],
                    'people': ['Alice'],
                    'topics': ['testing'],
                    'questions': [],
                    'ideas': [],
                    'decisions': [],
                    'mood': 'neutral',
                    'temporal': {}
                })
            }
        }
        
        # Mock embeddings response
        mock_ollama.embeddings.return_value = {
            'embedding': [0.1] * 768
        }
        
        # Mock list response
        mock_list_response = MagicMock()
        mock_list_response.models = [
            MagicMock(name='gpt-oss:120b'),
            MagicMock(name='nomic-embed-text')
        ]
        mock_ollama.list.return_value = mock_list_response
        
        yield mock_ollama


@pytest.fixture
def mock_mlx_whisper():
    """Mock MLX Whisper transcription"""
    with patch('src.memory.processing.transcription_mlx.mlx_whisper') as mock_mlx:
        mock_mlx.transcribe.return_value = {
            'text': 'This is a test transcription',
            'segments': [],
            'language': 'en'
        }
        yield mock_mlx


@pytest.fixture
def sample_memory():
    """Create a sample memory for testing"""
    return Memory(
        raw_text="Remember to review the API design with Sarah tomorrow at 2pm",
        source="text",
        thought_type="action",
        summary="Review API design with Sarah",
        extracted_data={
            'thought_type': 'action',
            'summary': 'Review API design with Sarah',
            'actions': [
                {'text': 'Review API design with Sarah', 'priority': 'high'}
            ],
            'people': ['Sarah'],
            'topics': ['API', 'design'],
            'temporal': {'tomorrow': '2pm'}
        }
    )


@pytest.fixture
def sample_memories():
    """Create multiple sample memories for testing"""
    from datetime import datetime, timedelta
    base_time = datetime.now()
    
    return [
        Memory(
            raw_text="Remember to buy groceries: milk, eggs, bread",
            source="text",
            thought_type="action",
            summary="Buy groceries",
            timestamp=base_time - timedelta(hours=2),  # Oldest
            extracted_data={
                'thought_type': 'action',
                'actions': [{'text': 'Buy groceries', 'priority': 'medium'}],
                'topics': ['groceries']
            }
        ),
        Memory(
            raw_text="The authentication system should use OAuth2 and JWT tokens",
            source="text", 
            thought_type="decision",
            summary="Use OAuth2 and JWT for authentication",
            timestamp=base_time - timedelta(hours=1),  # Middle
            extracted_data={
                'thought_type': 'decision',
                'decisions': ['Use OAuth2 and JWT'],
                'topics': ['authentication', 'security']
            }
        ),
        Memory(
            raw_text="What if we used a vector database for semantic search?",
            source="text",
            thought_type="idea",
            summary="Use vector database for semantic search",
            timestamp=base_time,  # Most recent
            extracted_data={
                'thought_type': 'idea',
                'ideas': ['Use vector database for semantic search'],
                'topics': ['search', 'database']
            }
        )
    ]


@pytest.fixture
def sample_audio_file(temp_dir):
    """Create a dummy audio file for testing"""
    import wave
    import struct
    
    audio_path = temp_dir / "test_audio.wav"
    
    # Create a simple WAV file
    sample_rate = 16000
    duration = 1  # 1 second
    frequency = 440  # A4 note
    
    with wave.open(str(audio_path), 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample
        wav_file.setframerate(sample_rate)
        
        # Generate sine wave
        for i in range(sample_rate * duration):
            value = int(32767 * 0.5 * (1 + (i % 100) / 100))  # Simple pattern
            data = struct.pack('<h', value)
            wav_file.writeframesraw(data)
    
    return audio_path


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables for each test"""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def isolated_processor(test_db, test_queue, test_vector_store, mock_ollama, mock_mlx_whisper, mock_embedding_generator):
    """Create a processor with all mocked dependencies"""
    processor = MemoryProcessor(
        queue=test_queue,
        db=test_db,
        extractor=LLMExtractor(),
        embedding_generator=mock_embedding_generator,
        vector_store=test_vector_store
    )
    return processor