"""Base consolidator with infrastructure and synthesis separation"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from ..storage import Database, Memory
from ..processing.extraction import LLMExtractor
from ..prompts import PromptManager, ContextDetector


class BaseConsolidator:
    """Base class for all consolidators with two-layer architecture"""
    
    def __init__(self, 
                 db: Optional[Database] = None, 
                 extractor: Optional[LLMExtractor] = None,
                 prompt_manager: Optional[PromptManager] = None):
        """Initialize base consolidator"""
        self.db = db or Database()
        self.extractor = extractor or LLMExtractor()
        self.prompt_manager = prompt_manager or PromptManager()
        self.context_detector = ContextDetector()
    
    def extract_infrastructure(self, memories: List[Memory]) -> Dict[str, Any]:
        """
        Extract infrastructure data (connections, patterns, etc.)
        This runs regardless of user prompts
        
        Args:
            memories: List of Memory objects to analyze
        
        Returns:
            Dictionary containing all infrastructure data
        """
        infrastructure = {
            'memory_count': len(memories),
            'memories': memories,
            'connections': self._find_connections(memories),
            'clusters': self._cluster_by_topic(memories),
            'temporal_patterns': self._extract_temporal_patterns(memories),
            'people': self._extract_people(memories),
            'decisions': self._extract_decisions(memories),
            'questions': self._extract_questions(memories),
            'tasks': self._extract_tasks(memories),
            'emotions': self._extract_emotions(memories),
            'topics': self._extract_topics(memories)
        }
        
        return infrastructure
    
    def synthesize_with_prompt(self, 
                              infrastructure: Dict[str, Any],
                              prompt_type: str,
                              custom_prompt: Optional[str] = None) -> str:
        """
        Generate synthesis using user prompt and infrastructure data
        
        Args:
            infrastructure: Extracted infrastructure data
            prompt_type: Type of prompt (daily, weekly, monthly)
            custom_prompt: Optional custom prompt to use
        
        Returns:
            Synthesized text based on user prompt
        """
        # Detect context for dynamic prompt selection
        context = self.context_detector.analyze_context({
            'memories': infrastructure.get('memories', []),
            'patterns': infrastructure
        })
        
        # Get the appropriate prompt
        if custom_prompt:
            prompt = custom_prompt
        else:
            # Check if we should use a contextual prompt
            if self.context_detector.should_use_contextual_prompt(context):
                prompt = self.prompt_manager.get_prompt('contextual', context=context)
            else:
                prompt = self.prompt_manager.get_prompt(prompt_type)
        
        # Prepare the context for LLM
        synthesis_prompt = self._prepare_synthesis_prompt(infrastructure, prompt)
        
        # Generate synthesis
        try:
            result = self.extractor.extract(synthesis_prompt)
            
            # Extract the synthesis text
            if isinstance(result, dict):
                return result.get('synthesis', result.get('summary', str(result)))
            return str(result)
            
        except Exception as e:
            print(f"Synthesis generation failed: {e}")
            return f"Failed to generate synthesis: {e}"
    
    def _prepare_synthesis_prompt(self, infrastructure: Dict[str, Any], user_prompt: str) -> str:
        """Prepare the full prompt with infrastructure data and user instructions"""
        # Format memories for context
        memory_texts = []
        for i, mem in enumerate(infrastructure.get('memories', [])[:50], 1):  # Limit to 50 for token limits
            summary = mem.summary if hasattr(mem, 'summary') else ''
            raw_text = mem.raw_text if hasattr(mem, 'raw_text') else str(mem)
            text = summary or raw_text[:200]
            memory_texts.append(f"{i}. {text}")
        
        # Format other infrastructure data
        infrastructure_summary = f"""
        Total memories: {infrastructure.get('memory_count', 0)}
        
        Key people: {', '.join(infrastructure.get('people', {}).keys()[:10])}
        Main topics: {', '.join([t['topic'] for t in infrastructure.get('topics', [])[:10]])}
        Decisions made: {len(infrastructure.get('decisions', []))}
        Questions raised: {len(infrastructure.get('questions', []))}
        Tasks identified: {len(infrastructure.get('tasks', []))}
        
        Connections found: {len(infrastructure.get('connections', []))}
        Topic clusters: {len(infrastructure.get('clusters', {}))}
        """
        
        # Combine everything
        full_prompt = f"""
        Analyze these memories and their patterns according to the user's instructions.
        
        MEMORIES:
        {chr(10).join(memory_texts)}
        
        INFRASTRUCTURE DATA:
        {infrastructure_summary}
        
        DETAILED PATTERNS:
        - Decisions: {json.dumps(infrastructure.get('decisions', [])[:10], indent=2)}
        - Questions: {json.dumps(infrastructure.get('questions', [])[:10], indent=2)}
        - Emotional patterns: {json.dumps(infrastructure.get('emotions', {}), indent=2)}
        
        USER'S SYNTHESIS INSTRUCTIONS:
        {user_prompt}
        
        Generate your synthesis based on the user's instructions above.
        """
        
        return full_prompt
    
    def _find_connections(self, memories: List[Memory]) -> List[Dict[str, Any]]:
        """Find connections between memories"""
        connections = []
        
        # Simple connection finding based on shared entities
        for i, mem1 in enumerate(memories):
            for j, mem2 in enumerate(memories[i+1:], i+1):
                connection_strength = 0
                connection_type = []
                
                # Check for shared people
                if hasattr(mem1, 'extracted_data') and hasattr(mem2, 'extracted_data'):
                    data1 = mem1.extracted_data or {}
                    data2 = mem2.extracted_data or {}
                    
                    people1 = set(data1.get('people', []))
                    people2 = set(data2.get('people', []))
                    if people1 & people2:
                        connection_strength += 1
                        connection_type.append('shared_people')
                    
                    # Check for shared topics
                    topics1 = set(data1.get('topics', []))
                    topics2 = set(data2.get('topics', []))
                    if topics1 & topics2:
                        connection_strength += 1
                        connection_type.append('shared_topics')
                
                # Store strong connections
                if connection_strength > 0:
                    connections.append({
                        'from': i,
                        'to': j,
                        'strength': connection_strength,
                        'types': connection_type
                    })
        
        return connections
    
    def _cluster_by_topic(self, memories: List[Memory]) -> Dict[str, List[int]]:
        """Cluster memories by topic"""
        clusters = {}
        
        for i, memory in enumerate(memories):
            if hasattr(memory, 'extracted_data') and memory.extracted_data:
                topics = memory.extracted_data.get('topics', [])
                for topic in topics:
                    if topic not in clusters:
                        clusters[topic] = []
                    clusters[topic].append(i)
        
        return clusters
    
    def _extract_temporal_patterns(self, memories: List[Memory]) -> Dict[str, Any]:
        """Extract temporal patterns from memories"""
        patterns = {
            'hourly_distribution': {},
            'day_distribution': {},
            'gaps': []
        }
        
        last_time = None
        for memory in memories:
            if hasattr(memory, 'timestamp') and memory.timestamp:
                # Hour distribution
                hour = memory.timestamp.hour
                patterns['hourly_distribution'][hour] = patterns['hourly_distribution'].get(hour, 0) + 1
                
                # Day distribution
                day = memory.timestamp.strftime('%A')
                patterns['day_distribution'][day] = patterns['day_distribution'].get(day, 0) + 1
                
                # Gaps
                if last_time:
                    gap_minutes = (memory.timestamp - last_time).total_seconds() / 60
                    if gap_minutes > 60:  # More than 1 hour gap
                        patterns['gaps'].append({
                            'start': last_time.isoformat(),
                            'end': memory.timestamp.isoformat(),
                            'duration_minutes': gap_minutes
                        })
                
                last_time = memory.timestamp
        
        return patterns
    
    def _extract_people(self, memories: List[Memory]) -> Dict[str, Any]:
        """Extract people mentions and interactions"""
        people = {}
        
        for memory in memories:
            if hasattr(memory, 'extracted_data') and memory.extracted_data:
                for person in memory.extracted_data.get('people', []):
                    if person not in people:
                        people[person] = {
                            'count': 0,
                            'contexts': [],
                            'timestamps': []
                        }
                    
                    people[person]['count'] += 1
                    
                    # Add context
                    summary = memory.summary if hasattr(memory, 'summary') else None
                    if summary:
                        people[person]['contexts'].append(summary[:100])
                    
                    # Add timestamp
                    if hasattr(memory, 'timestamp') and memory.timestamp:
                        people[person]['timestamps'].append(memory.timestamp.isoformat())
        
        return people
    
    def _extract_decisions(self, memories: List[Memory]) -> List[Dict[str, Any]]:
        """Extract decisions from memories"""
        decisions = []
        
        for memory in memories:
            if hasattr(memory, 'thought_type') and memory.thought_type == 'decision':
                decision = {
                    'decision': memory.summary if hasattr(memory, 'summary') else memory.raw_text[:200],
                    'timestamp': memory.timestamp.isoformat() if hasattr(memory, 'timestamp') and memory.timestamp else None
                }
                decisions.append(decision)
            
            # Also check extracted data
            if hasattr(memory, 'extracted_data') and memory.extracted_data:
                for decision_text in memory.extracted_data.get('decisions', []):
                    decisions.append({
                        'decision': decision_text,
                        'timestamp': memory.timestamp.isoformat() if hasattr(memory, 'timestamp') and memory.timestamp else None
                    })
        
        return decisions
    
    def _extract_questions(self, memories: List[Memory]) -> List[str]:
        """Extract questions from memories"""
        questions = []
        
        for memory in memories:
            if hasattr(memory, 'thought_type') and memory.thought_type == 'question':
                question = memory.summary if hasattr(memory, 'summary') else memory.raw_text[:200]
                questions.append(question)
            
            # Also check extracted data
            if hasattr(memory, 'extracted_data') and memory.extracted_data:
                questions.extend(memory.extracted_data.get('questions', []))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_questions = []
        for q in questions:
            if q not in seen:
                seen.add(q)
                unique_questions.append(q)
        
        return unique_questions
    
    def _extract_tasks(self, memories: List[Memory]) -> List[Dict[str, Any]]:
        """Extract tasks and actionable items"""
        tasks = []
        
        for memory in memories:
            if hasattr(memory, 'extracted_data') and memory.extracted_data:
                if memory.extracted_data.get('actionable'):
                    task = {
                        'task': memory.summary if hasattr(memory, 'summary') else memory.raw_text[:200],
                        'urgency': memory.extracted_data.get('urgency', 'normal'),
                        'completed': memory.extracted_data.get('completed', False),
                        'timestamp': memory.timestamp.isoformat() if hasattr(memory, 'timestamp') and memory.timestamp else None
                    }
                    tasks.append(task)
        
        return tasks
    
    def _extract_emotions(self, memories: List[Memory]) -> Dict[str, Any]:
        """Extract emotional patterns"""
        emotions = {
            'moods': [],
            'mood_counts': {},
            'emotional_journey': []
        }
        
        for memory in memories:
            if hasattr(memory, 'extracted_data') and memory.extracted_data:
                mood = memory.extracted_data.get('mood')
                if mood:
                    emotions['moods'].append(mood)
                    emotions['mood_counts'][mood] = emotions['mood_counts'].get(mood, 0) + 1
                    
                    if hasattr(memory, 'timestamp') and memory.timestamp:
                        emotions['emotional_journey'].append({
                            'mood': mood,
                            'time': memory.timestamp.isoformat()
                        })
        
        return emotions
    
    def _extract_topics(self, memories: List[Memory]) -> List[Dict[str, Any]]:
        """Extract and rank topics"""
        topic_counts = {}
        topic_first_seen = {}
        topic_last_seen = {}
        
        for memory in memories:
            if hasattr(memory, 'extracted_data') and memory.extracted_data:
                for topic in memory.extracted_data.get('topics', []):
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1
                    
                    if hasattr(memory, 'timestamp') and memory.timestamp:
                        if topic not in topic_first_seen:
                            topic_first_seen[topic] = memory.timestamp
                        topic_last_seen[topic] = memory.timestamp
        
        # Convert to sorted list
        topics = []
        for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True):
            topic_info = {
                'topic': topic,
                'count': count
            }
            
            if topic in topic_first_seen and topic in topic_last_seen:
                duration = (topic_last_seen[topic] - topic_first_seen[topic]).total_seconds() / 3600
                topic_info['duration_hours'] = round(duration, 2)
            
            topics.append(topic_info)
        
        return topics