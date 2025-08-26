"""Database operations for memory storage"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
import uuid


@dataclass
class Memory:
    """Memory data model"""
    id: Optional[int] = None
    uuid: Optional[str] = None
    timestamp: Optional[datetime] = None
    raw_text: str = ""
    source: str = "text"
    extracted_data: Optional[Dict[str, Any]] = None
    thought_type: Optional[str] = None
    summary: Optional[str] = None
    status: str = "pending"
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        # Convert datetime objects to strings
        for key in ['timestamp', 'processed_at', 'created_at', 'updated_at']:
            if data[key] and isinstance(data[key], datetime):
                data[key] = data[key].isoformat()
        # Convert extracted_data to JSON string
        if data['extracted_data']:
            data['extracted_data'] = json.dumps(data['extracted_data'])
        return data
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> 'Memory':
        """Create Memory from database row"""
        data = dict(row)
        # Parse JSON extracted_data
        if data.get('extracted_data'):
            try:
                data['extracted_data'] = json.loads(data['extracted_data'])
            except json.JSONDecodeError:
                data['extracted_data'] = {}
        # Parse datetime strings
        for key in ['timestamp', 'processed_at', 'created_at', 'updated_at']:
            if data.get(key) and isinstance(data[key], str):
                try:
                    data[key] = datetime.fromisoformat(data[key])
                except ValueError:
                    pass
        return cls(**data)


class Database:
    """SQLite database manager for memories"""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection"""
        if db_path is None:
            memory_home = os.path.expanduser(os.getenv("MEMORY_HOME", "~/.memory"))
            Path(memory_home).mkdir(parents=True, exist_ok=True)
            db_path = os.path.join(memory_home, "memories.db")
        
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._init_schema()
    
    def _connect(self):
        """Create database connection"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        # Enable JSON support
        self.conn.execute("PRAGMA journal_mode=WAL")
    
    def _init_schema(self):
        """Initialize database schema"""
        schema_path = Path(__file__).parent.parent.parent.parent / "config" / "schema.sql"
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                schema = f.read()
            self.conn.executescript(schema)
        else:
            # Fallback to inline schema if file not found
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT UNIQUE NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    raw_text TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'text',
                    extracted_data JSON,
                    thought_type TEXT,
                    summary TEXT,
                    status TEXT DEFAULT 'pending',
                    processed_at DATETIME,
                    error_message TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_memories_thought_type ON memories(thought_type);
                CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status);
            """)
        self.conn.commit()
    
    def add_memory(self, memory: Memory) -> int:
        """Add a new memory to the database"""
        if not memory.uuid:
            memory.uuid = str(uuid.uuid4())
        
        data = memory.to_dict()
        
        # Remove id if None (for auto-increment)
        if data['id'] is None:
            del data['id']
        
        columns = list(data.keys())
        placeholders = ["?" for _ in columns]
        values = [data[col] for col in columns]
        
        query = f"""
            INSERT INTO memories ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
        """
        
        cursor = self.conn.execute(query, values)
        self.conn.commit()
        return cursor.lastrowid
    
    def get_memory(self, memory_id: Optional[int] = None, memory_uuid: Optional[str] = None) -> Optional[Memory]:
        """Get a memory by ID or UUID"""
        if memory_id:
            query = "SELECT * FROM memories WHERE id = ?"
            params = (memory_id,)
        elif memory_uuid:
            query = "SELECT * FROM memories WHERE uuid = ?"
            params = (memory_uuid,)
        else:
            return None
        
        cursor = self.conn.execute(query, params)
        row = cursor.fetchone()
        
        if row:
            return Memory.from_row(row)
        return None
    
    def update_memory(self, memory: Memory) -> bool:
        """Update an existing memory"""
        if not memory.id and not memory.uuid:
            return False
        
        data = memory.to_dict()
        data['updated_at'] = datetime.now().isoformat()
        
        # Build update query
        if memory.id:
            where_clause = "id = ?"
            where_param = memory.id
        else:
            where_clause = "uuid = ?"
            where_param = memory.uuid
        
        # Remove id and uuid from update fields
        for key in ['id', 'uuid']:
            if key in data:
                del data[key]
        
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        values = list(data.values()) + [where_param]
        
        query = f"UPDATE memories SET {set_clause} WHERE {where_clause}"
        
        cursor = self.conn.execute(query, values)
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_pending_memories(self, limit: int = 10) -> List[Memory]:
        """Get pending memories for processing"""
        query = """
            SELECT * FROM memories 
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT ?
        """
        cursor = self.conn.execute(query, (limit,))
        return [Memory.from_row(row) for row in cursor]
    
    def search_memories(self, query: str, limit: int = 20) -> List[Memory]:
        """Search memories using full-text search"""
        # First try FTS if table exists
        try:
            fts_query = """
                SELECT m.* FROM memories m
                JOIN memories_fts f ON m.uuid = f.uuid
                WHERE memories_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """
            cursor = self.conn.execute(fts_query, (query, limit))
            results = [Memory.from_row(row) for row in cursor]
            if results:
                return results
        except sqlite3.OperationalError:
            pass
        
        # Fallback to LIKE query
        like_query = """
            SELECT * FROM memories
            WHERE raw_text LIKE ? OR summary LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        search_pattern = f"%{query}%"
        cursor = self.conn.execute(like_query, (search_pattern, search_pattern, limit))
        return [Memory.from_row(row) for row in cursor]
    
    def get_recent_memories(self, limit: int = 20) -> List[Memory]:
        """Get recent memories"""
        query = """
            SELECT * FROM memories
            WHERE status = 'completed'
            ORDER BY timestamp DESC
            LIMIT ?
        """
        cursor = self.conn.execute(query, (limit,))
        return [Memory.from_row(row) for row in cursor]
    
    def get_tasks(self, status: Optional[str] = None) -> List[Memory]:
        """Get memories that are tasks"""
        query = """
            SELECT * FROM memories
            WHERE thought_type = 'action'
            AND status = 'completed'
        """
        params = []
        
        if status:
            # Look for task status in extracted_data JSON
            query += " AND json_extract(extracted_data, '$.actions[0].status') = ?"
            params.append(status)
        
        query += " ORDER BY timestamp DESC"
        
        cursor = self.conn.execute(query, params)
        return [Memory.from_row(row) for row in cursor]
    
    def get_memories_by_date(self, date: datetime) -> List[Memory]:
        """Get memories for a specific date"""
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        query = """
            SELECT * FROM memories
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
        """
        cursor = self.conn.execute(query, (start.isoformat(), end.isoformat()))
        return [Memory.from_row(row) for row in cursor]
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()