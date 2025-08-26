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
        # Use a longer timeout to handle concurrent access better
        self.conn = sqlite3.connect(
            self.db_path, 
            timeout=30.0,  # 30 second timeout for lock acquisition
            isolation_level='DEFERRED',  # Better transaction handling
            check_same_thread=False
        )
        self.conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrent access
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=30000")  # 30 second busy timeout
    
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
        
        # Retry logic for database locks
        import time
        max_retries = 5
        for attempt in range(max_retries):
            try:
                cursor = self.conn.execute(query, values)
                self.conn.commit()
                memory_id = cursor.lastrowid
                
                # Manually update FTS table (safer than triggers)
                try:
                    fts_query = "INSERT INTO memories_fts(uuid, raw_text, summary) VALUES (?, ?, ?)"
                    self.conn.execute(fts_query, (
                        data.get('uuid', ''),
                        data.get('raw_text', ''),
                        data.get('summary', '')
                    ))
                    self.conn.commit()
                except:
                    pass  # FTS update is optional
                
                return memory_id
            except sqlite3.OperationalError as e:
                if "locked" in str(e) or "malformed" in str(e):
                    if attempt < max_retries - 1:
                        time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
                        continue
                raise
        
        raise sqlite3.OperationalError("Failed to add memory after retries")
    
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
    
    def get_memory_by_uuid(self, memory_uuid: str) -> Optional[Memory]:
        """Convenience method to get memory by UUID"""
        return self.get_memory(memory_uuid=memory_uuid)
    
    def update_memory(self, memory: Memory) -> bool:
        """Update an existing memory with retry logic"""
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
        
        # Retry logic for database locks
        import time
        max_retries = 5
        for attempt in range(max_retries):
            try:
                cursor = self.conn.execute(query, values)
                self.conn.commit()
                success = cursor.rowcount > 0
                
                if success:
                    # Manually update FTS table (safer than triggers)
                    try:
                        # Delete old FTS entry
                        self.conn.execute("DELETE FROM memories_fts WHERE uuid = ?", (where_param,))
                        # Insert new FTS entry
                        fts_query = "INSERT INTO memories_fts(uuid, raw_text, summary) VALUES (?, ?, ?)"
                        self.conn.execute(fts_query, (
                            where_param,
                            data.get('raw_text', ''),
                            data.get('summary', '')
                        ))
                        self.conn.commit()
                    except:
                        pass  # FTS update is optional
                
                return success
            except sqlite3.OperationalError as e:
                if "locked" in str(e) or "malformed" in str(e):
                    if attempt < max_retries - 1:
                        time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
                        continue
                raise
        
        return False
    
    def sync_fts(self):
        """Sync FTS table with memories table (useful after manual DB changes)"""
        try:
            # Clear FTS
            self.conn.execute("DELETE FROM memories_fts")
            # Repopulate from memories
            self.conn.execute("""
                INSERT INTO memories_fts(uuid, raw_text, summary)
                SELECT uuid, raw_text, COALESCE(summary, '') FROM memories
            """)
            self.conn.commit()
            return True
        except Exception as e:
            print(f"FTS sync failed: {e}")
            return False
    
    def delete_memory(self, memory_id: Optional[int] = None, memory_uuid: Optional[str] = None) -> bool:
        """Delete a memory and its FTS entry"""
        if memory_id:
            where_clause = "id = ?"
            where_param = memory_id
        elif memory_uuid:
            where_clause = "uuid = ?"
            where_param = memory_uuid
        else:
            return False
        
        try:
            # Get UUID for FTS deletion
            if memory_id:
                cursor = self.conn.execute("SELECT uuid FROM memories WHERE id = ?", (memory_id,))
                row = cursor.fetchone()
                uuid_to_delete = row[0] if row else None
            else:
                uuid_to_delete = memory_uuid
            
            # Delete from memories
            cursor = self.conn.execute(f"DELETE FROM memories WHERE {where_clause}", (where_param,))
            
            # Delete from FTS if we have a UUID
            if uuid_to_delete:
                self.conn.execute("DELETE FROM memories_fts WHERE uuid = ?", (uuid_to_delete,))
            
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Delete failed: {e}")
            return False
    
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
                WHERE m.uuid IN (
                    SELECT uuid FROM memories_fts 
                    WHERE memories_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                )
                ORDER BY m.timestamp DESC
            """
            cursor = self.conn.execute(fts_query, (query, limit))
            results = [Memory.from_row(row) for row in cursor]
            if results:
                return results
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
            # Log the error but continue with fallback
            print(f"FTS search failed, using fallback: {e}")
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