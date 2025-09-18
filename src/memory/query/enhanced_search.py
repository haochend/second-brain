"""Enhanced query interface for multi-level memory retrieval"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from enum import Enum
from ..storage import Database, Memory
from ..embeddings import EmbeddingGenerator, VectorStore
from ..consolidation.knowledge import KnowledgeSynthesizer


class QueryType(Enum):
    """Types of queries based on intent"""
    SPECIFIC_RECENT = "specific_recent"      # Looking for specific recent memory
    PATTERN_SEEKING = "pattern_seeking"      # Looking for patterns over time
    CONCEPTUAL = "conceptual"               # Looking for knowledge/concepts
    TEMPORAL = "temporal"                   # Looking for time-based info
    TASK_RELATED = "task_related"          # Looking for tasks/actions
    PERSON_RELATED = "person_related"       # Looking for people interactions
    WISDOM_SEEKING = "wisdom_seeking"       # Looking for principles/lessons


class EnhancedQueryInterface:
    """Query across all memory levels intelligently"""
    
    def __init__(self, 
                 db: Optional[Database] = None,
                 vector_store: Optional[VectorStore] = None,
                 embedding_generator: Optional[EmbeddingGenerator] = None):
        """Initialize enhanced query interface"""
        self.db = db or Database()
        self.vector_store = vector_store or VectorStore()
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.knowledge_synthesizer = KnowledgeSynthesizer(db=self.db, vector_store=self.vector_store)
    
    def query(self, natural_query: str, limit: int = 20) -> Dict[str, Any]:
        """Route query to appropriate memory level and return structured results"""
        # Classify the query type
        query_type = self._classify_query(natural_query)
        
        print(f"🔍 Query type: {query_type.value}")
        
        # Route to appropriate search method
        if query_type == QueryType.SPECIFIC_RECENT:
            results = self._search_raw_memories(natural_query, limit)
            
        elif query_type == QueryType.PATTERN_SEEKING:
            patterns = self._search_patterns(natural_query)
            wisdom = self._search_wisdom(natural_query)
            results = self._combine_pattern_results(patterns, wisdom)
            
        elif query_type == QueryType.CONCEPTUAL:
            results = self._search_knowledge_graph(natural_query, limit)
            
        elif query_type == QueryType.TEMPORAL:
            results = self._search_consolidations(natural_query)
            
        elif query_type == QueryType.TASK_RELATED:
            results = self._search_tasks(natural_query)
            
        elif query_type == QueryType.PERSON_RELATED:
            results = self._search_people_interactions(natural_query)
            
        elif query_type == QueryType.WISDOM_SEEKING:
            results = self._search_wisdom_directly(natural_query)
            
        else:
            # Federated search across all levels
            results = self._federated_search(natural_query, limit)
        
        # Add context-aware suggestions
        results['suggestions'] = self._get_context_aware_suggestions(natural_query)
        
        return results
    
    def _classify_query(self, query: str) -> QueryType:
        """Classify the type of query based on keywords and patterns"""
        query_lower = query.lower()
        
        # Task-related keywords
        if any(word in query_lower for word in ['task', 'todo', 'action', 'need to', 'must', 'should']):
            return QueryType.TASK_RELATED
        
        # Person-related keywords
        if any(word in query_lower for word in ['who', 'person', 'people', 'meeting', 'talk', 'conversation']):
            return QueryType.PERSON_RELATED
        
        # Pattern-seeking keywords
        if any(word in query_lower for word in ['pattern', 'trend', 'usually', 'often', 'recurring', 'habit']):
            return QueryType.PATTERN_SEEKING
        
        # Wisdom-seeking keywords
        if any(word in query_lower for word in ['lesson', 'learned', 'principle', 'wisdom', 'insight', 'rule']):
            return QueryType.WISDOM_SEEKING
        
        # Temporal keywords
        if any(word in query_lower for word in ['yesterday', 'today', 'last week', 'this week', 'when', 'timeline']):
            return QueryType.TEMPORAL
        
        # Conceptual keywords
        if any(word in query_lower for word in ['concept', 'idea', 'knowledge', 'understand', 'explain', 'what is']):
            return QueryType.CONCEPTUAL
        
        # Default to specific recent
        return QueryType.SPECIFIC_RECENT
    
    def _search_raw_memories(self, query: str, limit: int) -> Dict[str, Any]:
        """Search raw memories using both FTS and vector search"""
        results = {
            'type': 'raw_memories',
            'keyword_results': [],
            'semantic_results': []
        }
        
        # Keyword search
        keyword_memories = self.db.search_memories(query, limit)
        results['keyword_results'] = [self._format_memory(m) for m in keyword_memories]
        
        # Semantic search
        try:
            embedding = self.embedding_generator.generate(query)
            semantic_results = self.vector_store.search(embedding, k=limit)
            
            semantic_memories = []
            for result in semantic_results:
                memory = self.db.get_memory_by_uuid(result['id'])
                if memory:
                    formatted = self._format_memory(memory)
                    formatted['relevance_score'] = result.get('distance', 0)
                    semantic_memories.append(formatted)
            
            results['semantic_results'] = semantic_memories
        except Exception as e:
            print(f"Semantic search failed: {e}")
        
        # Merge and rank results
        results['merged'] = self._merge_and_rank(results['keyword_results'], results['semantic_results'])
        
        return results
    
    def _search_patterns(self, query: str) -> List[Dict]:
        """Search for patterns in weekly consolidations"""
        patterns = []
        
        # Search weekly patterns
        query_sql = """
            SELECT * FROM weekly_patterns
            WHERE insights LIKE ? 
            OR json_extract(patterns, '$') LIKE ?
            ORDER BY created_at DESC
            LIMIT 10
        """
        
        search_pattern = f"%{query}%"
        cursor = self.db.conn.execute(query_sql, (search_pattern, search_pattern))
        
        for row in cursor:
            data = dict(row)
            # Parse JSON fields
            for field in ['patterns', 'recurring_themes', 'recommendations']:
                if data.get(field):
                    try:
                        data[field] = json.loads(data[field])
                    except:
                        pass
            patterns.append(data)
        
        return patterns
    
    def _search_wisdom(self, query: str) -> List[Dict]:
        """Search wisdom and principles"""
        query_sql = """
            SELECT * FROM wisdom
            WHERE content LIKE ? OR context LIKE ?
            ORDER BY confidence DESC, evidence_count DESC
            LIMIT 10
        """
        
        search_pattern = f"%{query}%"
        cursor = self.db.conn.execute(query_sql, (search_pattern, search_pattern))
        
        return [dict(row) for row in cursor]
    
    def _combine_pattern_results(self, patterns: List[Dict], wisdom: List[Dict]) -> Dict[str, Any]:
        """Combine pattern and wisdom results"""
        return {
            'type': 'patterns_and_wisdom',
            'patterns': patterns,
            'wisdom': wisdom,
            'summary': self._generate_pattern_summary(patterns, wisdom)
        }
    
    def _generate_pattern_summary(self, patterns: List[Dict], wisdom: List[Dict]) -> str:
        """Generate a summary of patterns and wisdom"""
        summary_parts = []
        
        if patterns:
            summary_parts.append(f"Found {len(patterns)} relevant patterns")
            
            # Extract key insights
            for pattern in patterns[:3]:
                if pattern.get('insights'):
                    summary_parts.append(f"Pattern: {pattern['insights'][:100]}...")
        
        if wisdom:
            summary_parts.append(f"Found {len(wisdom)} wisdom items")
            
            # Show top wisdom
            for w in wisdom[:3]:
                summary_parts.append(f"Wisdom: {w['content'][:80]}...")
        
        return " | ".join(summary_parts) if summary_parts else "No patterns or wisdom found"
    
    def _search_knowledge_graph(self, query: str, limit: int) -> Dict[str, Any]:
        """Search knowledge nodes and their relationships"""
        results = {
            'type': 'knowledge_graph',
            'nodes': [],
            'edges': []
        }
        
        # Search knowledge nodes
        query_sql = """
            SELECT * FROM knowledge_nodes
            WHERE topic LIKE ? OR summary LIKE ?
            ORDER BY confidence DESC, times_referenced DESC
            LIMIT ?
        """
        
        search_pattern = f"%{query}%"
        cursor = self.db.conn.execute(query_sql, (search_pattern, search_pattern, limit))
        
        node_ids = []
        for row in cursor:
            node = dict(row)
            node_ids.append(node['id'])
            
            # Parse JSON fields
            for field in ['insights', 'decisions', 'questions', 'connections']:
                if node.get(field):
                    try:
                        node[field] = json.loads(node[field])
                    except:
                        pass
            
            results['nodes'].append(node)
        
        # Get edges for found nodes
        if node_ids:
            placeholders = ','.join('?' * len(node_ids))
            edge_query = f"""
                SELECT * FROM knowledge_edges
                WHERE from_node_id IN ({placeholders})
                OR to_node_id IN ({placeholders})
            """
            
            cursor = self.db.conn.execute(edge_query, node_ids + node_ids)
            results['edges'] = [dict(row) for row in cursor]
        
        return results
    
    def _search_consolidations(self, query: str) -> Dict[str, Any]:
        """Search daily consolidations for temporal queries"""
        results = {
            'type': 'daily_consolidations',
            'consolidations': []
        }
        
        # Parse temporal references
        days_back = self._parse_temporal_reference(query)
        
        if days_back is not None:
            cutoff = (datetime.now() - timedelta(days=days_back)).date().isoformat()
            query_sql = """
                SELECT * FROM daily_consolidations
                WHERE date >= ?
                ORDER BY date DESC
            """
            cursor = self.db.conn.execute(query_sql, (cutoff,))
        else:
            # General search in consolidations
            query_sql = """
                SELECT * FROM daily_consolidations
                WHERE narrative LIKE ?
                OR json_extract(main_topics, '$') LIKE ?
                ORDER BY date DESC
                LIMIT 10
            """
            search_pattern = f"%{query}%"
            cursor = self.db.conn.execute(query_sql, (search_pattern, search_pattern))
        
        for row in cursor:
            consolidation = dict(row)
            # Parse JSON fields
            for field in ['key_decisions', 'main_topics', 'emotional_arc', 'insights']:
                if consolidation.get(field):
                    try:
                        consolidation[field] = json.loads(consolidation[field])
                    except:
                        pass
            results['consolidations'].append(consolidation)
        
        return results
    
    def _parse_temporal_reference(self, query: str) -> Optional[int]:
        """Parse temporal references in query to days back"""
        query_lower = query.lower()
        
        if 'yesterday' in query_lower:
            return 1
        elif 'today' in query_lower:
            return 0
        elif 'last week' in query_lower:
            return 7
        elif 'this week' in query_lower:
            return datetime.now().weekday()
        elif 'last month' in query_lower:
            return 30
        
        return None
    
    def _search_tasks(self, query: str) -> Dict[str, Any]:
        """Search for tasks and actionable items"""
        results = {
            'type': 'tasks',
            'active_tasks': [],
            'completed_tasks': []
        }
        
        # Search active tasks
        active_query = """
            SELECT * FROM memories
            WHERE json_extract(extracted_data, '$.actionable') = 1
            AND (json_extract(extracted_data, '$.completed') IS NULL 
                 OR json_extract(extracted_data, '$.completed') = 0)
            AND (raw_text LIKE ? OR summary LIKE ?)
            ORDER BY 
                CASE json_extract(extracted_data, '$.urgency')
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    ELSE 3
                END,
                timestamp DESC
        """
        
        search_pattern = f"%{query}%" if query else "%"
        cursor = self.db.conn.execute(active_query, (search_pattern, search_pattern))
        results['active_tasks'] = [self._format_memory(Memory.from_row(row)) for row in cursor]
        
        # Search completed tasks
        completed_query = """
            SELECT * FROM memories
            WHERE json_extract(extracted_data, '$.completed') = 1
            AND (raw_text LIKE ? OR summary LIKE ?)
            ORDER BY timestamp DESC
            LIMIT 10
        """
        
        cursor = self.db.conn.execute(completed_query, (search_pattern, search_pattern))
        results['completed_tasks'] = [self._format_memory(Memory.from_row(row)) for row in cursor]
        
        return results
    
    def _search_people_interactions(self, query: str) -> Dict[str, Any]:
        """Search for people-related memories"""
        results = {
            'type': 'people_interactions',
            'interactions': [],
            'people_summary': {}
        }
        
        # Extract person name from query if present
        person_name = self._extract_person_name(query)
        
        if person_name:
            # Search for specific person
            query_sql = """
                SELECT * FROM memories
                WHERE json_extract(extracted_data, '$.people') LIKE ?
                AND status = 'completed'
                ORDER BY timestamp DESC
            """
            search_pattern = f"%{person_name}%"
        else:
            # General people search
            query_sql = """
                SELECT * FROM memories
                WHERE json_extract(extracted_data, '$.people') IS NOT NULL
                AND (raw_text LIKE ? OR summary LIKE ?)
                AND status = 'completed'
                ORDER BY timestamp DESC
                LIMIT 20
            """
            search_pattern = f"%{query}%"
            
        cursor = self.db.conn.execute(query_sql, 
                                     (search_pattern,) if person_name else (search_pattern, search_pattern))
        
        # Process results
        people_counts = {}
        for row in cursor:
            memory = Memory.from_row(row)
            formatted = self._format_memory(memory)
            results['interactions'].append(formatted)
            
            # Count people mentions
            if memory.extracted_data and memory.extracted_data.get('people'):
                for person in memory.extracted_data['people']:
                    people_counts[person] = people_counts.get(person, 0) + 1
        
        # Create people summary
        results['people_summary'] = {
            'total_people': len(people_counts),
            'top_interactions': sorted(people_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        }
        
        return results
    
    def _extract_person_name(self, query: str) -> Optional[str]:
        """Try to extract a person's name from the query"""
        # Simple heuristic - look for capitalized words after certain keywords
        import re
        
        patterns = [
            r'about ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'with ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'from ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                name = match.group(1)
                # Filter out common words that might be capitalized
                if name.lower() not in ['the', 'a', 'an', 'and', 'or', 'but']:
                    return name
        
        return None
    
    def _search_wisdom_directly(self, query: str) -> Dict[str, Any]:
        """Search wisdom with context"""
        wisdom_items = self._search_wisdom(query)
        
        return {
            'type': 'wisdom',
            'items': wisdom_items,
            'applicable_now': self._find_applicable_wisdom(query)
        }
    
    def _find_applicable_wisdom(self, context: str) -> List[Dict]:
        """Find wisdom applicable to current context"""
        return self.knowledge_synthesizer.get_relevant_wisdom(context)
    
    def _federated_search(self, query: str, limit: int) -> Dict[str, Any]:
        """Search everything and combine results"""
        results = {
            'type': 'federated',
            'memories': self._search_raw_memories(query, limit//2),
            'patterns': self._search_patterns(query)[:3],
            'knowledge': self._search_knowledge_graph(query, limit//4),
            'wisdom': self._search_wisdom(query)[:3],
            'tasks': self._search_tasks(query) if 'task' in query.lower() else None
        }
        
        # Remove empty results
        results = {k: v for k, v in results.items() if v}
        
        return results
    
    def _get_context_aware_suggestions(self, query: str) -> List[str]:
        """Get proactive suggestions based on query context"""
        suggestions = []
        
        # Get current context
        current_hour = datetime.now().hour
        current_day = datetime.now().strftime('%A')
        
        # Time-based suggestions
        if 8 <= current_hour <= 10:
            suggestions.append("Check morning tasks and priorities")
        elif 14 <= current_hour <= 16:
            suggestions.append("Review afternoon progress")
        elif current_hour >= 20:
            suggestions.append("Reflect on today's accomplishments")
        
        # Day-based suggestions
        if current_day == 'Monday':
            suggestions.append("Review last week's patterns")
        elif current_day == 'Friday':
            suggestions.append("Plan for next week based on patterns")
        
        # Query-based suggestions
        query_lower = query.lower()
        if 'stress' in query_lower or 'anxious' in query_lower:
            suggestions.append("Review stress patterns and coping strategies")
        elif 'productive' in query_lower:
            suggestions.append("Check your peak productivity hours")
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    def _format_memory(self, memory: Memory) -> Dict[str, Any]:
        """Format memory for output"""
        return {
            'id': memory.uuid,
            'timestamp': memory.timestamp.isoformat() if memory.timestamp else None,
            'type': memory.thought_type,
            'summary': memory.summary or memory.raw_text[:100],
            'raw_text': memory.raw_text,
            'source': memory.source,
            'extracted_data': memory.extracted_data,
            'status': memory.status
        }
    
    def _merge_and_rank(self, keyword_results: List[Dict], semantic_results: List[Dict]) -> List[Dict]:
        """Merge and rank results from different search methods"""
        # Create a dict to track seen memories
        seen = {}
        merged = []
        
        # Process semantic results first (usually more relevant)
        for result in semantic_results:
            memory_id = result['id']
            if memory_id not in seen:
                result['search_method'] = 'semantic'
                merged.append(result)
                seen[memory_id] = True
        
        # Add keyword results not in semantic
        for result in keyword_results:
            memory_id = result['id']
            if memory_id not in seen:
                result['search_method'] = 'keyword'
                merged.append(result)
                seen[memory_id] = True
        
        return merged
    
    def explain_reasoning(self, memory_id: str) -> Dict[str, Any]:
        """Trace back through consolidation layers for a memory"""
        trace = {
            'memory_id': memory_id,
            'layers': {}
        }
        
        # Get original memory
        memory = self.db.get_memory_by_uuid(memory_id)
        if memory:
            trace['layers']['original'] = self._format_memory(memory)
        
        # Find daily consolidation containing this memory
        query = """
            SELECT * FROM daily_consolidations
            WHERE json_extract(source_memory_ids, '$') LIKE ?
            ORDER BY date DESC
            LIMIT 1
        """
        cursor = self.db.conn.execute(query, (f"%{memory_id}%",))
        row = cursor.fetchone()
        if row:
            trace['layers']['daily_consolidation'] = dict(row)
        
        # Find weekly pattern
        if trace['layers'].get('daily_consolidation'):
            date = trace['layers']['daily_consolidation']['date']
            week_query = """
                SELECT * FROM weekly_patterns
                WHERE json_extract(source_consolidation_ids, '$') LIKE ?
                LIMIT 1
            """
            # This would need the consolidation ID, simplified for now
            
        # Find knowledge node
        node_query = """
            SELECT * FROM knowledge_nodes
            WHERE json_extract(source_memory_ids, '$') LIKE ?
            LIMIT 1
        """
        cursor = self.db.conn.execute(node_query, (f"%{memory_id}%",))
        row = cursor.fetchone()
        if row:
            trace['layers']['knowledge_node'] = dict(row)
        
        # Find derived wisdom
        # This would trace through knowledge nodes to wisdom
        
        return trace