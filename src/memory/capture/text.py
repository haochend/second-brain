"""Text input capture for memories"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from .queue import Queue
from ..storage import Database, Memory


class TextCapture:
    """Handle text input capture"""
    
    def __init__(self, queue: Optional[Queue] = None, db: Optional[Database] = None):
        """Initialize text capture"""
        self.queue = queue or Queue()
        self.db = db or Database()
    
    def capture(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Capture text input and add to queue"""
        # Quick validation
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Create a shared UUID for both queue and database
        memory_uuid = str(uuid.uuid4())
        
        # Add to queue for processing
        metadata = metadata or {}
        metadata['memory_uuid'] = memory_uuid
        
        item_id = self.queue.add(
            item_type="text",
            content=text.strip(),
            metadata=metadata
        )
        
        # Also add to database as pending with same UUID
        memory = Memory(
            uuid=memory_uuid,
            raw_text=text.strip(),
            source="text",
            status="pending",
            timestamp=datetime.now()
        )
        memory_id = self.db.add_memory(memory)
        
        return item_id