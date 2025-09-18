"""Daily memory consolidation - processes today's thoughts into insights"""

import json
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
from ..storage import Database, Memory
from ..processing.extraction import LLMExtractor


class DailyConsolidator:
    """Process today's thoughts into consolidated insights"""
    
    def __init__(self, db: Optional[Database] = None, extractor: Optional[LLMExtractor] = None):
        """Initialize daily consolidator"""
        self.db = db or Database()
        self.extractor = extractor or LLMExtractor()
    
    def consolidate_day(self, target_date: Optional[date] = None) -> Dict[str, Any]:
        """Process a day's memories into insights"""
        target_date = target_date or datetime.now().date()
        
        # Check if already consolidated
        existing = self._get_existing_consolidation(target_date)
        if existing:
            print(f"Day {target_date} already consolidated")
            return existing
        
        # Get all memories for the date
        memories = self._get_memories_for_date(target_date)
        
        if not memories:
            print(f"No memories found for {target_date}")
            return {}
        
        print(f"Consolidating {len(memories)} memories from {target_date}...")
        
        # Group by threads and topics
        threads = self._identify_thought_threads(memories)
        
        # Extract key elements
        consolidation = {
            'date': target_date.isoformat(),
            'memory_count': len(memories),
            'key_decisions': self._extract_decisions(memories),
            'main_topics': self._extract_topics(memories),
            'emotional_arc': self._analyze_emotional_journey(memories),
            'important_interactions': self._extract_people_interactions(memories),
            'creative_insights': self._extract_ideas(memories),
            'completed_actions': self._get_completed_tasks(memories),
            'open_questions': self._extract_questions(memories),
            'energy_pattern': self._analyze_energy_levels(memories),
            'thought_threads': threads
        }
        
        # Generate narrative summary
        daily_narrative = self._generate_narrative(consolidation)
        
        # Calculate importance score
        importance_score = self._calculate_importance(consolidation)
        
        # Store consolidated memory
        self._store_consolidation({
            'date': target_date,
            'narrative': daily_narrative,
            'key_decisions': consolidation['key_decisions'],
            'main_topics': consolidation['main_topics'],
            'emotional_arc': consolidation['emotional_arc'],
            'interactions': consolidation['important_interactions'],
            'insights': consolidation['creative_insights'],
            'completed_actions': consolidation['completed_actions'],
            'open_questions': consolidation['open_questions'],
            'energy_pattern': consolidation['energy_pattern'],
            'source_memory_ids': [m.uuid for m in memories],
            'importance_score': importance_score
        })
        
        print(f"✓ Daily consolidation complete for {target_date}")
        return consolidation
    
    def _get_existing_consolidation(self, target_date: date) -> Optional[Dict]:
        """Check if consolidation already exists for date"""
        query = "SELECT * FROM daily_consolidations WHERE date = ?"
        cursor = self.db.conn.execute(query, (target_date.isoformat(),))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def _get_memories_for_date(self, target_date: date) -> List[Memory]:
        """Get all memories for a specific date"""
        start = datetime.combine(target_date, datetime.min.time())
        end = datetime.combine(target_date, datetime.max.time())
        
        query = """
            SELECT * FROM memories
            WHERE timestamp BETWEEN ? AND ?
            AND status = 'completed'
            ORDER BY timestamp ASC
        """
        cursor = self.db.conn.execute(query, (start.isoformat(), end.isoformat()))
        return [Memory.from_row(row) for row in cursor]
    
    def _identify_thought_threads(self, memories: List[Memory]) -> List[Dict]:
        """Group memories into coherent thought threads"""
        threads = []
        current_thread = []
        last_time = None
        
        for memory in memories:
            # If more than 30 minutes gap, start new thread
            if last_time and memory.timestamp:
                gap = (memory.timestamp - last_time).total_seconds() / 60
                if gap > 30:
                    if current_thread:
                        threads.append(self._summarize_thread(current_thread))
                    current_thread = []
            
            current_thread.append(memory)
            last_time = memory.timestamp
        
        # Don't forget the last thread
        if current_thread:
            threads.append(self._summarize_thread(current_thread))
        
        return threads
    
    def _summarize_thread(self, thread_memories: List[Memory]) -> Dict:
        """Summarize a thought thread"""
        return {
            'start_time': thread_memories[0].timestamp.isoformat() if thread_memories[0].timestamp else None,
            'end_time': thread_memories[-1].timestamp.isoformat() if thread_memories[-1].timestamp else None,
            'memory_count': len(thread_memories),
            'main_topic': self._get_dominant_topic(thread_memories),
            'summary': self._generate_thread_summary(thread_memories)
        }
    
    def _get_dominant_topic(self, memories: List[Memory]) -> str:
        """Find the most common topic in a set of memories"""
        topic_counts = {}
        
        for memory in memories:
            if memory.extracted_data and memory.extracted_data.get('topics'):
                for topic in memory.extracted_data['topics']:
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        if topic_counts:
            return max(topic_counts, key=topic_counts.get)
        return "general"
    
    def _generate_thread_summary(self, memories: List[Memory]) -> str:
        """Generate a summary of a thought thread"""
        if len(memories) == 1:
            return memories[0].summary or memories[0].raw_text[:100]
        
        # Combine summaries for LLM
        summaries = []
        for mem in memories[:10]:  # Limit to prevent too long prompt
            summary = mem.summary or mem.raw_text[:100]
            summaries.append(summary)
        
        prompt = f"""
        Summarize this sequence of related thoughts into one coherent summary:
        {chr(10).join(summaries)}
        
        Return a single sentence that captures the essence of this thought sequence.
        """
        
        try:
            result = self.extractor.extract(prompt)
            return result.get('summary', summaries[0])
        except:
            return summaries[0] if summaries else ""
    
    def _extract_decisions(self, memories: List[Memory]) -> List[Dict]:
        """Extract key decisions made during the day"""
        decisions = []
        
        for memory in memories:
            if memory.thought_type == 'decision':
                decisions.append({
                    'decision': memory.summary or memory.raw_text[:100],
                    'time': memory.timestamp.isoformat() if memory.timestamp else None,
                    'context': memory.extracted_data.get('context', '') if memory.extracted_data else ''
                })
            elif memory.extracted_data and memory.extracted_data.get('decisions'):
                for decision in memory.extracted_data['decisions']:
                    decisions.append({
                        'decision': decision,
                        'time': memory.timestamp.isoformat() if memory.timestamp else None,
                        'context': memory.summary
                    })
        
        return decisions
    
    def _extract_topics(self, memories: List[Memory]) -> List[Dict]:
        """Extract and rank main topics of the day"""
        topic_stats = {}
        
        for memory in memories:
            if memory.extracted_data and memory.extracted_data.get('topics'):
                for topic in memory.extracted_data['topics']:
                    if topic not in topic_stats:
                        topic_stats[topic] = {
                            'count': 0,
                            'first_mention': memory.timestamp,
                            'last_mention': memory.timestamp,
                            'memories': []
                        }
                    
                    topic_stats[topic]['count'] += 1
                    topic_stats[topic]['last_mention'] = memory.timestamp
                    topic_stats[topic]['memories'].append(memory.uuid)
        
        # Convert to sorted list
        topics = []
        for topic, stats in sorted(topic_stats.items(), key=lambda x: x[1]['count'], reverse=True):
            topics.append({
                'topic': topic,
                'count': stats['count'],
                'duration': (stats['last_mention'] - stats['first_mention']).total_seconds() / 3600 if stats['first_mention'] and stats['last_mention'] else 0,
                'memory_ids': stats['memories'][:5]  # Keep only first 5 for space
            })
        
        return topics[:10]  # Top 10 topics
    
    def _analyze_emotional_journey(self, memories: List[Memory]) -> Dict:
        """Analyze emotional patterns throughout the day"""
        emotions = []
        
        for memory in memories:
            if memory.extracted_data and memory.extracted_data.get('mood'):
                emotions.append({
                    'time': memory.timestamp.hour if memory.timestamp else 0,
                    'mood': memory.extracted_data['mood'],
                    'context': memory.summary
                })
        
        if not emotions:
            return {'pattern': 'neutral', 'changes': []}
        
        # Identify emotional shifts
        shifts = []
        last_mood = None
        for emotion in emotions:
            if last_mood and emotion['mood'] != last_mood:
                shifts.append({
                    'from': last_mood,
                    'to': emotion['mood'],
                    'time': emotion['time']
                })
            last_mood = emotion['mood']
        
        return {
            'pattern': self._identify_emotional_pattern(emotions),
            'changes': shifts,
            'dominant_mood': max(set(e['mood'] for e in emotions), key=lambda x: sum(1 for e in emotions if e['mood'] == x))
        }
    
    def _identify_emotional_pattern(self, emotions: List[Dict]) -> str:
        """Identify overall emotional pattern"""
        if len(emotions) < 2:
            return 'stable'
        
        # Simple heuristic - could be made more sophisticated
        unique_moods = len(set(e['mood'] for e in emotions))
        
        if unique_moods == 1:
            return 'stable'
        elif unique_moods == 2:
            return 'binary'
        elif unique_moods > len(emotions) / 2:
            return 'volatile'
        else:
            return 'varied'
    
    def _extract_people_interactions(self, memories: List[Memory]) -> List[Dict]:
        """Extract important people interactions"""
        people_stats = {}
        
        for memory in memories:
            if memory.extracted_data and memory.extracted_data.get('people'):
                for person in memory.extracted_data['people']:
                    if person not in people_stats:
                        people_stats[person] = {
                            'mentions': 0,
                            'contexts': [],
                            'memories': []
                        }
                    
                    people_stats[person]['mentions'] += 1
                    people_stats[person]['contexts'].append(memory.summary or memory.raw_text[:50])
                    people_stats[person]['memories'].append(memory.uuid)
        
        # Convert to list
        interactions = []
        for person, stats in sorted(people_stats.items(), key=lambda x: x[1]['mentions'], reverse=True):
            interactions.append({
                'person': person,
                'mentions': stats['mentions'],
                'primary_context': stats['contexts'][0] if stats['contexts'] else '',
                'memory_ids': stats['memories'][:3]
            })
        
        return interactions[:10]  # Top 10 people
    
    def _extract_ideas(self, memories: List[Memory]) -> List[Dict]:
        """Extract creative insights and ideas"""
        ideas = []
        
        for memory in memories:
            if memory.thought_type in ['idea', 'insight']:
                ideas.append({
                    'idea': memory.summary or memory.raw_text[:200],
                    'type': memory.thought_type,
                    'time': memory.timestamp.isoformat() if memory.timestamp else None
                })
            elif memory.extracted_data and memory.extracted_data.get('ideas'):
                for idea in memory.extracted_data['ideas']:
                    ideas.append({
                        'idea': idea,
                        'type': 'idea',
                        'time': memory.timestamp.isoformat() if memory.timestamp else None
                    })
        
        return ideas
    
    def _get_completed_tasks(self, memories: List[Memory]) -> List[Dict]:
        """Get tasks that were completed during the day"""
        completed = []
        
        for memory in memories:
            if memory.extracted_data:
                # Check if this is a completed task
                if memory.extracted_data.get('completed'):
                    completed.append({
                        'task': memory.summary or memory.raw_text[:100],
                        'completed_at': memory.timestamp.isoformat() if memory.timestamp else None
                    })
                # Check for completion indicators in text
                elif any(word in memory.raw_text.lower() for word in ['done', 'completed', 'finished']):
                    if memory.extracted_data.get('actionable'):
                        completed.append({
                            'task': memory.summary or memory.raw_text[:100],
                            'completed_at': memory.timestamp.isoformat() if memory.timestamp else None
                        })
        
        return completed
    
    def _extract_questions(self, memories: List[Memory]) -> List[str]:
        """Extract open questions from the day"""
        questions = []
        
        for memory in memories:
            if memory.thought_type == 'question':
                questions.append(memory.summary or memory.raw_text[:200])
            elif memory.extracted_data and memory.extracted_data.get('questions'):
                questions.extend(memory.extracted_data['questions'])
        
        return list(set(questions))[:20]  # Unique questions, max 20
    
    def _analyze_energy_levels(self, memories: List[Memory]) -> Dict:
        """Analyze energy and productivity patterns"""
        hourly_activity = {}
        
        for memory in memories:
            if memory.timestamp:
                hour = memory.timestamp.hour
                if hour not in hourly_activity:
                    hourly_activity[hour] = {
                        'count': 0,
                        'types': [],
                        'completed_tasks': 0
                    }
                
                hourly_activity[hour]['count'] += 1
                hourly_activity[hour]['types'].append(memory.thought_type)
                
                if memory.extracted_data and memory.extracted_data.get('completed'):
                    hourly_activity[hour]['completed_tasks'] += 1
        
        # Find peak hours
        peak_hours = sorted(hourly_activity.keys(), 
                          key=lambda h: hourly_activity[h]['count'], 
                          reverse=True)[:3]
        
        return {
            'peak_hours': peak_hours,
            'total_active_hours': len(hourly_activity),
            'hourly_breakdown': hourly_activity,
            'most_productive_hour': max(hourly_activity.keys(), 
                                       key=lambda h: hourly_activity[h]['completed_tasks']) if hourly_activity else None
        }
    
    def _generate_narrative(self, consolidation: Dict) -> str:
        """Create a human-readable story of the day"""
        # Build prompt with day's data
        decisions_text = ""
        if consolidation['key_decisions']:
            decisions_text = "Key decisions: " + "; ".join([d['decision'] for d in consolidation['key_decisions'][:3]])
        
        topics_text = ""
        if consolidation['main_topics']:
            topics_text = "Main topics: " + ", ".join([t['topic'] for t in consolidation['main_topics'][:5]])
        
        people_text = ""
        if consolidation['important_interactions']:
            people_text = "Interacted with: " + ", ".join([p['person'] for p in consolidation['important_interactions'][:5]])
        
        prompt = f"""
        Create a brief narrative summary of this day:
        - {consolidation['memory_count']} thoughts recorded
        - {decisions_text}
        - {topics_text}
        - {people_text}
        - Emotional pattern: {consolidation['emotional_arc'].get('pattern', 'stable')}
        - {len(consolidation['completed_actions'])} tasks completed
        - {len(consolidation['creative_insights'])} creative insights
        
        Write a cohesive 2-3 sentence paragraph focusing on what mattered most.
        Make it personal and reflective, as if writing in a journal.
        """
        
        try:
            result = self.extractor.extract(prompt)
            return result.get('narrative', result.get('summary', 'Day processed successfully.'))
        except:
            return f"Processed {consolidation['memory_count']} memories with {len(consolidation['key_decisions'])} decisions and {len(consolidation['completed_actions'])} completed tasks."
    
    def _calculate_importance(self, consolidation: Dict) -> float:
        """Calculate importance score for the day"""
        score = 0.0
        
        # Decisions are important
        score += len(consolidation['key_decisions']) * 2.0
        
        # Completed tasks show productivity
        score += len(consolidation['completed_actions']) * 1.5
        
        # Creative insights are valuable
        score += len(consolidation['creative_insights']) * 2.5
        
        # People interactions matter
        score += min(len(consolidation['important_interactions']), 5) * 1.0
        
        # Emotional volatility might indicate important events
        if consolidation['emotional_arc'].get('pattern') == 'volatile':
            score += 2.0
        
        # Many thought threads show mental activity
        score += len(consolidation.get('thought_threads', [])) * 0.5
        
        # Normalize to 0-10 scale
        return min(score / 5.0, 10.0)
    
    def _store_consolidation(self, data: Dict):
        """Store consolidation in database"""
        query = """
            INSERT INTO daily_consolidations (
                date, narrative, key_decisions, main_topics, emotional_arc,
                interactions, insights, completed_actions, open_questions,
                energy_pattern, source_memory_ids, importance_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        values = (
            data['date'].isoformat() if isinstance(data['date'], date) else data['date'],
            data['narrative'],
            json.dumps(data['key_decisions']),
            json.dumps(data['main_topics']),
            json.dumps(data['emotional_arc']),
            json.dumps(data['interactions']),
            json.dumps(data['insights']),
            json.dumps(data['completed_actions']),
            json.dumps(data['open_questions']),
            json.dumps(data['energy_pattern']),
            json.dumps(data['source_memory_ids']),
            data['importance_score']
        )
        
        self.db.conn.execute(query, values)
        self.db.conn.commit()
    
    def consolidate_recent_days(self, days: int = 7):
        """Consolidate the last N days"""
        for i in range(days):
            target_date = datetime.now().date() - timedelta(days=i)
            try:
                self.consolidate_day(target_date)
            except Exception as e:
                print(f"Failed to consolidate {target_date}: {e}")