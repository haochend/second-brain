"""Unit tests for queue system"""

import pytest
import json
import time
from pathlib import Path

from src.memory.capture import Queue


class TestQueue:
    """Test Queue operations"""
    
    def test_queue_initialization(self, test_queue):
        """Test queue creates correct directory structure"""
        queue_dir = Path(test_queue.queue_dir)
        
        assert queue_dir.exists()
        assert (queue_dir / "pending").exists()
        assert (queue_dir / "processing").exists()
        assert (queue_dir / "completed").exists()
        assert (queue_dir / "failed").exists()
    
    def test_add_item(self, test_queue):
        """Test adding item to queue"""
        item_id = test_queue.add(
            item_type="text",
            content="Test content",
            metadata={"key": "value"}
        )
        
        assert item_id is not None
        assert len(item_id) == 36  # UUID format
        
        # Check file was created
        pending_file = test_queue.queue_dir / "pending" / f"{item_id}.json"
        assert pending_file.exists()
        
        # Check content
        with open(pending_file) as f:
            data = json.load(f)
        
        assert data['id'] == item_id
        assert data['type'] == "text"
        assert data['content'] == "Test content"
        assert data['metadata']['key'] == "value"
        assert data['status'] == "pending"
    
    def test_get_pending(self, test_queue):
        """Test getting pending items"""
        # Add multiple items
        id1 = test_queue.add("text", "Content 1")
        time.sleep(0.01)  # Ensure different timestamps
        id2 = test_queue.add("text", "Content 2")
        time.sleep(0.01)
        id3 = test_queue.add("voice", "Content 3")
        
        # Get pending items
        pending = test_queue.get_pending(limit=2)
        
        assert len(pending) == 2
        # Should be ordered by timestamp (FIFO)
        assert pending[0]['id'] == id1
        assert pending[1]['id'] == id2
    
    def test_mark_processing(self, test_queue):
        """Test marking item as processing"""
        item_id = test_queue.add("text", "Test content")
        
        # Mark as processing
        success = test_queue.mark_processing(item_id)
        assert success is True
        
        # Check file was moved
        pending_file = test_queue.queue_dir / "pending" / f"{item_id}.json"
        processing_file = test_queue.queue_dir / "processing" / f"{item_id}.json"
        
        assert not pending_file.exists()
        assert processing_file.exists()
        
        # Check status was updated
        with open(processing_file) as f:
            data = json.load(f)
        assert data['status'] == "processing"
    
    def test_mark_completed(self, test_queue):
        """Test marking item as completed"""
        item_id = test_queue.add("text", "Test content")
        test_queue.mark_processing(item_id)
        
        # Mark as completed
        success = test_queue.mark_completed(item_id)
        assert success is True
        
        # Check file was moved
        processing_file = test_queue.queue_dir / "processing" / f"{item_id}.json"
        completed_file = test_queue.queue_dir / "completed" / f"{item_id}.json"
        
        assert not processing_file.exists()
        assert completed_file.exists()
        
        # Check status
        with open(completed_file) as f:
            data = json.load(f)
        assert data['status'] == "completed"
    
    def test_mark_failed(self, test_queue):
        """Test marking item as failed"""
        item_id = test_queue.add("text", "Test content")
        test_queue.mark_processing(item_id)
        
        # Mark as failed with error message
        error_msg = "Test error"
        success = test_queue.mark_failed(item_id, error_msg)
        assert success is True
        
        # Check file was moved
        failed_file = test_queue.queue_dir / "failed" / f"{item_id}.json"
        assert failed_file.exists()
        
        # Check error was recorded
        with open(failed_file) as f:
            data = json.load(f)
        assert data['status'] == "failed"
        assert data['error'] == error_msg
    
    def test_get_stats(self, test_queue):
        """Test getting queue statistics"""
        # Create items in different states
        id1 = test_queue.add("text", "Pending 1")
        id2 = test_queue.add("text", "Pending 2")
        id3 = test_queue.add("text", "Processing")
        id4 = test_queue.add("text", "Completed")
        id5 = test_queue.add("text", "Failed")
        
        test_queue.mark_processing(id3)
        test_queue.mark_processing(id4)
        test_queue.mark_completed(id4)
        test_queue.mark_processing(id5)
        test_queue.mark_failed(id5, "Error")
        
        stats = test_queue.get_stats()
        
        assert stats['pending'] == 2
        assert stats['processing'] == 1
        assert stats['completed'] == 1
        assert stats['failed'] == 1
    
    def test_get_item(self, test_queue):
        """Test getting specific item"""
        item_id = test_queue.add("text", "Test content", {"key": "value"})
        
        # Get from pending
        item = test_queue.get_item(item_id)
        assert item is not None
        assert item['id'] == item_id
        assert item['content'] == "Test content"
        
        # Move to processing and get again
        test_queue.mark_processing(item_id)
        item = test_queue.get_item(item_id)
        assert item is not None
        assert item['status'] == "processing"
    
    def test_cleanup_old_completed(self, test_queue):
        """Test cleanup of old completed items"""
        import time
        
        # Add and complete items
        id1 = test_queue.add("text", "Old item")
        id2 = test_queue.add("text", "Recent item")
        
        test_queue.mark_processing(id1)
        test_queue.mark_completed(id1)
        test_queue.mark_processing(id2)
        test_queue.mark_completed(id2)
        
        # Modify timestamp of first item to make it old
        completed_file = test_queue.queue_dir / "completed" / f"{id1}.json"
        
        # Set file modification time to 8 days ago
        import os
        from datetime import datetime, timedelta
        old_timestamp = (datetime.now() - timedelta(days=8)).timestamp()
        os.utime(completed_file, (old_timestamp, old_timestamp))
        
        # Run cleanup (default 7 days)
        removed = test_queue.cleanup_old()
        
        assert removed == 1
        assert not (test_queue.queue_dir / "completed" / f"{id1}.json").exists()
        assert (test_queue.queue_dir / "completed" / f"{id2}.json").exists()
    
    def test_concurrent_queue_operations(self, test_queue):
        """Test queue handles concurrent operations"""
        import threading
        
        results = []
        
        def add_and_process(thread_id):
            try:
                item_id = test_queue.add("text", f"Item from thread {thread_id}")
                test_queue.mark_processing(item_id)
                test_queue.mark_completed(item_id)
                results.append((thread_id, item_id, "success"))
            except Exception as e:
                results.append((thread_id, None, str(e)))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=add_and_process, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Check all operations succeeded
        assert len(results) == 5
        successful = [r for r in results if r[2] == "success"]
        assert len(successful) == 5
        
        # Check stats
        stats = test_queue.get_stats()
        assert stats['completed'] == 5