"""Database schema for memory consolidation layers"""

CONSOLIDATION_SCHEMA = """
-- Daily consolidations
CREATE TABLE IF NOT EXISTS daily_consolidations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE UNIQUE NOT NULL,
    narrative TEXT,
    key_decisions JSON,
    main_topics JSON,
    emotional_arc JSON,
    interactions JSON,
    insights JSON,
    completed_actions JSON,
    open_questions JSON,
    energy_pattern JSON,
    source_memory_ids JSON,
    importance_score REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_daily_consolidations_date ON daily_consolidations(date DESC);

-- Weekly patterns
CREATE TABLE IF NOT EXISTS weekly_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_number INTEGER NOT NULL,
    year INTEGER NOT NULL,
    patterns JSON,
    insights TEXT,
    recommendations JSON,
    recurring_themes JSON,
    productivity_patterns JSON,
    collaboration_patterns JSON,
    decision_patterns JSON,
    blocker_patterns JSON,
    creative_patterns JSON,
    stress_triggers JSON,
    success_patterns JSON,
    source_consolidation_ids JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(week_number, year)
);

CREATE INDEX IF NOT EXISTS idx_weekly_patterns_week ON weekly_patterns(year DESC, week_number DESC);

-- Knowledge nodes
CREATE TABLE IF NOT EXISTS knowledge_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT,
    summary TEXT,
    insights JSON,
    decisions JSON,
    questions JSON,
    connections JSON,
    source_memory_ids JSON,
    confidence REAL,
    times_referenced INTEGER DEFAULT 0,
    last_referenced DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_topic ON knowledge_nodes(topic);
CREATE INDEX IF NOT EXISTS idx_knowledge_nodes_confidence ON knowledge_nodes(confidence DESC);

-- Knowledge graph edges
CREATE TABLE IF NOT EXISTS knowledge_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_node_id INTEGER,
    to_node_id INTEGER,
    relationship_type TEXT,
    strength REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_node_id) REFERENCES knowledge_nodes(id),
    FOREIGN KEY (to_node_id) REFERENCES knowledge_nodes(id)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_edges_from ON knowledge_edges(from_node_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_edges_to ON knowledge_edges(to_node_id);

-- Wisdom/principles
CREATE TABLE IF NOT EXISTS wisdom (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT, -- 'principle', 'heuristic', 'insight'
    content TEXT,
    context TEXT,
    exceptions TEXT,
    confidence REAL,
    evidence_count INTEGER,
    times_applied INTEGER DEFAULT 0,
    success_rate REAL,
    learned_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wisdom_type ON wisdom(type);
CREATE INDEX IF NOT EXISTS idx_wisdom_confidence ON wisdom(confidence DESC);

-- Add actionable field to memories table if it doesn't exist
ALTER TABLE memories ADD COLUMN actionable BOOLEAN DEFAULT 0;
ALTER TABLE memories ADD COLUMN urgency TEXT;
ALTER TABLE memories ADD COLUMN completed BOOLEAN DEFAULT 0;
ALTER TABLE memories ADD COLUMN connections JSON;

-- Create indices for actionable queries
CREATE INDEX IF NOT EXISTS idx_memories_actionable ON memories(actionable, completed, urgency DESC);
"""


def migrate_database(db_conn):
    """Apply consolidation schema to existing database"""
    try:
        # Split the schema into individual statements to handle errors better
        statements = CONSOLIDATION_SCHEMA.strip().split(';')
        
        for statement in statements:
            statement = statement.strip()
            if not statement:
                continue
                
            # Handle ALTER TABLE statements carefully
            if statement.startswith('ALTER TABLE'):
                try:
                    db_conn.execute(statement)
                except Exception as e:
                    # Column might already exist, that's OK
                    if 'duplicate column name' not in str(e).lower():
                        print(f"Warning during migration: {e}")
            else:
                # Create tables and indices normally
                db_conn.execute(statement)
        
        db_conn.commit()
        print("✓ Consolidation schema applied successfully")
        return True
        
    except Exception as e:
        print(f"Error applying consolidation schema: {e}")
        return False