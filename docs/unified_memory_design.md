# Unified Memory System - Design Document
*Version 1.0 - Personal Local-First Implementation*

## Executive Summary

A unified memory system that captures all thoughts through voice—tasks, ideas, feelings, observations—and presents different views based on what you need. Unlike traditional apps that force you to categorize thoughts at input, this system accepts everything naturally and extracts meaning gently, without forcing structure where none exists.

**Core Insight**: Your mind doesn't separate tasks from ideas from observations. Neither should your memory system. Capture everything, understand what's there, surface it when needed.

## Vision & Principles

### Vision
"Your thoughts, understood and remembered."

## Core Principles
1. **Capture Everything**: Random thoughts, feelings, ideas, observations - not just tasks
2. **Gentle Extraction**: Don't force structure where it doesn't exist
3. **Flexible Views**: Different lenses for different needs (tasks, ideas, mood, topics)
4. **Natural Expression**: Think out loud without worrying about format
5. **Local-First**: Your thoughts stay yours, cloud is optional

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Input Layer                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  Voice   │  │   Text   │  │  Import  │              │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘              │
│       └─────────────┼─────────────┘                     │
│                     ▼                                    │
│              ┌──────────────┐                           │
│              │ Transcription│                           │
│              └──────┬───────┘                           │
└─────────────────────┼────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────┐
│                Processing Pipeline                       │
│  ┌────────────────────────────────────────────────┐     │
│  │            Unified Extraction Engine           │     │
│  │  • Actions & Tasks                             │     │
│  │  • Entities (People, Projects, Topics)         │     │
│  │  • Temporal References                         │     │
│  │  • Decisions & Facts                           │     │
│  │  • Questions & Blockers                        │     │
│  │  • Emotional Context                           │     │
│  └────────────────┬───────────────────────────────┘     │
│                    ▼                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │           Enrichment & Embedding               │     │
│  │  • Vector Embeddings                           │     │
│  │  • Relationship Mapping                        │     │
│  │  • Confidence Scoring                          │     │
│  │  • Project Inference                           │     │
│  └────────────────┬───────────────────────────────┘     │
└────────────────────┼─────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   Storage Layer                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │                SQLite Database                   │    │
│  │  memories table with rich JSON fields            │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Vector Index (Qdrant)               │    │
│  │  For semantic search and similarity              │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────────┐
│                    Access Layer                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │Task View │  │ Context  │  │  Search  │  │  MCP   │  │
│  │   API    │  │   API    │  │   API    │  │ Server │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Data Model

```sql
-- Core memories table
CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT UNIQUE NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Raw content
    raw_text TEXT NOT NULL,
    audio_path TEXT,  -- Optional path to audio file
    source TEXT NOT NULL,  -- 'voice', 'text', 'import'
    
    -- Extracted structured data (JSON)
    actions JSON,      -- [{action, priority, deadline, status}] - if any
    entities JSON,     -- {people: [], projects: [], topics: [], locations: []}
    temporal JSON,     -- {mentioned_dates: [], relative_times: []}
    decisions JSON,    -- [{decision, rationale, date}] - if any
    questions JSON,    -- [{question, context}] - open questions, wonderings
    ideas JSON,        -- [{idea, trigger, potential}] - creative thoughts
    observations JSON, -- [{observation, context}] - things noticed
    feelings JSON,     -- [{feeling, intensity, context}] - emotional content
    
    -- Metadata
    thought_type TEXT, -- 'action', 'idea', 'observation', 'question', 'feeling', 'memory', 'mixed'
    summary TEXT,      -- One-line summary from LLM
    tags JSON,         -- Auto-generated flexible tags
    confidence REAL,   -- 0.0 to 1.0
    energy_level TEXT, -- 'low', 'normal', 'high', 'anxious', 'excited'
    project TEXT,      -- Inferred if applicable
    thread_id TEXT,    -- For grouping related thoughts
    parent_id INTEGER, -- For thought evolution/replies
    
    -- Search optimization
    embedding BLOB,    -- Vector embedding for semantic search
    fts_text TEXT,     -- Optimized text for full-text search
    
    -- Status tracking
    status TEXT DEFAULT 'active',  -- 'active', 'completed', 'archived', 'recurring'
    completed_at DATETIME,
    
    -- Sync support (future)
    modified_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    sync_status TEXT DEFAULT 'local',
    deleted BOOLEAN DEFAULT FALSE,
    
    FOREIGN KEY (parent_id) REFERENCES memories(id)
);

-- Indexes for common queries
CREATE INDEX idx_memories_timestamp ON memories(timestamp DESC);
CREATE INDEX idx_memories_project ON memories(project);
CREATE INDEX idx_memories_thread ON memories(thread_id);
CREATE INDEX idx_memories_status ON memories(status);
CREATE INDEX idx_memories_thought_type ON memories(thought_type);
CREATE INDEX idx_memories_parent ON memories(parent_id);

-- Full-text search
CREATE VIRTUAL TABLE memories_fts USING fts5(
    uuid UNINDEXED,
    fts_text,
    content='memories',
    content_rowid='id'
);

-- References table - which memories reference each other
CREATE TABLE references (
    id INTEGER PRIMARY KEY,
    from_memory_id INTEGER NOT NULL,
    to_memory_id INTEGER NOT NULL,
    reference_type TEXT,  -- 'mentions', 'continues', 'answers', 'blocks'
    confidence REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_memory_id) REFERENCES memories(id),
    FOREIGN KEY (to_memory_id) REFERENCES memories(id)
);

-- Views for common queries (like Notion's linked databases)
CREATE VIEW tasks_view AS
SELECT 
    id, timestamp, raw_text, summary,
    json_extract(actions, '$[0].text') as task,
    json_extract(actions, '$[0].priority') as priority,
    json_extract(actions, '$[0].deadline') as deadline,
    project, status
FROM memories
WHERE json_array_length(actions) > 0;

CREATE VIEW daily_notes AS
SELECT 
    date(timestamp) as day,
    GROUP_CONCAT(summary, ' | ') as thoughts,
    COUNT(*) as thought_count,
    SUM(CASE WHEN thought_type = 'action' THEN 1 ELSE 0 END) as tasks,
    SUM(CASE WHEN thought_type = 'idea' THEN 1 ELSE 0 END) as ideas
FROM memories
GROUP BY date(timestamp);
```

## Core Components

### 1. Input & Capture (Immediate, Lightweight)

```python
class InputHandler:
    def __init__(self):
        self.queue = Queue("~/.memory/queue")
        
    def capture_voice(self):
        """Just record and queue - no processing"""
        audio = self.record_until_silence()
        
        # Save raw audio immediately
        audio_id = str(uuid4())
        audio_path = f"~/.memory/raw/{audio_id}.wav"
        audio.save(audio_path)
        
        # Queue for processing
        self.queue.add({
            'id': audio_id,
            'type': 'voice',
            'path': audio_path,
            'timestamp': datetime.now()
        })
        
        print("✓ Captured")
        return audio_id
    
    def capture_text(self, text):
        """Queue text for processing"""
        text_id = str(uuid4())
        self.queue.add({
            'id': text_id,
            'type': 'text',
            'content': text,
            'timestamp': datetime.now()
        })
        
        print("✓ Saved")
        return text_id
```

### 2. Background Processor (Runs every 5-10 minutes)

```python
class BackgroundProcessor:
    def __init__(self):
        self.queue = Queue("~/.memory/queue")
        self.whisper = WhisperModel("large")  # Can use larger model
        self.llm = Ollama("llama3.2")  # Or even GPT-4 for better extraction
        
    def process_batch(self):
        """Process all queued items in batch"""
        items = self.queue.get_all_pending()
        
        if not items:
            return
        
        # Group by type for efficient processing
        voice_items = [i for i in items if i['type'] == 'voice']
        text_items = [i for i in items if i['type'] == 'text']
        
        # Batch transcribe voice
        if voice_items:
            transcriptions = self.batch_transcribe(voice_items)
            for item, text in zip(voice_items, transcriptions):
                item['transcribed_text'] = text
        
        # Now extract from all items together for better context
        all_thoughts = voice_items + text_items
        
        # Process with context awareness
        for i, thought in enumerate(all_thoughts):
            # Can look at previous thoughts for context
            context = all_thoughts[max(0, i-5):i]
            
            extracted = self.deep_extract(
                thought.get('transcribed_text') or thought.get('content'),
                context=context
            )
            
            # Store enriched memory
            self.store_memory(thought, extracted)
            
        # After storing, do relationship building
        self.build_relationships(all_thoughts)
        
        # Mark as processed
        self.queue.mark_processed([i['id'] for i in items])
    
    def deep_extract(self, text, context=None):
        """Deeper extraction with context"""
        context_text = "\n".join([c.get('transcribed_text', '') for c in context])
        
        prompt = f"""
        Previous context:
        {context_text}
        
        Current thought: "{text}"
        
        Extract with awareness of the context. Look for:
        - Continuations of previous thoughts
        - Answers to previous questions
        - References to earlier mentions
        - Evolution of ideas
        
        [JSON structure as before...]
        """
        
        return self.llm.extract(prompt)
    
    def build_relationships(self, thoughts):
        """Find connections between thoughts"""
        # Can be more sophisticated since not real-time
        for thought in thoughts:
            similar = self.find_similar_memories(thought)
            for related in similar:
                self.create_reference(thought['id'], related['id'])
```

### 2. Extraction Engine

```python
class ExtractionEngine:
    def __init__(self):
        # Local LLM for extraction (Ollama)
        self.llm = Ollama("llama3.2")
        
    def extract(self, text):
        # One pass - let the LLM understand naturally
        prompt = f"""
        Understand this thought: "{text}"
        
        Return a JSON object with this structure:
        {{
            "thought_type": "action|idea|observation|question|feeling|decision|memory|mixed",
            "summary": "one line summary of the thought",
            "actions": [
                {{"text": "action to take", "deadline": "optional", "priority": "high|medium|low"}}
            ],
            "entities": {{
                "people": ["names mentioned"],
                "projects": ["project names"],
                "topics": ["topics discussed"]
            }},
            "temporal": {{
                "dates": ["specific dates mentioned"],
                "relative": ["tomorrow", "next week", etc]
            }},
            "decisions": [
                {{"decision": "what was decided", "reason": "why"}}
            ],
            "questions": [
                {{"question": "what's being asked/wondered", "context": "optional context"}}
            ],
            "ideas": [
                {{"idea": "the creative thought", "trigger": "what sparked it"}}
            ],
            "observations": [
                {{"observation": "what was noticed", "context": "optional"}}
            ],
            "mood": {{
                "feeling": "emotional state if expressed",
                "energy": "high|normal|low|anxious|excited"
            }}
        }}
        
        Only include fields that are actually present in the thought.
        Empty arrays/objects are fine for missing elements.
        """
        
        # LLM returns structured JSON
        result = self.llm.extract(prompt)
        
        # Validate and clean the response
        return self.validate_extraction(result)
    
    def validate_extraction(self, result):
        # Ensure all expected fields exist, even if empty
        defaults = {
            'thought_type': 'general',
            'summary': '',
            'actions': [],
            'entities': {'people': [], 'projects': [], 'topics': []},
            'temporal': {'dates': [], 'relative': []},
            'decisions': [],
            'questions': [],
            'ideas': [],
            'observations': [],
            'mood': {}
        }
        
        # Merge with defaults to ensure structure
        for key, default_value in defaults.items():
            if key not in result:
                result[key] = default_value
                
        return result
```

### 3. Storage Manager

```python
class StorageManager:
    def __init__(self, db_path="~/.memory/unified.db"):
        self.db = sqlite3.connect(db_path)
        self.vector_store = QdrantClient(path="~/.memory/vectors")
        
    def store_memory(self, memory):
        # Generate embedding
        memory['embedding'] = self.generate_embedding(memory['raw_text'])
        
        # Store in SQLite
        memory_id = self.insert_memory(memory)
        
        # Store vector for semantic search
        self.vector_store.upsert(
            collection_name="memories",
            points=[{
                'id': memory_id,
                'vector': memory['embedding'],
                'payload': {'text': memory['raw_text']}
            }]
        )
        
        # Update FTS index
        self.update_fts(memory_id, memory['fts_text'])
        
        return memory_id
```

### 4. Query Interface

```python
class QueryInterface:
    def __init__(self, storage):
        self.storage = storage
        
    def query(self, natural_query):
        """Parse natural language queries into structured searches"""
        # "ideas about note taking from yesterday"
        # "tasks assigned to Sarah" 
        # "decisions about auth last week"
        # "everything about the photography app"
        
        parsed = self.parse_natural_query(natural_query)
        return self.execute_query(parsed)
    
    def get_daily_note(self, date=None):
        """Everything from a specific day, chronologically"""
        date = date or datetime.now().date()
        return self.storage.get_by_date(date)
    
    def get_thread(self, memory_id):
        """Get a thought and everything related to it"""
        memory = self.storage.get(memory_id)
        return {
            'original': memory,
            'references': self.find_references(memory),
            'backlinks': self.find_backlinks(memory),
            'timeline': self.get_thought_evolution(memory)
        }
    
    def get_project_view(self, project=None):
        """Everything about a project - decisions, tasks, ideas, people"""
        if not project:
            project = self.infer_current_project()
            
        return {
            'tasks': self.get_project_tasks(project),
            'decisions': self.get_project_decisions(project),
            'ideas': self.get_project_ideas(project),
            'people': self.get_project_people(project),
            'timeline': self.get_project_timeline(project),
            'blockers': self.get_project_blockers(project)
        }
    
    def get_person_context(self, person):
        """Everything about interactions with a person"""
        return {
            'mentions': self.storage.search_entity('person', person),
            'commitments': self.get_commitments_to(person),
            'shared_projects': self.get_shared_projects(person),
            'interaction_timeline': self.get_interaction_history(person)
        }
    
    def get_smart_filters(self):
        """Pre-built filters like Linear"""
        return {
            'inbox': self.get_unprocessed(),  # Recent thoughts not yet acted on
            'today': self.get_todays_focus(),  # Tasks + meetings for today
            'blocked': self.get_blocked_tasks(),
            'decisions_needed': self.get_open_questions(),
            'recurring_themes': self.get_recurring_topics(),  # What you think about often
            'energy_map': self.get_energy_patterns()  # When you're most creative/focused
        }
    
    def search_with_context(self, query):
        """Search that understands context"""
        # Not just text matching, but semantic + temporal + entity aware
        results = self.storage.hybrid_search(query)
        
        # Enrich with context
        for result in results:
            result['thread'] = self.get_thread_preview(result['id'])
            result['related'] = self.get_related_memories(result['id'])
            
        return results
```
```

### 5. MCP Server

```python
class MemoryMCPServer:
    """Model Context Protocol server for AI tool integration"""
    
    def __init__(self, query_interface):
        self.query = query_interface
        
    async def handle_request(self, request):
        if request.method == "get_context":
            # Auto-inject relevant context
            context = self.query.get_context_for_ai(
                current_context=request.params.get('current_context')
            )
            return self.format_context(context)
            
        elif request.method == "search":
            results = self.query.search(request.params['query'])
            return self.format_results(results)
            
        elif request.method == "get_tasks":
            tasks = self.query.get_tasks(request.params.get('filters'))
            return self.format_tasks(tasks)
```

## User Interfaces

### 1. CLI Interface (Primary for MVP)

```bash
# Quick capture - instant, no waiting
$ memory add
🎤 Recording... (press Enter when done)
[speaking...]
✓ Captured! Will be processed soon.

$ memory add "Just met with Sarah about the new architecture"
✓ Saved! Will be processed soon.

# Check processing status
$ memory status
📥 Queue: 3 items pending
⏰ Last processed: 5 minutes ago
📊 Today: 12 memories processed

# Natural language queries - run against processed memories
$ memory find "ideas about note taking from yesterday"
💡 Yesterday 3:42pm: "What if notes were more like memory palaces..."
💡 Yesterday 9:15pm: "Voice notes but with automatic structure extraction"
🔗 Related thread: "Memory palace visualization concept" (last week)

# Force immediate processing if needed
$ memory process --now
Processing 3 queued items...
✓ Processed: 3 memories added, 7 connections found

# Browse everything chronologically
$ memory browse --date yesterday
[Shows all processed memories from yesterday with extracted structure]

# Review and correct extractions
$ memory review
📝 10:30am: "Meet with Sarah about auth"
   Extracted: [task: "Meet with Sarah", topic: "auth"]
   Correct? (y/n/edit): y

📝 10:45am: "The new linear algorithm is fascinating"
   Extracted: [observation: "linear algorithm"]
   Correct? (y/n/edit): edit
   > It's actually about the Linear app, not an algorithm
   ✓ Updated
```

### 2. System Tray App (Week 2)

- Global hotkey for voice capture
- Floating task widget
- Quick search bar
- Notification for extracted tasks/deadlines

### 3. Web Interface (Future)

- Timeline view of memories
- Task kanban board
- Knowledge graph visualization
- Voice playback with transcription

## Integration Points

### 1. AI Tools (via MCP)
```python
# Automatic context injection
# When Claude/Cursor/Windsurf opens, they receive:
{
    "recent_decisions": [...],
    "current_blockers": [...],
    "relevant_context": [...],
    "active_projects": [...]
}
```

### 2. Calendar Integration
- Extract meetings and deadlines
- Sync back meeting notes as memories

### 3. Development Tools
- Git commit messages from completed tasks
- PR descriptions from decision history
- Documentation from extracted facts

## Privacy & Security

### Local-First Approach
- All processing happens locally
- Audio stored locally (~/.memory/audio/)
- Database encrypted at rest (optional)
- No telemetry without explicit consent

### Future Cloud Sync (Optional)
- End-to-end encryption
- Selective sync (mark memories as local-only)
- Self-hosted option
- Export everything anytime

## Implementation Roadmap

### Week 1: Core System
**Day 1-2: Storage & Basic Pipeline**
- SQLite setup with schema
- Basic voice capture (Whisper)
- Simple extraction (regex + patterns)

**Day 3-4: Extraction Engine**
- Integrate local LLM (Ollama)
- Action/entity/temporal extraction
- Confidence scoring

**Day 5-7: Query Interface**
- Task view implementation
- Basic search (FTS)
- CLI interface

### Week 2: Intelligence & Integration
**Day 8-10: Semantic Search**
- Vector embeddings
- Qdrant integration
- Hybrid search

**Day 11-12: MCP Server**
- Context API
- Tool registration
- Testing with Claude

**Day 13-14: Polish & Testing**
- Error handling
- Performance optimization
- Documentation

### Post-MVP Enhancements
- **Month 2**: System tray app, better extraction, relationship mapping
- **Month 3**: Web UI, calendar sync, git integration
- **Quarter 2**: Cloud sync, team features, mobile app

## Technical Stack

### Core Dependencies
```toml
[dependencies]
# Local AI
openai-whisper = "^1.0"  # Voice transcription
ollama = "^0.3"          # Local LLM
sentence-transformers = "^2.0"  # Embeddings

# Storage
sqlite3 = "built-in"
qdrant-client = "^1.7"   # Vector search

# Voice
pyaudio = "^0.2"         # Audio capture
webrtcvad = "^2.0"       # Voice activity detection

# Interface
click = "^8.0"           # CLI
fastapi = "^0.100"       # MCP server
```

### System Requirements
- **Minimum**: 8GB RAM, 20GB storage
- **Recommended**: 16GB RAM, 50GB storage, GPU for faster transcription
- **OS**: macOS, Linux (Windows WSL2)

## Success Metrics

### User Experience
- Time to capture: <2 seconds (just save and queue)
- Processing delay: 5-10 minutes (acceptable for non-urgent recall)
- Extraction accuracy: >85% (with ability to review/correct)
- Zero friction capture: No categorization or structure required

### System Performance
- Batch transcription: Process 10+ voice notes at once
- Deep extraction: Can use larger models (not real-time constrained)
- Relationship discovery: Find connections across all memories
- Storage growth: ~1MB/day typical use

## Configuration

```yaml
# ~/.memory/config.yaml
memory:
  storage:
    path: ~/.memory/unified.db
    audio_path: ~/.memory/audio
    
  capture:
    hotkey: "cmd+shift+m"
    auto_stop_silence: 2.0  # seconds
    
  extraction:
    model: "llama3.2"
    confidence_threshold: 0.7
    
  context:
    max_age_hours: 168  # 1 week
    max_items: 20
    
  privacy:
    store_audio: true
    encryption: false  # Set true for encryption
    local_only: true   # No cloud sync
```

## Conclusion

This unified memory system represents a fundamental shift in personal information management. By treating all input as interconnected memory and providing intelligent views based on current needs, we eliminate the artificial boundaries between task management, note-taking, and AI context.

The local-first approach ensures privacy while the modular architecture allows for future cloud capabilities. The focus on voice input and automatic extraction removes friction from capture, while deep understanding ensures nothing important is lost.

**Next Step**: Begin Week 1 implementation focusing on the core storage and extraction pipeline.