"""Simple queue system for memory processing"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid


class Queue:
    """File-based queue for reliable memory processing"""
    
    def __init__(self, queue_dir: Optional[str] = None):
        """Initialize queue with directory"""
        if queue_dir is None:
            memory_home = os.path.expanduser(os.getenv("MEMORY_HOME", "~/.memory"))
            queue_dir = os.path.join(memory_home, "queue")
        
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different states
        (self.queue_dir / "pending").mkdir(exist_ok=True)
        (self.queue_dir / "processing").mkdir(exist_ok=True)
        (self.queue_dir / "completed").mkdir(exist_ok=True)
        (self.queue_dir / "failed").mkdir(exist_ok=True)
    
    def add(self, item_type: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add item to queue"""
        item_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        queue_item = {
            "id": item_id,
            "type": item_type,  # 'text', 'voice', etc.
            "content": content,
            "metadata": metadata or {},
            "timestamp": timestamp,
            "status": "pending"
        }
        
        # Save to pending directory
        file_path = self.queue_dir / "pending" / f"{item_id}.json"
        with open(file_path, 'w') as f:
            json.dump(queue_item, f, indent=2)
        
        return item_id
    
    def get_pending(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get pending items from queue"""
        items = []
        pending_dir = self.queue_dir / "pending"
        
        for file_path in list(pending_dir.glob("*.json"))[:limit]:
            try:
                with open(file_path, 'r') as f:
                    item = json.load(f)
                items.append(item)
            except (json.JSONDecodeError, IOError):
                # Skip corrupted files
                continue
        
        return sorted(items, key=lambda x: x.get('timestamp', ''))
    
    def mark_processing(self, item_id: str) -> bool:
        """Mark item as processing"""
        return self._move_item(item_id, "pending", "processing")
    
    def mark_completed(self, item_id: str) -> bool:
        """Mark item as completed"""
        return self._move_item(item_id, "processing", "completed")
    
    def mark_failed(self, item_id: str, error: Optional[str] = None) -> bool:
        """Mark item as failed"""
        # Add error to item if provided
        if error:
            processing_path = self.queue_dir / "processing" / f"{item_id}.json"
            if processing_path.exists():
                try:
                    with open(processing_path, 'r') as f:
                        item = json.load(f)
                    item['error'] = error
                    item['failed_at'] = datetime.now().isoformat()
                    with open(processing_path, 'w') as f:
                        json.dump(item, f, indent=2)
                except (json.JSONDecodeError, IOError):
                    pass
        
        return self._move_item(item_id, "processing", "failed")
    
    def _move_item(self, item_id: str, from_state: str, to_state: str) -> bool:
        """Move item between states"""
        from_path = self.queue_dir / from_state / f"{item_id}.json"
        to_path = self.queue_dir / to_state / f"{item_id}.json"
        
        if from_path.exists():
            try:
                # Read, update status, and move
                with open(from_path, 'r') as f:
                    item = json.load(f)
                
                item['status'] = to_state
                item[f'{to_state}_at'] = datetime.now().isoformat()
                
                with open(to_path, 'w') as f:
                    json.dump(item, f, indent=2)
                
                from_path.unlink()  # Remove old file
                return True
            except (json.JSONDecodeError, IOError):
                return False
        return False
    
    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        stats = {}
        for state in ['pending', 'processing', 'completed', 'failed']:
            state_dir = self.queue_dir / state
            stats[state] = len(list(state_dir.glob("*.json")))
        return stats
    
    def cleanup_completed(self, days: int = 7):
        """Clean up old completed items"""
        completed_dir = self.queue_dir / "completed"
        cutoff = datetime.now().timestamp() - (days * 86400)
        
        for file_path in completed_dir.glob("*.json"):
            if file_path.stat().st_mtime < cutoff:
                file_path.unlink()