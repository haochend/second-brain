"""Tests for database corruption and recovery scenarios"""

import pytest
import sqlite3
import json
from pathlib import Path

from src.memory.storage import Database, Memory
from tests.fixtures.data import TestDataGenerator


class TestDatabaseCorruption:
    """Test database corruption scenarios and recovery"""
    
    def test_special_characters_in_fts(self, test_db):
        """Test that special characters don't corrupt FTS"""
        # These previously caused "database disk image is malformed" errors
        problematic_texts = [
            "It's important to test apostrophes",
            "Testing \"quotes\" in text",
            "Mix of 'single' and \"double\" quotes",
            "Special chars: & < > $ % @ # !",
            "'; DROP TABLE memories; --",  # SQL injection attempt
            "Test with\nnewlines\nand\ttabs",
            "Unicode: café, naïve, 日本語, 中文, 한글",
            "Emojis: 🚀 🎉 👍 ❤️"
        ]
        
        for text in problematic_texts:
            memory = Memory(raw_text=text, summary=f"Testing: {text[:20]}")
            memory_id = test_db.add_memory(memory)
            assert memory_id is not None
        
        # Try searching for these texts
        for text in problematic_texts:
            # Search for a safe portion of the text
            search_term = text.split()[0] if text.split() else text[:5]
            try:
                results = test_db.search_memories(search_term)
                # We don't care if results are empty, just that it doesn't crash
            except sqlite3.DatabaseError as e:
                pytest.fail(f"FTS search failed with: {e}")
    
    def test_fts_sync_after_deletion(self, test_db):
        """Test that FTS stays in sync after deletions"""
        # Add memories
        memories = []
        for i in range(5):
            memory = Memory(raw_text=f"Memory {i}")
            memory_id = test_db.add_memory(memory)
            memories.append((memory_id, memory))
        
        # Delete middle memory
        test_db.delete_memory(memory_id=memories[2][0])
        
        # Search should not crash
        results = test_db.search_memories("Memory")
        assert len(results) == 4
        
        # Verify FTS is in sync
        cursor = test_db.conn.execute("SELECT COUNT(*) FROM memories")
        main_count = cursor.fetchone()[0]
        
        cursor = test_db.conn.execute("SELECT COUNT(*) FROM memories_fts")
        fts_count = cursor.fetchone()[0]
        
        assert main_count == fts_count == 4
    
    def test_concurrent_writes_dont_corrupt(self, test_db):
        """Test that concurrent writes don't corrupt database"""
        import threading
        import time
        
        errors = []
        success_count = [0]
        
        def write_memories(thread_id):
            for i in range(10):
                try:
                    memory = Memory(
                        raw_text=f"Thread {thread_id} memory {i}",
                        summary=f"T{thread_id}M{i}"
                    )
                    test_db.add_memory(memory)
                    success_count[0] += 1
                    time.sleep(0.001)  # Small delay to increase contention
                except Exception as e:
                    errors.append((thread_id, i, str(e)))
        
        # Start multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=write_memories, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert success_count[0] == 50
        
        # Verify database integrity
        cursor = test_db.conn.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        assert result == "ok"
    
    def test_recovery_from_locked_database(self, test_db):
        """Test recovery from database lock scenarios"""
        # Simulate a long-running transaction
        conn2 = sqlite3.connect(test_db.db_path, timeout=1.0)
        conn2.execute("BEGIN EXCLUSIVE")
        
        # Try to write from main connection (should retry)
        memory = Memory(raw_text="Test during lock")
        
        # This should eventually succeed due to retry logic
        # or fail gracefully without corruption
        try:
            memory_id = test_db.add_memory(memory)
            # If it succeeds, the retry logic worked
            assert memory_id is not None
        except sqlite3.DatabaseError:
            # If it fails, that's also acceptable as long as
            # the database isn't corrupted
            pass
        finally:
            conn2.rollback()
            conn2.close()
        
        # Database should still be functional
        test_memory = Memory(raw_text="Test after lock")
        memory_id = test_db.add_memory(test_memory)
        assert memory_id is not None
    
    def test_malformed_json_in_extracted_data(self, test_db):
        """Test handling of malformed JSON in extracted_data field"""
        # Directly insert malformed JSON
        cursor = test_db.conn.execute(
            """INSERT INTO memories (uuid, raw_text, extracted_data, status)
               VALUES (?, ?, ?, ?)""",
            ("test-uuid", "Test", "{invalid json}", "completed")
        )
        test_db.conn.commit()
        
        # Try to retrieve - should handle gracefully
        memory = test_db.get_memory_by_uuid("test-uuid")
        assert memory is not None
        assert memory.raw_text == "Test"
        # Extracted data should be None or empty dict due to parse error
        assert memory.extracted_data is None or memory.extracted_data == {}
    
    def test_database_size_limits(self, test_db):
        """Test behavior with large amounts of data"""
        # Add many memories
        generator = TestDataGenerator()
        batch_size = 100
        
        for batch in range(3):  # 300 memories total
            memories = generator.generate_memories(batch_size)
            for memory in memories:
                test_db.add_memory(memory)
        
        # Database should still be responsive
        import time
        start = time.time()
        results = test_db.search_memories("test")
        search_time = time.time() - start
        
        # Search should complete in reasonable time
        assert search_time < 2.0  # 2 seconds max
        
        # Get recent memories should also be fast
        start = time.time()
        recent = test_db.get_recent_memories(50)
        recent_time = time.time() - start
        
        assert recent_time < 1.0  # 1 second max
        assert len(recent) <= 50
    
    def test_null_and_empty_values(self, test_db):
        """Test handling of null and empty values"""
        # Memory with minimal data
        memory = Memory(raw_text="")
        memory_id = test_db.add_memory(memory)
        assert memory_id is not None
        
        # Memory with None values
        memory2 = Memory(
            raw_text="Test",
            summary=None,
            extracted_data=None,
            thought_type=None
        )
        memory_id2 = test_db.add_memory(memory2)
        assert memory_id2 is not None
        
        # Should be retrievable
        retrieved = test_db.get_recent_memories(2)
        assert len(retrieved) == 2