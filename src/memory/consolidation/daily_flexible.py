"""Daily memory consolidation with flexible synthesis"""

import json
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
from ..storage import Database, Memory
from .base import BaseConsolidator


class FlexibleDailyConsolidator(BaseConsolidator):
    """Daily consolidator with user-defined synthesis"""
    
    def consolidate_day(self, 
                       target_date: Optional[date] = None,
                       custom_prompt: Optional[str] = None,
                       skip_synthesis: bool = False) -> Dict[str, Any]:
        """
        Process a day's memories with flexible synthesis
        
        Args:
            target_date: Date to consolidate (defaults to yesterday)
            custom_prompt: Optional custom prompt for synthesis
            skip_synthesis: If True, only extract infrastructure
        
        Returns:
            Dictionary with infrastructure and synthesis
        """
        target_date = target_date or (datetime.now().date() - timedelta(days=1))
        
        # Check if already consolidated
        existing = self._get_existing_consolidation(target_date)
        if existing and not custom_prompt:
            print(f"Day {target_date} already consolidated")
            return existing
        
        # Get all memories for the date
        memories = self._get_memories_for_date(target_date)
        
        if not memories:
            print(f"No memories found for {target_date}")
            return {}
        
        print(f"Consolidating {len(memories)} memories from {target_date}...")
        
        # LAYER 1: Extract Infrastructure (always runs)
        infrastructure = self.extract_infrastructure(memories)
        
        # Add daily-specific infrastructure
        infrastructure['thought_threads'] = self._identify_thought_threads(memories)
        infrastructure['energy_pattern'] = self._analyze_energy_levels(memories)
        infrastructure['completed_actions'] = self._get_completed_tasks(memories)
        
        # Calculate importance score
        importance_score = self._calculate_importance(infrastructure)
        
        # LAYER 2: Generate Synthesis (user-defined)
        synthesis = None
        if not skip_synthesis:
            synthesis = self.synthesize_with_prompt(
                infrastructure=infrastructure,
                prompt_type='daily',
                custom_prompt=custom_prompt
            )
        
        # Prepare result
        result = {
            'date': target_date.isoformat(),
            'infrastructure': infrastructure,
            'synthesis': synthesis,
            'importance_score': importance_score,
            'memory_count': len(memories),
            'source_memory_ids': [m.uuid if hasattr(m, 'uuid') else str(i) 
                                 for i, m in enumerate(memories)]
        }
        
        # Store consolidation
        if not existing or custom_prompt:
            self._store_consolidation(result)
        
        return result
    
    def _get_existing_consolidation(self, target_date: date) -> Optional[Dict]:
        """Check if consolidation already exists for date"""
        query = "SELECT * FROM daily_consolidations WHERE date = ?"
        cursor = self.db.conn.execute(query, (target_date.isoformat(),))
        row = cursor.fetchone()
        
        if row:
            data = dict(row)
            # Parse JSON fields
            for field in ['key_decisions', 'main_topics', 'emotional_arc', 'insights']:
                if data.get(field):
                    try:
                        data[field] = json.loads(data[field])
                    except:
                        pass
            return data
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
            if last_time and hasattr(memory, 'timestamp') and memory.timestamp:
                gap = (memory.timestamp - last_time).total_seconds() / 60
                if gap > 30:
                    if current_thread:
                        threads.append(self._summarize_thread(current_thread))
                    current_thread = []
            
            current_thread.append(memory)
            if hasattr(memory, 'timestamp'):
                last_time = memory.timestamp
        
        # Don't forget the last thread
        if current_thread:
            threads.append(self._summarize_thread(current_thread))
        
        return threads
    
    def _summarize_thread(self, thread_memories: List[Memory]) -> Dict:
        """Summarize a thought thread"""
        # Get dominant topic
        topics = {}
        for mem in thread_memories:
            if hasattr(mem, 'extracted_data') and mem.extracted_data:
                for topic in mem.extracted_data.get('topics', []):
                    topics[topic] = topics.get(topic, 0) + 1
        
        dominant_topic = max(topics, key=topics.get) if topics else "general"
        
        return {
            'start_time': thread_memories[0].timestamp.isoformat() if hasattr(thread_memories[0], 'timestamp') and thread_memories[0].timestamp else None,
            'end_time': thread_memories[-1].timestamp.isoformat() if hasattr(thread_memories[-1], 'timestamp') and thread_memories[-1].timestamp else None,
            'memory_count': len(thread_memories),
            'main_topic': dominant_topic,
            'memory_indices': [i for i in range(len(thread_memories))]
        }
    
    def _analyze_energy_levels(self, memories: List[Memory]) -> Dict:
        """Analyze energy and productivity patterns"""
        hourly_activity = {}
        
        for memory in memories:
            if hasattr(memory, 'timestamp') and memory.timestamp:
                hour = memory.timestamp.hour
                if hour not in hourly_activity:
                    hourly_activity[hour] = {
                        'count': 0,
                        'types': [],
                        'completed_tasks': 0
                    }
                
                hourly_activity[hour]['count'] += 1
                
                if hasattr(memory, 'thought_type'):
                    hourly_activity[hour]['types'].append(memory.thought_type)
                
                if hasattr(memory, 'extracted_data') and memory.extracted_data:
                    if memory.extracted_data.get('completed'):
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
    
    def _get_completed_tasks(self, memories: List[Memory]) -> List[Dict]:
        """Get tasks that were completed during the day"""
        completed = []
        
        for memory in memories:
            if hasattr(memory, 'extracted_data') and memory.extracted_data:
                # Check if this is a completed task
                if memory.extracted_data.get('completed'):
                    completed.append({
                        'task': memory.summary if hasattr(memory, 'summary') else memory.raw_text[:100] if hasattr(memory, 'raw_text') else str(memory)[:100],
                        'completed_at': memory.timestamp.isoformat() if hasattr(memory, 'timestamp') and memory.timestamp else None
                    })
        
        return completed
    
    def _calculate_importance(self, infrastructure: Dict) -> float:
        """Calculate importance score for the day"""
        score = 0.0
        
        # Decisions are important
        score += len(infrastructure.get('decisions', [])) * 2.0
        
        # Completed tasks show productivity
        score += len(infrastructure.get('completed_actions', [])) * 1.5
        
        # Questions show curiosity
        score += len(infrastructure.get('questions', [])) * 1.0
        
        # People interactions matter
        score += min(len(infrastructure.get('people', {})), 5) * 1.0
        
        # Many thought threads show mental activity
        score += len(infrastructure.get('thought_threads', [])) * 0.5
        
        # Normalize to 0-10 scale
        return min(score / 5.0, 10.0)
    
    def _store_consolidation(self, data: Dict):
        """Store consolidation in database"""
        # For backward compatibility, extract some fields
        infrastructure = data.get('infrastructure', {})
        
        query = """
            INSERT OR REPLACE INTO daily_consolidations (
                date, narrative, key_decisions, main_topics, emotional_arc,
                interactions, insights, completed_actions, open_questions,
                energy_pattern, source_memory_ids, importance_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        values = (
            data['date'],
            data.get('synthesis', ''),  # Use synthesis as narrative
            json.dumps(infrastructure.get('decisions', [])),
            json.dumps(infrastructure.get('topics', [])),
            json.dumps(infrastructure.get('emotions', {})),
            json.dumps(infrastructure.get('people', {})),
            json.dumps([]),  # insights will be in synthesis
            json.dumps(infrastructure.get('completed_actions', [])),
            json.dumps(infrastructure.get('questions', [])),
            json.dumps(infrastructure.get('energy_pattern', {})),
            json.dumps(data.get('source_memory_ids', [])),
            data.get('importance_score', 0)
        )
        
        self.db.conn.execute(query, values)
        self.db.conn.commit()