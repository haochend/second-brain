"""Knowledge synthesis and wisdom extraction"""

import json
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter
from sklearn.cluster import DBSCAN
from ..storage import Database, Memory
from ..processing.extraction import LLMExtractor
from ..embeddings import EmbeddingGenerator, VectorStore


class KnowledgeSynthesizer:
    """Transform scattered thoughts into structured knowledge and wisdom"""
    
    def __init__(self, 
                 db: Optional[Database] = None, 
                 extractor: Optional[LLMExtractor] = None,
                 embedding_generator: Optional[EmbeddingGenerator] = None,
                 vector_store: Optional[VectorStore] = None):
        """Initialize knowledge synthesizer"""
        self.db = db or Database()
        self.extractor = extractor or LLMExtractor()
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.vector_store = vector_store or VectorStore()
    
    def build_knowledge_nodes(self, days: int = 30) -> List[Dict]:
        """Build knowledge nodes from recent memories"""
        print(f"Building knowledge nodes from last {days} days...")
        
        # Get recent memories
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        query = """
            SELECT * FROM memories
            WHERE timestamp > ?
            AND status = 'completed'
            ORDER BY timestamp DESC
        """
        cursor = self.db.conn.execute(query, (cutoff,))
        memories = [Memory.from_row(row) for row in cursor]
        
        if not memories:
            print("No memories found for knowledge synthesis")
            return []
        
        print(f"Clustering {len(memories)} memories...")
        
        # Cluster memories by semantic similarity
        clusters = self._cluster_memories_semantically(memories)
        
        # Create knowledge nodes from coherent clusters
        knowledge_nodes = []
        for cluster in clusters:
            if cluster['coherence'] > 0.7:  # Strong theme
                node = self._create_knowledge_node(cluster)
                if node:
                    knowledge_nodes.append(node)
                    self._store_knowledge_node(node)
        
        # Link knowledge nodes
        self._link_knowledge_nodes(knowledge_nodes)
        
        print(f"✓ Created {len(knowledge_nodes)} knowledge nodes")
        return knowledge_nodes
    
    def _cluster_memories_semantically(self, memories: List[Memory]) -> List[Dict]:
        """Cluster memories by semantic similarity"""
        # Get embeddings for all memories
        embeddings = []
        valid_memories = []
        
        for memory in memories:
            try:
                # Get embedding from vector store
                results = self.vector_store.collection.get(
                    ids=[memory.uuid],
                    include=['embeddings']
                )
                
                if results and results['embeddings']:
                    embeddings.append(results['embeddings'][0])
                    valid_memories.append(memory)
            except:
                # Generate embedding if not in store
                try:
                    text = memory.summary or memory.raw_text[:500]
                    embedding = self.embedding_generator.generate(text)
                    embeddings.append(embedding)
                    valid_memories.append(memory)
                except:
                    pass
        
        if len(embeddings) < 2:
            return []
        
        # Use DBSCAN clustering
        embeddings_array = np.array(embeddings)
        clustering = DBSCAN(eps=0.3, min_samples=2, metric='cosine').fit(embeddings_array)
        
        # Group memories by cluster
        clusters = {}
        for idx, label in enumerate(clustering.labels_):
            if label != -1:  # Ignore noise points
                if label not in clusters:
                    clusters[label] = {
                        'memories': [],
                        'memory_ids': [],
                        'embeddings': []
                    }
                clusters[label]['memories'].append(valid_memories[idx])
                clusters[label]['memory_ids'].append(valid_memories[idx].uuid)
                clusters[label]['embeddings'].append(embeddings[idx])
        
        # Calculate cluster properties
        cluster_list = []
        for label, cluster_data in clusters.items():
            # Calculate coherence (average similarity within cluster)
            if len(cluster_data['embeddings']) > 1:
                similarities = []
                for i in range(len(cluster_data['embeddings'])):
                    for j in range(i+1, len(cluster_data['embeddings'])):
                        sim = np.dot(cluster_data['embeddings'][i], cluster_data['embeddings'][j])
                        similarities.append(sim)
                coherence = np.mean(similarities) if similarities else 0
            else:
                coherence = 0.8  # Single item clusters are coherent by definition
            
            # Extract common topics
            all_topics = []
            all_people = []
            all_projects = []
            
            for memory in cluster_data['memories']:
                if memory.extracted_data:
                    all_topics.extend(memory.extracted_data.get('topics', []))
                    all_people.extend(memory.extracted_data.get('people', []))
                    all_projects.extend(memory.extracted_data.get('projects', []))
            
            # Find primary topic
            topic_counts = Counter(all_topics)
            primary_topic = topic_counts.most_common(1)[0][0] if topic_counts else 'general'
            
            cluster_list.append({
                'memories': cluster_data['memories'],
                'memory_ids': cluster_data['memory_ids'],
                'coherence': coherence,
                'primary_topic': primary_topic,
                'topics': list(set(all_topics)),
                'people': list(set(all_people)),
                'projects': list(set(all_projects))
            })
        
        return sorted(cluster_list, key=lambda x: x['coherence'], reverse=True)
    
    def _create_knowledge_node(self, cluster: Dict) -> Optional[Dict]:
        """Transform a cluster into structured knowledge"""
        if len(cluster['memories']) < 2:
            return None  # Need at least 2 memories for synthesis
        
        # Prepare memories for synthesis
        memory_texts = []
        for mem in cluster['memories'][:20]:  # Limit to prevent huge prompts
            summary = mem.summary or mem.raw_text[:200]
            memory_texts.append(f"- {summary}")
        
        prompt = f"""
        These related thoughts all discuss similar topics:
        {chr(10).join(memory_texts)}
        
        Topics involved: {', '.join(cluster['topics'][:10])}
        People mentioned: {', '.join(cluster['people'][:5]) if cluster['people'] else 'None'}
        
        Create a structured knowledge summary:
        1. core_concept: What is the central theme or concept?
        2. key_insights: What are the main insights learned? (list)
        3. decisions: What decisions were made about this? (list)
        4. open_questions: What questions remain? (list)
        5. practical_applications: How can this knowledge be applied? (list)
        6. relationships: How does this relate to other concepts?
        
        Return as JSON with these exact fields.
        """
        
        try:
            synthesis = self.extractor.extract(prompt)
            
            # Ensure all required fields exist
            node = {
                'id': None,  # Will be set by database
                'type': 'knowledge_node',
                'topic': cluster['primary_topic'],
                'summary': synthesis.get('core_concept', cluster['primary_topic']),
                'insights': synthesis.get('key_insights', []),
                'decisions': synthesis.get('decisions', []),
                'questions': synthesis.get('open_questions', []),
                'applications': synthesis.get('practical_applications', []),
                'connections': {
                    'people': cluster['people'],
                    'projects': cluster['projects'],
                    'topics': cluster['topics'],
                    'related_nodes': []  # Will be filled by linking
                },
                'source_memory_ids': cluster['memory_ids'],
                'confidence': cluster['coherence'],
                'times_referenced': 0,
                'last_referenced': datetime.now(),
                'created_at': datetime.now()
            }
            
            return node
            
        except Exception as e:
            print(f"Failed to synthesize knowledge node: {e}")
            return None
    
    def _store_knowledge_node(self, node: Dict):
        """Store a knowledge node in the database"""
        query = """
            INSERT INTO knowledge_nodes (
                topic, summary, insights, decisions, questions,
                connections, source_memory_ids, confidence,
                times_referenced, last_referenced
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        values = (
            node['topic'],
            node['summary'],
            json.dumps(node['insights']),
            json.dumps(node['decisions']),
            json.dumps(node['questions']),
            json.dumps(node['connections']),
            json.dumps(node['source_memory_ids']),
            node['confidence'],
            node['times_referenced'],
            node['last_referenced'].isoformat() if isinstance(node['last_referenced'], datetime) else node['last_referenced']
        )
        
        cursor = self.db.conn.execute(query, values)
        self.db.conn.commit()
        node['id'] = cursor.lastrowid
    
    def _link_knowledge_nodes(self, nodes: List[Dict]):
        """Build relationships between knowledge nodes"""
        for i, node1 in enumerate(nodes):
            for j, node2 in enumerate(nodes):
                if i >= j:  # Skip self and already processed pairs
                    continue
                
                # Calculate relationship strength
                relationship = self._determine_relationship(node1, node2)
                
                if relationship['strength'] > 0.3:  # Meaningful relationship
                    self._create_knowledge_edge(node1, node2, relationship)
    
    def _determine_relationship(self, node1: Dict, node2: Dict) -> Dict:
        """Determine the relationship between two knowledge nodes"""
        # Check topic overlap
        topics1 = set(node1['connections']['topics'])
        topics2 = set(node2['connections']['topics'])
        topic_overlap = len(topics1 & topics2) / max(len(topics1 | topics2), 1)
        
        # Check people overlap
        people1 = set(node1['connections']['people'])
        people2 = set(node2['connections']['people'])
        people_overlap = len(people1 & people2) / max(len(people1 | people2), 1) if (people1 or people2) else 0
        
        # Check question-answer relationships
        questions1 = set(node1.get('questions', []))
        insights2 = set(node2.get('insights', []))
        qa_relationship = 0.5 if any(q in str(insights2) for q in questions1) else 0
        
        # Calculate overall strength
        strength = (topic_overlap * 0.5 + people_overlap * 0.3 + qa_relationship * 0.2)
        
        # Determine relationship type
        if qa_relationship > 0:
            rel_type = 'answers'
        elif people_overlap > 0.5:
            rel_type = 'same_people'
        elif topic_overlap > 0.7:
            rel_type = 'same_topic'
        elif topic_overlap > 0.3:
            rel_type = 'related_topic'
        else:
            rel_type = 'associated'
        
        return {
            'type': rel_type,
            'strength': strength
        }
    
    def _create_knowledge_edge(self, node1: Dict, node2: Dict, relationship: Dict):
        """Create an edge in the knowledge graph"""
        if not node1.get('id') or not node2.get('id'):
            return  # Need IDs to create edge
        
        query = """
            INSERT INTO knowledge_edges (
                from_node_id, to_node_id, relationship_type, strength
            ) VALUES (?, ?, ?, ?)
        """
        
        self.db.conn.execute(query, (
            node1['id'],
            node2['id'],
            relationship['type'],
            relationship['strength']
        ))
        self.db.conn.commit()
        
        # Update nodes' related_nodes
        node1['connections']['related_nodes'].append(node2['id'])
        node2['connections']['related_nodes'].append(node1['id'])
    
    def extract_wisdom(self, months: int = 3) -> List[Dict]:
        """Extract learned principles and patterns over time"""
        print(f"Extracting wisdom from last {months} months...")
        
        # Get all patterns from the period
        cutoff = (datetime.now() - timedelta(days=months*30)).isoformat()
        
        # Get weekly patterns
        query = """
            SELECT * FROM weekly_patterns
            WHERE created_at > ?
            ORDER BY year DESC, week_number DESC
        """
        cursor = self.db.conn.execute(query, (cutoff,))
        weekly_patterns = []
        for row in cursor:
            data = dict(row)
            # Parse JSON fields
            for field in ['patterns', 'recurring_themes', 'productivity_patterns', 'success_patterns']:
                if data.get(field):
                    try:
                        data[field] = json.loads(data[field])
                    except:
                        pass
            weekly_patterns.append(data)
        
        # Get knowledge nodes
        query = """
            SELECT * FROM knowledge_nodes
            WHERE created_at > ?
            AND confidence > 0.7
            ORDER BY confidence DESC
        """
        cursor = self.db.conn.execute(query, (cutoff,))
        knowledge_nodes = []
        for row in cursor:
            data = dict(row)
            # Parse JSON fields
            for field in ['insights', 'decisions', 'questions']:
                if data.get(field):
                    try:
                        data[field] = json.loads(data[field])
                    except:
                        pass
            knowledge_nodes.append(data)
        
        wisdom_candidates = []
        
        # Extract principles from consistent patterns
        principles = self._extract_principles(weekly_patterns)
        wisdom_candidates.extend(principles)
        
        # Extract heuristics from successful decisions
        heuristics = self._extract_heuristics(knowledge_nodes, weekly_patterns)
        wisdom_candidates.extend(heuristics)
        
        # Store wisdom
        for wisdom in wisdom_candidates:
            self._store_wisdom(wisdom)
        
        print(f"✓ Extracted {len(wisdom_candidates)} wisdom items")
        return wisdom_candidates
    
    def _extract_principles(self, patterns: List[Dict]) -> List[Dict]:
        """Extract consistent principles from patterns"""
        principles = []
        
        # Look for patterns that appear consistently
        recurring_observations = Counter()
        success_patterns_all = []
        productivity_insights = []
        
        for pattern in patterns:
            # Collect recurring themes
            if pattern.get('recurring_themes'):
                for theme, data in pattern['recurring_themes'].items():
                    if data.get('sentiment') == 'positive':
                        recurring_observations[theme] += 1
            
            # Collect success patterns
            if pattern.get('success_patterns'):
                success_patterns_all.append(pattern['success_patterns'])
            
            # Collect productivity insights
            if pattern.get('productivity_patterns'):
                prod = pattern['productivity_patterns']
                if prod.get('peak_hours'):
                    productivity_insights.append(prod['peak_hours'])
        
        # Formulate principles from consistent observations
        for observation, count in recurring_observations.most_common(5):
            if count >= 3:  # Appears in at least 3 weeks
                principle = self._formulate_principle(observation, patterns)
                if principle:
                    principles.append(principle)
        
        # Extract productivity principle if consistent
        if len(productivity_insights) >= 3:
            # Find most common peak hours
            all_hours = [h for hours in productivity_insights for h in hours[:2]]
            hour_counts = Counter(all_hours)
            if hour_counts:
                top_hours = hour_counts.most_common(2)
                principle = {
                    'type': 'principle',
                    'content': f"Peak productivity occurs at {top_hours[0][0]}:00" + 
                              (f" and {top_hours[1][0]}:00" if len(top_hours) > 1 else ""),
                    'context': 'time_management',
                    'exceptions': 'May vary on weekends or during high-stress periods',
                    'confidence': 0.8,
                    'evidence_count': len(productivity_insights),
                    'learned_date': datetime.now()
                }
                principles.append(principle)
        
        return principles
    
    def _formulate_principle(self, observation: str, patterns: List[Dict]) -> Optional[Dict]:
        """Turn an observation into a principle"""
        # Collect evidence for this observation
        evidence = []
        contexts = []
        
        for pattern in patterns:
            if pattern.get('recurring_themes') and observation in pattern['recurring_themes']:
                evidence.append(pattern['recurring_themes'][observation])
                contexts.append(pattern.get('insights', ''))
        
        if len(evidence) < 3:
            return None
        
        # Use LLM to formulate principle
        prompt = f"""
        This theme/pattern has been observed consistently: "{observation}"
        
        Evidence from multiple weeks:
        {chr(10).join(str(e) for e in evidence[:5])}
        
        Formulate this as a personal principle or rule of thumb.
        Return JSON with:
        - statement: The principle itself (one sentence)
        - applies_when: When this principle applies
        - exceptions: Any exceptions noticed
        """
        
        try:
            result = self.extractor.extract(prompt)
            
            return {
                'type': 'principle',
                'content': result.get('statement', f"Consistent focus on {observation} leads to positive outcomes"),
                'context': result.get('applies_when', observation),
                'exceptions': result.get('exceptions', 'None identified'),
                'confidence': min(len(evidence) / 10, 0.9),
                'evidence_count': len(evidence),
                'learned_date': datetime.now()
            }
        except:
            return None
    
    def _extract_heuristics(self, knowledge_nodes: List[Dict], patterns: List[Dict]) -> List[Dict]:
        """Extract decision-making heuristics"""
        heuristics = []
        
        # Look for repeated successful decision patterns
        decision_patterns = []
        for node in knowledge_nodes:
            if node.get('decisions'):
                for decision in node['decisions']:
                    decision_patterns.append({
                        'decision': decision,
                        'outcome': 'positive' if node['confidence'] > 0.8 else 'mixed',
                        'context': node['topic']
                    })
        
        # Group similar decisions
        decision_groups = {}
        for pattern in decision_patterns:
            # Simple grouping by keywords
            key_words = pattern['decision'].lower().split()[:3]
            key = ' '.join(key_words)
            
            if key not in decision_groups:
                decision_groups[key] = []
            decision_groups[key].append(pattern)
        
        # Extract heuristics from successful patterns
        for key, group in decision_groups.items():
            if len(group) >= 2:  # Repeated pattern
                success_rate = sum(1 for g in group if g['outcome'] == 'positive') / len(group)
                
                if success_rate > 0.7:
                    heuristic = {
                        'type': 'heuristic',
                        'content': f"When facing {key}, follow similar approach as before",
                        'context': 'decision_making',
                        'exceptions': 'Unless context has significantly changed',
                        'confidence': success_rate,
                        'evidence_count': len(group),
                        'success_rate': success_rate,
                        'learned_date': datetime.now()
                    }
                    heuristics.append(heuristic)
        
        return heuristics
    
    def _store_wisdom(self, wisdom: Dict):
        """Store wisdom in database"""
        query = """
            INSERT INTO wisdom (
                type, content, context, exceptions,
                confidence, evidence_count, success_rate, learned_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        values = (
            wisdom['type'],
            wisdom['content'],
            wisdom.get('context', ''),
            wisdom.get('exceptions', ''),
            wisdom.get('confidence', 0.5),
            wisdom.get('evidence_count', 1),
            wisdom.get('success_rate', 0.0),
            wisdom['learned_date'].isoformat() if isinstance(wisdom['learned_date'], datetime) else wisdom['learned_date']
        )
        
        self.db.conn.execute(query, values)
        self.db.conn.commit()
    
    def get_relevant_wisdom(self, context: str) -> List[Dict]:
        """Get wisdom relevant to current context"""
        query = """
            SELECT * FROM wisdom
            WHERE context LIKE ?
            OR content LIKE ?
            ORDER BY confidence DESC, evidence_count DESC
            LIMIT 5
        """
        
        search_pattern = f"%{context}%"
        cursor = self.db.conn.execute(query, (search_pattern, search_pattern))
        
        wisdom_items = []
        for row in cursor:
            wisdom_items.append(dict(row))
        
        return wisdom_items