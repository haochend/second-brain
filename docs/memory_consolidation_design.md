# Memory Consolidation & Knowledge Synthesis - Design Document
*Extension to Unified Memory System*

## Overview

Just as human memory consolidates during sleep—transforming daily experiences into patterns, insights, and wisdom—our system should periodically process raw memories into increasingly useful forms of knowledge. This creates a multi-layered memory system that mimics how our brain actually works.

**Critical Insight**: Task detection and semantic understanding happen during the background processing phase, not at storage or query time. This ensures tasks are ready when AI tools need them while maintaining the flexibility of emergent memory structures.

## The Consolidation Philosophy

### Human Memory Parallel

```
Raw Experience → Working Memory → Processing → Long-term Memory → Wisdom

Our System:
Raw Capture → Background Processing → Daily Consolidation → Patterns → Knowledge
         (instant)  (5-10 min)         (nightly)       (weekly)   (monthly)
```

### Key Insights
- **Immediate processing** ensures tasks are ready for AI tools
- **Semantic search during processing** provides context for better understanding
- **Structure emerges** from patterns, not forced at input
- **Consolidation happens in layers** with different time horizons
- **Forgetting details while keeping insights** is a feature

## Architecture

### Consolidation Pipeline

```
┌─────────────────────────────────────────────────────────┐
│                   Raw Memories Layer                     │
│         (Original thoughts, full detail)                 │
│              Retention: 30-90 days                       │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼ (Nightly Processing)
┌─────────────────────────────────────────────────────────┐
│               Daily Consolidation Layer                  │
│     (Themes, decisions, insights from each day)         │
│              Retention: 6 months                         │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼ (Weekly Processing)
┌─────────────────────────────────────────────────────────┐
│              Pattern Recognition Layer                   │
│    (Recurring themes, behavioral patterns, trends)      │
│              Retention: Indefinite                       │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼ (Monthly Processing)
┌─────────────────────────────────────────────────────────┐
│              Knowledge Synthesis Layer                   │
│   (Concepts, principles, learned experiences)           │
│              Retention: Permanent                        │
└─────────────────────────────────────────────────────────┘
```

## Processing Pipeline

### Background Processing (Every 5-10 minutes)

```python
class BackgroundProcessor:
    """
    Process queued memories with full context and understanding.
    This is where task detection and semantic connections happen.
    """
    
    def process_batch(self):
        """Process all queued items with semantic understanding"""
        items = self.queue.get_all_pending()
        
        if not items:
            return
        
        # Batch transcribe voice items
        voice_items = [i for i in items if i['type'] == 'voice']
        if voice_items:
            transcriptions = self.batch_transcribe(voice_items)
            for item, text in zip(voice_items, transcriptions):
                item['transcribed_text'] = text
        
        # Process each memory with full context
        for i, item in enumerate(items):
            text = item.get('transcribed_text') or item.get('content')
            
            # Step 1: Generate embedding for semantic search
            embedding = self.generate_embedding(text)
            
            # Step 2: Find related memories through semantic search
            related_memories = self.semantic_search(embedding, limit=20)
            
            # Step 3: Extract understanding WITH context from related memories
            context = self.build_context(related_memories)
            understanding = self.extract_with_context(text, context)
            
            # Step 4: Task detection happens HERE
            if self.has_actionable_intent(understanding):
                # Check if this updates an existing task
                existing_task = self.find_similar_task(understanding, related_memories)
                if existing_task:
                    self.update_task(existing_task, understanding)
                else:
                    understanding['actionable'] = True
                    understanding['urgency'] = self.detect_urgency(understanding)
                    
                # Check if this completes a previous task
                self.check_task_completion(understanding, related_memories)
            
            # Step 5: Store enriched memory
            memory = {
                'content': text,
                'embedding': embedding,
                'understanding': understanding,
                'connections': [m['id'] for m in related_memories],
                'actionable': understanding.get('actionable', False),
                'processed_at': datetime.now()
            }
            
            self.store_memory(memory)
        
        # After storing all, build additional relationships
        self.build_relationships(items)
        self.mark_processed([i['id'] for i in items])
    
    def extract_with_context(self, text, context):
        """
        Extract understanding with awareness of related memories.
        This is where emergent structure meets practical needs.
        """
        prompt = f"""
        Current thought: "{text}"
        
        Related context from previous memories:
        {context}
        
        Understand this thought naturally. Extract whatever is meaningful:
        - Is this actionable? (task, commitment, todo)
        - What entities are involved? (people, projects, topics)
        - Any decisions being made?
        - Questions or uncertainties?
        - Ideas or insights?
        - Emotional context?
        - Does this complete or update a previous thought?
        
        Return as flexible JSON. Include only what's actually there.
        Don't force structure where it doesn't exist.
        """
        
        return self.llm.extract(prompt)
    
    def has_actionable_intent(self, understanding):
        """
        Determine if this memory contains something to be done.
        Not based on schema, but on semantic meaning.
        """
        indicators = [
            understanding.get('contains_commitment'),
            understanding.get('future_action'),
            understanding.get('deadline_mentioned'),
            understanding.get('blocking_something'),
            'need to' in str(understanding).lower(),
            'should' in str(understanding).lower(),
            'must' in str(understanding).lower()
        ]
        
        return any(indicators) or understanding.get('actionable', False)
```

### 1. Daily Consolidation (Runs at 2 AM)

```python
class DailyConsolidator:
    """Process today's thoughts into insights"""
    
    def consolidate_day(self, date=None):
        date = date or datetime.now().date()
        memories = self.get_memories_for_date(date)
        
        # Group by threads and topics
        threads = self.identify_thought_threads(memories)
        
        # Extract key elements
        consolidation = {
            'date': date,
            'memory_count': len(memories),
            'key_decisions': self.extract_decisions(memories),
            'main_topics': self.extract_topics(memories),
            'emotional_arc': self.analyze_emotional_journey(memories),
            'important_interactions': self.extract_people_interactions(memories),
            'creative_insights': self.extract_ideas(memories),
            'completed_actions': self.get_completed_tasks(memories),
            'open_questions': self.extract_questions(memories),
            'energy_pattern': self.analyze_energy_levels(memories)
        }
        
        # Generate narrative summary
        daily_narrative = self.generate_narrative(consolidation)
        
        # Store consolidated memory
        return self.store_consolidation({
            'type': 'daily',
            'date': date,
            'narrative': daily_narrative,
            'structured_data': consolidation,
            'source_memories': [m['id'] for m in memories],
            'importance_score': self.calculate_importance(consolidation)
        })
    
    def generate_narrative(self, consolidation):
        """Create a human-readable story of the day"""
        prompt = f"""
        Create a brief narrative summary of this day:
        - Decisions: {consolidation['key_decisions']}
        - Topics: {consolidation['main_topics']}
        - Mood journey: {consolidation['emotional_arc']}
        - Key interactions: {consolidation['important_interactions']}
        
        Write it as a cohesive paragraph, focusing on what mattered.
        """
        return self.llm.generate(prompt)
```

### 2. Weekly Pattern Recognition

```python
class WeeklyPatternRecognizer:
    """Find patterns across the week"""
    
    def identify_patterns(self):
        week_memories = self.get_past_week_memories()
        daily_consolidations = self.get_past_week_consolidations()
        
        patterns = {
            'recurring_themes': self.find_recurring_themes(week_memories),
            'productivity_patterns': self.analyze_productivity(),
            'collaboration_patterns': self.analyze_interactions(),
            'decision_patterns': self.analyze_decision_making(),
            'blocker_patterns': self.find_recurring_blockers(),
            'creative_patterns': self.analyze_creative_timing(),
            'stress_triggers': self.identify_stress_patterns(),
            'success_patterns': self.identify_what_works()
        }
        
        # Generate insights
        insights = self.generate_weekly_insights(patterns)
        
        return self.store_pattern_recognition({
            'type': 'weekly_patterns',
            'week': datetime.now().isocalendar()[1],
            'patterns': patterns,
            'insights': insights,
            'actionable_recommendations': self.generate_recommendations(patterns)
        })
    
    def find_recurring_themes(self, memories):
        """What keeps coming up?"""
        themes = {}
        for memory in memories:
            for topic in memory.get('topics', []):
                themes[topic] = themes.get(topic, 0) + 1
        
        # Return themes that appeared multiple times
        return {
            topic: {
                'count': count,
                'trend': self.analyze_trend(topic),
                'sentiment': self.analyze_sentiment(topic, memories)
            }
            for topic, count in themes.items() 
            if count > 2
        }
    
    def analyze_productivity(self):
        """When are you most effective?"""
        return {
            'peak_hours': self.find_peak_productivity_hours(),
            'task_completion_rate': self.calculate_completion_rate(),
            'focus_duration': self.analyze_focus_sessions(),
            'context_switching': self.measure_context_switching()
        }
```

### 3. Knowledge Node Builder

```python
class KnowledgeNodeBuilder:
    """Transform scattered thoughts into structured knowledge"""
    
    def build_knowledge_nodes(self):
        """Run monthly to synthesize knowledge"""
        
        # Cluster memories by semantic similarity
        clusters = self.cluster_memories_semantically()
        
        knowledge_nodes = []
        for cluster in clusters:
            if cluster['coherence'] > 0.7:  # Strong theme
                node = self.create_knowledge_node(cluster)
                knowledge_nodes.append(node)
        
        return knowledge_nodes
    
    def create_knowledge_node(self, cluster):
        """Transform a cluster into structured knowledge"""
        
        # Synthesize understanding
        synthesis = self.llm.synthesize(f"""
        These related thoughts all discuss a similar topic:
        {cluster['memories']}
        
        Create a structured knowledge summary:
        1. Core concept
        2. Key insights learned
        3. Decisions made
        4. Open questions
        5. Related people/projects
        6. Practical applications
        """)
        
        return {
            'id': generate_id(),
            'type': 'knowledge_node',
            'topic': cluster['primary_topic'],
            'summary': synthesis['core_concept'],
            'insights': synthesis['insights'],
            'decisions': synthesis['decisions'],
            'questions': synthesis['questions'],
            'connections': {
                'people': cluster['people'],
                'projects': cluster['projects'],
                'related_nodes': self.find_related_nodes(cluster)
            },
            'source_memories': cluster['memory_ids'],
            'confidence': cluster['coherence'],
            'created_at': datetime.now(),
            'last_referenced': datetime.now()
        }
    
    def link_knowledge_nodes(self):
        """Build a knowledge graph"""
        nodes = self.get_all_knowledge_nodes()
        
        for node in nodes:
            related = self.find_semantically_related(node, nodes)
            for related_node in related:
                self.create_knowledge_edge(
                    from_node=node,
                    to_node=related_node,
                    relationship=self.determine_relationship(node, related_node)
                )
```

### 4. Wisdom Extractor

```python
class WisdomExtractor:
    """Extract learned principles and patterns"""
    
    def extract_wisdom(self):
        """Run quarterly to extract deep learnings"""
        
        # Look across all consolidation levels
        patterns = self.get_all_patterns()
        knowledge = self.get_all_knowledge_nodes()
        
        wisdom_candidates = []
        
        # Find principles that consistently hold true
        for pattern in patterns:
            if self.is_consistent_principle(pattern):
                wisdom = self.formulate_principle(pattern)
                wisdom_candidates.append(wisdom)
        
        # Extract learned heuristics
        heuristics = self.extract_heuristics(knowledge)
        
        return wisdom_candidates + heuristics
    
    def formulate_principle(self, pattern):
        """Turn a pattern into a principle"""
        
        principle = self.llm.generate(f"""
        This pattern has been observed consistently:
        {pattern}
        
        Formulate this as a personal principle or rule of thumb.
        Include:
        - The principle itself
        - When it applies
        - Exceptions noticed
        - Confidence level
        """)
        
        return {
            'type': 'wisdom',
            'principle': principle['statement'],
            'context': principle['applies_when'],
            'exceptions': principle['exceptions'],
            'evidence_count': pattern['occurrence_count'],
            'confidence': pattern['consistency_score'],
            'learned_date': datetime.now()
        }
    
    def extract_heuristics(self, knowledge_nodes):
        """Extract decision-making heuristics"""
        
        # Look for repeated decision patterns
        decision_patterns = self.analyze_decisions(knowledge_nodes)
        
        heuristics = []
        for pattern in decision_patterns:
            if pattern['success_rate'] > 0.8:
                heuristic = {
                    'type': 'heuristic',
                    'rule': pattern['decision_rule'],
                    'success_rate': pattern['success_rate'],
                    'applications': pattern['example_applications']
                }
                heuristics.append(heuristic)
        
        return heuristics
```

## Emergent Structure with Practical Extraction

### The Balance: Flexibility with Reliability

```python
class FlexibleMemorySystem:
    """
    Memories aren't forced into rigid schemas, but we still
    extract actionable information reliably for practical use.
    """
    
    def store_raw_memory(self, content):
        """
        Minimal structure at storage time - just enough for retrieval
        """
        return {
            'id': generate_id(),
            'content': content,
            'timestamp': now(),
            'embedding': None,  # Generated during processing
            'understanding': None,  # Added during processing
            'actionable': None,  # Detected during processing
        }
    
    def process_memory(self, memory):
        """
        During processing: understand, connect, and detect tasks
        """
        # Generate embedding
        memory['embedding'] = self.generate_embedding(memory['content'])
        
        # Find related memories through semantic search
        related = self.vector_search(memory['embedding'])
        
        # Let LLM understand naturally WITH context
        understanding = self.llm.understand(
            content=memory['content'],
            context=related,
            instructions="""
            Understand this naturally. Don't force categories.
            But DO identify:
            - If this expresses intention to do something
            - If this completes or updates a previous thought
            - Key entities (people, projects, topics)
            - Temporal markers
            - Emotional context
            
            Return free-form JSON with whatever you find.
            """
        )
        
        memory['understanding'] = understanding
        memory['actionable'] = self.is_actionable(understanding)
        memory['connections'] = [r['id'] for r in related]
        
        return memory
    
    def query_for_tasks(self):
        """
        Tasks are just actionable memories that aren't complete.
        They were detected during processing, so this is fast.
        """
        return self.db.query("""
            SELECT * FROM memories 
            WHERE actionable = true 
            AND completed = false
            ORDER BY urgency DESC, timestamp DESC
        """)
    
    def get_ai_context(self):
        """
        AI tools get pre-processed, ready-to-use context
        """
        return {
            'active_tasks': self.query_for_tasks(),
            'recent_decisions': self.get_recent_decisions(),
            'current_context': self.get_relevant_context(),
            'blockers': self.get_blockers()
        }
```

### Why This Architecture Works

1. **Capture is instant** - No processing delay
2. **Processing enriches** - Semantic search → Understanding → Task detection
3. **Queries are fast** - Everything pre-computed
4. **AI tools get rich context** - Tasks already detected and ready
5. **Structure emerges** - Not forced at input time

### The Timeline

```
[CAPTURE - Instant]
"Need to review Sarah's PR before standup"
    ↓ (queued)
    
[PROCESS - 5 min later]
→ Transcribe
→ Generate embedding
→ Semantic search: finds previous Sarah/PR memories
→ Understand with context
→ Detect: actionable=true, deadline="before standup"
→ Store enriched
    ↓
    
[QUERY - Anytime]
Claude: "What tasks do you have?"
→ Instant response with pre-detected tasks
```

## Data Models

### Consolidation Tables

```sql
-- Daily consolidations
CREATE TABLE daily_consolidations (
    id INTEGER PRIMARY KEY,
    date DATE UNIQUE,
    narrative TEXT,
    key_decisions JSON,
    main_topics JSON,
    emotional_arc JSON,
    interactions JSON,
    insights JSON,
    source_memory_ids JSON,
    importance_score REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Weekly patterns
CREATE TABLE weekly_patterns (
    id INTEGER PRIMARY KEY,
    week_number INTEGER,
    year INTEGER,
    patterns JSON,
    insights TEXT,
    recommendations JSON,
    source_consolidation_ids JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(week_number, year)
);

-- Knowledge nodes
CREATE TABLE knowledge_nodes (
    id INTEGER PRIMARY KEY,
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

-- Knowledge graph edges
CREATE TABLE knowledge_edges (
    id INTEGER PRIMARY KEY,
    from_node_id INTEGER,
    to_node_id INTEGER,
    relationship_type TEXT,
    strength REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_node_id) REFERENCES knowledge_nodes(id),
    FOREIGN KEY (to_node_id) REFERENCES knowledge_nodes(id)
);

-- Wisdom/principles
CREATE TABLE wisdom (
    id INTEGER PRIMARY KEY,
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
```

## Query Interface Enhancements

### Multi-Level Querying

```python
class EnhancedQueryInterface:
    """Query across all memory levels intelligently"""
    
    def query(self, natural_query):
        """Route query to appropriate memory level"""
        
        query_type = self.classify_query(natural_query)
        
        if query_type == 'specific_recent':
            # Search raw memories
            return self.search_raw_memories(natural_query)
            
        elif query_type == 'pattern_seeking':
            # Search patterns and wisdom
            patterns = self.search_patterns(natural_query)
            wisdom = self.search_wisdom(natural_query)
            return self.combine_results(patterns, wisdom)
            
        elif query_type == 'conceptual':
            # Search knowledge nodes
            return self.search_knowledge_graph(natural_query)
            
        elif query_type == 'temporal':
            # Search consolidations
            return self.search_consolidations(natural_query)
            
        else:
            # Search everything, rank by relevance
            return self.federated_search(natural_query)
    
    def get_context_aware_suggestions(self):
        """Proactively surface relevant wisdom"""
        
        current_context = self.get_current_context()
        
        suggestions = {
            'relevant_principles': self.find_applicable_wisdom(current_context),
            'similar_situations': self.find_similar_patterns(current_context),
            'learned_from_past': self.find_relevant_learnings(current_context)
        }
        
        return suggestions
    
    def explain_reasoning(self, memory_id):
        """Trace back through consolidation layers"""
        
        # Show the journey from raw thought to wisdom
        trace = {
            'original': self.get_raw_memory(memory_id),
            'daily_consolidation': self.get_daily_containing(memory_id),
            'weekly_pattern': self.get_pattern_containing(memory_id),
            'knowledge_node': self.get_knowledge_containing(memory_id),
            'derived_wisdom': self.get_wisdom_from(memory_id)
        }
        
        return trace
```

## Benefits of Consolidation

### 1. **Storage Efficiency**
- Raw memories can be pruned after consolidation
- Keep insights, not every detail
- Compressed long-term storage

### 2. **Better Retrieval**
- Search at the right level of abstraction
- Find patterns, not just instances
- Surface wisdom when relevant

### 3. **Continuous Learning**
- System gets smarter over time
- Learns your patterns and preferences
- Builds personalized knowledge base

### 4. **Cognitive Alignment**
- Mimics human memory consolidation
- Natural forgetting of irrelevant details
- Strengthening of important patterns

### 5. **Proactive Intelligence**
- Surface relevant wisdom automatically
- Remind you of learned lessons
- Prevent repeated mistakes

## Implementation Timeline

### Phase 1: Daily Consolidation (Week 3)
- Basic daily summary generation
- Extract key decisions and themes
- Simple narrative creation

### Phase 2: Pattern Recognition (Week 4)
- Weekly pattern identification
- Productivity analysis
- Basic recommendations

### Phase 3: Knowledge Synthesis (Month 2)
- Knowledge node creation
- Semantic clustering
- Basic knowledge graph

### Phase 4: Wisdom Extraction (Month 3)
- Principle formulation
- Heuristic extraction
- Intelligent forgetting

## Success Metrics

- **Consolidation Quality**: 90% of important decisions captured
- **Pattern Recognition**: Identify 80% of recurring themes
- **Knowledge Synthesis**: Create useful nodes from 70% of clusters
- **Storage Reduction**: 50% reduction after 90 days (keeping insights)
- **Wisdom Application**: Surface relevant wisdom 75% of the time

## Conclusion

By implementing memory consolidation, the system becomes a true thinking partner that not only remembers but also learns, recognizes patterns, and builds wisdom over time. This transforms it from a passive memory store into an active knowledge synthesis system that gets more valuable the longer you use it.