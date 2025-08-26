"""Unit tests for database operations"""

import pytest
import json
from datetime import datetime
from unittest.mock import patch
import sqlite3

from src.memory.storage import Database, Memory


class TestMemory:
    """Test Memory dataclass"""
    
    def test_memory_creation(self):
        """Test creating a memory instance"""
        memory = Memory(
            raw_text="Test memory",
            source="text",
            thought_type="idea"
        )
        assert memory.raw_text == "Test memory"
        assert memory.source == "text"
        assert memory.thought_type == "idea"
        assert memory.status == "pending"
    
    def test_memory_to_dict(self):
        """Test converting memory to dictionary"""
        memory = Memory(
            raw_text="Test memory",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            extracted_data={"key": "value"}
        )
        data = memory.to_dict()
        
        assert data['raw_text'] == "Test memory"
        assert data['timestamp'] == "2024-01-01T12:00:00"
        assert data['extracted_data'] == '{"key": "value"}'
    
    def test_memory_from_row(self):
        """Test creating memory from database row"""
        # Simulate a database row
        row_data = {
            'id': 1,
            'uuid': 'test-uuid',
            'raw_text': 'Test text',
            'source': 'voice',
            'thought_type': 'action',
            'summary': 'Test summary',
            'status': 'completed',
            'extracted_data': '{"actions": [{"text": "Test action"}]}',
            'timestamp': '2024-01-01T12:00:00',
            'processed_at': None,
            'created_at': '2024-01-01T11:00:00',
            'updated_at': '2024-01-01T12:00:00',
            'error_message': None
        }
        
        # Create a mock Row object
        class MockRow:
            def __init__(self, data):
                self._data = data
            
            def keys(self):
                return self._data.keys()
            
            def __getitem__(self, key):
                return self._data[key]
        
        memory = Memory.from_row(MockRow(row_data))
        
        assert memory.id == 1
        assert memory.uuid == 'test-uuid'
        assert memory.raw_text == 'Test text'
        assert memory.extracted_data == {"actions": [{"text": "Test action"}]}


class TestDatabase:
    """Test Database operations"""
    
    def test_database_initialization(self, in_memory_db):
        """Test database initializes with correct schema"""
        cursor = in_memory_db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        
        assert 'memories' in tables
        assert 'memories_fts' in tables
    
    def test_add_memory(self, in_memory_db, sample_memory):
        """Test adding a memory to database"""
        memory_id = in_memory_db.add_memory(sample_memory)
        
        assert memory_id is not None
        assert memory_id > 0
        
        # Verify memory was added
        cursor = in_memory_db.conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row['raw_text'] == sample_memory.raw_text
    
    def test_get_memory_by_uuid(self, in_memory_db, sample_memory):
        """Test retrieving memory by UUID"""
        memory_id = in_memory_db.add_memory(sample_memory)
        
        # Get the UUID that was generated
        cursor = in_memory_db.conn.execute(
            "SELECT uuid FROM memories WHERE id = ?", (memory_id,)
        )
        uuid = cursor.fetchone()['uuid']
        
        # Retrieve by UUID
        retrieved = in_memory_db.get_memory_by_uuid(uuid)
        
        assert retrieved is not None
        assert retrieved.raw_text == sample_memory.raw_text
        assert retrieved.uuid == uuid
    
    def test_update_memory(self, in_memory_db, sample_memory):
        """Test updating a memory"""
        memory_id = in_memory_db.add_memory(sample_memory)
        
        # Get the memory and update it
        cursor = in_memory_db.conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        )
        memory = Memory.from_row(cursor.fetchone())
        
        memory.summary = "Updated summary"
        memory.status = "completed"
        
        success = in_memory_db.update_memory(memory)
        assert success is True
        
        # Verify update
        updated = in_memory_db.get_memory_by_uuid(memory.uuid)
        assert updated.summary == "Updated summary"
        assert updated.status == "completed"
    
    def test_delete_memory(self, in_memory_db, sample_memory):
        """Test deleting a memory"""
        memory_id = in_memory_db.add_memory(sample_memory)
        
        success = in_memory_db.delete_memory(memory_id=memory_id)
        assert success is True
        
        # Verify deletion
        cursor = in_memory_db.conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        )
        assert cursor.fetchone() is None
    
    def test_get_recent_memories(self, in_memory_db, sample_memories):
        """Test getting recent memories"""
        # Add multiple memories with completed status
        for memory in sample_memories:
            memory.status = 'completed'  # Set status to completed
            in_memory_db.add_memory(memory)
        
        recent = in_memory_db.get_recent_memories(limit=2)
        
        assert len(recent) == 2
        # Should be ordered by timestamp DESC
        assert recent[0].raw_text == sample_memories[-1].raw_text
    
    def test_search_memories_with_special_chars(self, in_memory_db):
        """Test FTS search with special characters (apostrophes, quotes)"""
        # Add memory with special characters
        memory = Memory(
            raw_text="It's important to handle \"special\" characters & symbols!",
            summary="Testing special chars: don't break!"
        )
        in_memory_db.add_memory(memory)
        
        # Search should handle special characters without crashing
        results = in_memory_db.search_memories("It's")
        assert len(results) > 0
        
        results = in_memory_db.search_memories('"special"')
        assert len(results) > 0
    
    def test_get_tasks(self, in_memory_db):
        """Test getting task memories"""
        # Add action memory
        action_memory = Memory(
            raw_text="Buy groceries",
            thought_type="action",
            status="completed",
            extracted_data={'actions': [{'text': 'Buy groceries'}]}
        )
        in_memory_db.add_memory(action_memory)
        
        # Add non-action memory
        idea_memory = Memory(
            raw_text="What if we tried X?",
            thought_type="idea",
            status="completed"
        )
        in_memory_db.add_memory(idea_memory)
        
        tasks = in_memory_db.get_tasks()
        
        assert len(tasks) == 1
        assert tasks[0].thought_type == "action"
    
    def test_get_pending_memories(self, in_memory_db):
        """Test getting pending memories"""
        # Add pending memory
        pending = Memory(raw_text="Pending", status="pending")
        in_memory_db.add_memory(pending)
        
        # Add completed memory
        completed = Memory(raw_text="Completed", status="completed")
        in_memory_db.add_memory(completed)
        
        pending_memories = in_memory_db.get_pending_memories(limit=10)
        
        assert len(pending_memories) == 1
        assert pending_memories[0].status == "pending"
    
    def test_concurrent_access(self, test_db):
        """Test database handles concurrent access properly"""
        import threading
        import time
        
        results = []
        
        def add_memory(thread_id):
            try:
                memory = Memory(raw_text=f"Memory from thread {thread_id}")
                memory_id = test_db.add_memory(memory)
                results.append((thread_id, memory_id, None))
            except Exception as e:
                results.append((thread_id, None, str(e)))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=add_memory, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Check results
        assert len(results) == 5
        successful = [r for r in results if r[1] is not None]
        # With proper locking and retries, most should succeed
        # At least 3 out of 5 should succeed even under contention
        assert len(successful) >= 3
        
        # Verify the successful ones are actually in the database
        for thread_id, memory_id, error in successful:
            cursor = test_db.conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            )
            assert cursor.fetchone() is not None
    
    def test_fts_manual_update(self, in_memory_db):
        """Test that FTS is manually updated correctly"""
        memory = Memory(raw_text="Original text")
        memory_id = in_memory_db.add_memory(memory)
        
        # Get the UUID
        cursor = in_memory_db.conn.execute(
            "SELECT uuid FROM memories WHERE id = ?", (memory_id,)
        )
        uuid = cursor.fetchone()['uuid']
        
        # Check FTS has the original text
        cursor = in_memory_db.conn.execute(
            "SELECT raw_text FROM memories_fts WHERE uuid = ?", (uuid,)
        )
        fts_text = cursor.fetchone()['raw_text']
        assert fts_text == "Original text"
        
        # Update the memory
        memory = in_memory_db.get_memory_by_uuid(uuid)
        memory.raw_text = "Updated text"
        in_memory_db.update_memory(memory)
        
        # Check FTS was updated
        cursor = in_memory_db.conn.execute(
            "SELECT raw_text FROM memories_fts WHERE uuid = ?", (uuid,)
        )
        fts_text = cursor.fetchone()['raw_text']
        assert fts_text == "Updated text"