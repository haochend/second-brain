-- Second Brain Database Schema
-- Starting simple, will expand as needed

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Raw content
    raw_text TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'text', -- 'text', 'voice', 'import'
    
    -- Extracted data (JSON)
    extracted_data JSON,
    
    -- Flattened key fields for easier querying
    thought_type TEXT,
    summary TEXT,
    
    -- Status
    status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'error'
    processed_at DATETIME,
    error_message TEXT,
    
    -- Metadata
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_memories_thought_type ON memories(thought_type);
CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status);

-- Full-text search on raw text and summary
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    uuid UNINDEXED,
    raw_text,
    summary,
    content='memories',
    content_rowid='id'
);

-- Note: FTS triggers removed - FTS updates are handled in Python code
-- to avoid "database disk image is malformed" errors with special characters