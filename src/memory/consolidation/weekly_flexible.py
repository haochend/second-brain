"""Weekly pattern recognition with flexible synthesis"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import Counter
from ..storage import Database, Memory
from .base import BaseConsolidator


class FlexibleWeeklyPatternRecognizer(BaseConsolidator):
    """Weekly pattern recognizer with user-defined synthesis"""
    
    def identify_patterns(self, 
                         week_number: Optional[int] = None, 
                         year: Optional[int] = None,
                         custom_prompt: Optional[str] = None,
                         skip_synthesis: bool = False) -> Dict[str, Any]:
        """
        Identify patterns for a specific week with flexible synthesis
        
        Args:
            week_number: Week number to analyze
            year: Year of the week
            custom_prompt: Optional custom prompt for synthesis
            skip_synthesis: If True, only extract infrastructure
        
        Returns:
            Dictionary with patterns and synthesis
        """
        # Default to last week
        if week_number is None or year is None:
            last_week = datetime.now() - timedelta(weeks=1)
            year = last_week.year
            week_number = last_week.isocalendar()[1]
        
        # Check if already processed
        existing = self._get_existing_patterns(week_number, year)
        if existing and not custom_prompt:
            print(f"Week {week_number}/{year} already analyzed")
            return existing
        
        print(f"Analyzing patterns for week {week_number}/{year}...")
        
        # Get week's memories and consolidations
        week_memories = self._get_week_memories(week_number, year)
        daily_consolidations = self._get_week_consolidations(week_number, year)
        
        if not week_memories and not daily_consolidations:
            print(f"No data found for week {week_number}/{year}")
            return {}
        
        # LAYER 1: Extract Infrastructure (always runs)
        infrastructure = self.extract_infrastructure(week_memories)
        
        # Add weekly-specific patterns
        infrastructure['recurring_themes'] = self._find_recurring_themes(week_memories)
        infrastructure['productivity_patterns'] = self._analyze_productivity(week_memories)
        infrastructure['collaboration_patterns'] = self._analyze_interactions(week_memories)
        infrastructure['decision_patterns'] = self._analyze_decision_making(week_memories, daily_consolidations)
        infrastructure['blocker_patterns'] = self._find_recurring_blockers(week_memories)
        infrastructure['creative_patterns'] = self._analyze_creative_timing(week_memories)
        infrastructure['stress_triggers'] = self._identify_stress_patterns(week_memories)
        infrastructure['success_patterns'] = self._identify_what_works(week_memories)
        infrastructure['daily_consolidations'] = daily_consolidations
        
        # LAYER 2: Generate Synthesis (user-defined)
        synthesis = None
        if not skip_synthesis:
            synthesis = self.synthesize_with_prompt(
                infrastructure=infrastructure,
                prompt_type='weekly',
                custom_prompt=custom_prompt
            )
        
        # Generate traditional recommendations (can be overridden by synthesis)
        recommendations = self._generate_recommendations(infrastructure)
        
        # Prepare result
        result = {
            'week_number': week_number,
            'year': year,
            'infrastructure': infrastructure,
            'synthesis': synthesis,
            'recommendations': recommendations,
            'memory_count': len(week_memories),
            'consolidation_count': len(daily_consolidations)
        }
        
        # Store patterns
        if not existing or custom_prompt:
            self._store_patterns(result)
        
        return result
    
    def _get_existing_patterns(self, week_number: int, year: int) -> Optional[Dict]:
        """Check if patterns already exist for this week"""
        query = "SELECT * FROM weekly_patterns WHERE week_number = ? AND year = ?"
        cursor = self.db.conn.execute(query, (week_number, year))
        row = cursor.fetchone()
        
        if row:
            data = dict(row)
            # Parse JSON fields
            for field in ['patterns', 'recommendations', 'recurring_themes']:
                if data.get(field):
                    try:
                        data[field] = json.loads(data[field])
                    except:
                        pass
            return data
        return None
    
    def _get_week_memories(self, week_number: int, year: int) -> List[Memory]:
        """Get all memories for a specific week"""
        # Calculate week start and end dates
        jan1 = datetime(year, 1, 1)
        week_start = jan1 + timedelta(weeks=week_number-1)
        
        # Find the Monday of that week
        days_since_monday = week_start.weekday()
        week_start = week_start - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        query = """
            SELECT * FROM memories
            WHERE timestamp BETWEEN ? AND ?
            AND status = 'completed'
            ORDER BY timestamp ASC
        """
        cursor = self.db.conn.execute(query, (week_start.isoformat(), week_end.isoformat()))
        return [Memory.from_row(row) for row in cursor]
    
    def _get_week_consolidations(self, week_number: int, year: int) -> List[Dict]:
        """Get daily consolidations for the week"""
        # Calculate week dates
        jan1 = datetime(year, 1, 1)
        week_start = jan1 + timedelta(weeks=week_number-1)
        days_since_monday = week_start.weekday()
        week_start = week_start - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)
        
        query = """
            SELECT * FROM daily_consolidations
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC
        """
        cursor = self.db.conn.execute(query, 
                                    (week_start.date().isoformat(), 
                                     week_end.date().isoformat()))
        
        consolidations = []
        for row in cursor:
            data = dict(row)
            # Parse JSON fields
            for field in ['key_decisions', 'main_topics', 'emotional_arc']:
                if data.get(field):
                    try:
                        data[field] = json.loads(data[field])
                    except:
                        pass
            consolidations.append(data)
        
        return consolidations
    
    def _find_recurring_themes(self, memories: List[Memory]) -> Dict[str, Any]:
        """Identify themes that keep coming up"""
        theme_occurrences = {}
        theme_days = {}
        theme_sentiments = {}
        
        for memory in memories:
            if hasattr(memory, 'extracted_data') and memory.extracted_data:
                day = memory.timestamp.date() if hasattr(memory, 'timestamp') and memory.timestamp else None
                
                for topic in memory.extracted_data.get('topics', []):
                    # Count occurrences
                    theme_occurrences[topic] = theme_occurrences.get(topic, 0) + 1
                    
                    # Track days
                    if topic not in theme_days:
                        theme_days[topic] = set()
                    if day:
                        theme_days[topic].add(day.isoformat())
                    
                    # Track sentiment
                    mood = memory.extracted_data.get('mood')
                    if mood:
                        if topic not in theme_sentiments:
                            theme_sentiments[topic] = []
                        theme_sentiments[topic].append(mood)
        
        # Build recurring themes
        recurring_themes = {}
        for theme, count in theme_occurrences.items():
            if count >= 3:  # Theme appeared at least 3 times
                recurring_themes[theme] = {
                    'count': count,
                    'days_present': len(theme_days.get(theme, [])),
                    'trend': self._analyze_trend(theme, memories),
                    'sentiment': self._analyze_sentiment(theme_sentiments.get(theme, []))
                }
        
        return dict(sorted(recurring_themes.items(), key=lambda x: x[1]['count'], reverse=True))
    
    def _analyze_trend(self, theme: str, memories: List[Memory]) -> str:
        """Analyze if a theme is increasing, decreasing, or stable"""
        midpoint = len(memories) // 2
        first_half_count = 0
        second_half_count = 0
        
        for i, memory in enumerate(memories):
            if hasattr(memory, 'extracted_data') and memory.extracted_data:
                if theme in memory.extracted_data.get('topics', []):
                    if i < midpoint:
                        first_half_count += 1
                    else:
                        second_half_count += 1
        
        if second_half_count > first_half_count * 1.5:
            return 'increasing'
        elif first_half_count > second_half_count * 1.5:
            return 'decreasing'
        else:
            return 'stable'
    
    def _analyze_sentiment(self, sentiments: List[str]) -> str:
        """Analyze overall sentiment"""
        if not sentiments:
            return 'neutral'
        
        sentiment_counts = Counter(sentiments)
        dominant = sentiment_counts.most_common(1)[0][0] if sentiment_counts else 'neutral'
        
        # Categorize
        positive = ['happy', 'excited', 'confident', 'satisfied', 'peaceful']
        negative = ['stressed', 'anxious', 'frustrated', 'sad', 'angry']
        
        pos_count = sum(sentiment_counts.get(s, 0) for s in positive)
        neg_count = sum(sentiment_counts.get(s, 0) for s in negative)
        
        if pos_count > neg_count * 2:
            return 'positive'
        elif neg_count > pos_count * 2:
            return 'negative'
        else:
            return 'mixed'
    
    def _analyze_productivity(self, memories: List[Memory]) -> Dict[str, Any]:
        """Analyze productivity patterns"""
        productivity_by_day = {}
        productivity_by_hour = {}
        
        for memory in memories:
            if hasattr(memory, 'timestamp') and memory.timestamp:
                day = memory.timestamp.strftime('%A')
                hour = memory.timestamp.hour
                
                # Initialize counters
                if day not in productivity_by_day:
                    productivity_by_day[day] = {'total': 0, 'completed': 0, 'actionable': 0}
                if hour not in productivity_by_hour:
                    productivity_by_hour[hour] = {'total': 0, 'completed': 0, 'actionable': 0}
                
                # Count activity
                productivity_by_day[day]['total'] += 1
                productivity_by_hour[hour]['total'] += 1
                
                # Track completions and actionables
                if hasattr(memory, 'extracted_data') and memory.extracted_data:
                    if memory.extracted_data.get('completed'):
                        productivity_by_day[day]['completed'] += 1
                        productivity_by_hour[hour]['completed'] += 1
                    
                    if memory.extracted_data.get('actionable'):
                        productivity_by_day[day]['actionable'] += 1
                        productivity_by_hour[hour]['actionable'] += 1
        
        # Calculate metrics
        peak_hours = sorted(productivity_by_hour.keys(), 
                           key=lambda h: productivity_by_hour[h]['total'], 
                           reverse=True)[:3]
        
        most_productive_day = max(productivity_by_day.keys(), 
                                 key=lambda d: productivity_by_day[d]['completed']) if productivity_by_day else None
        
        total_actionable = sum(d['actionable'] for d in productivity_by_day.values())
        total_completed = sum(d['completed'] for d in productivity_by_day.values())
        completion_rate = total_completed / max(total_actionable, 1)
        
        return {
            'peak_hours': peak_hours,
            'most_productive_day': most_productive_day,
            'task_completion_rate': round(completion_rate, 2),
            'average_completions_per_day': round(total_completed / max(len(productivity_by_day), 1), 1),
            'by_day': productivity_by_day,
            'by_hour': productivity_by_hour
        }
    
    def _analyze_interactions(self, memories: List[Memory]) -> Dict[str, Any]:
        """Analyze collaboration and interaction patterns"""
        people_interactions = {}
        
        for memory in memories:
            if hasattr(memory, 'extracted_data') and memory.extracted_data:
                for person in memory.extracted_data.get('people', []):
                    if person not in people_interactions:
                        people_interactions[person] = {
                            'count': 0,
                            'days': set(),
                            'thought_types': Counter()
                        }
                    
                    people_interactions[person]['count'] += 1
                    
                    if hasattr(memory, 'timestamp') and memory.timestamp:
                        people_interactions[person]['days'].add(memory.timestamp.date().isoformat())
                    
                    if hasattr(memory, 'thought_type'):
                        people_interactions[person]['thought_types'][memory.thought_type] += 1
        
        # Convert to list format
        collaboration_insights = []
        for person, stats in sorted(people_interactions.items(), 
                                   key=lambda x: x[1]['count'], 
                                   reverse=True)[:10]:
            collaboration_insights.append({
                'person': person,
                'interaction_count': stats['count'],
                'days_interacted': len(stats['days']),
                'primary_context': stats['thought_types'].most_common(1)[0][0] if stats['thought_types'] else 'general'
            })
        
        return {
            'frequent_collaborators': collaboration_insights,
            'total_people_interacted': len(people_interactions),
            'average_interactions_per_person': round(sum(p['count'] for p in people_interactions.values()) / max(len(people_interactions), 1), 1)
        }
    
    def _analyze_decision_making(self, memories: List[Memory], consolidations: List[Dict]) -> Dict[str, Any]:
        """Analyze decision-making patterns"""
        decision_times = []
        decision_contexts = Counter()
        
        # From memories
        for memory in memories:
            if hasattr(memory, 'thought_type') and memory.thought_type == 'decision':
                if hasattr(memory, 'timestamp') and memory.timestamp:
                    decision_times.append(memory.timestamp.hour)
                
                # Track context
                if hasattr(memory, 'extracted_data') and memory.extracted_data:
                    for topic in memory.extracted_data.get('topics', []):
                        decision_contexts[topic] += 1
        
        # Count total decisions
        total_decisions = len(decision_times)
        
        # From daily consolidations
        for consolidation in consolidations:
            if consolidation.get('key_decisions'):
                total_decisions += len(consolidation['key_decisions'])
        
        return {
            'total_decisions': total_decisions,
            'decisions_per_day': round(total_decisions / max(len(consolidations), 1), 1),
            'peak_decision_hour': Counter(decision_times).most_common(1)[0][0] if decision_times else None,
            'main_decision_contexts': dict(decision_contexts.most_common(5))
        }
    
    def _find_recurring_blockers(self, memories: List[Memory]) -> Dict[str, Any]:
        """Find patterns in what blocks progress"""
        blockers = []
        blocker_themes = Counter()
        
        blocker_keywords = ['blocked', 'stuck', 'waiting', 'can\'t', 'unable', 'issue', 'problem']
        
        for memory in memories:
            text = memory.raw_text.lower() if hasattr(memory, 'raw_text') else str(memory).lower()
            
            if any(word in text for word in blocker_keywords):
                blocker = {
                    'description': memory.summary if hasattr(memory, 'summary') else text[:100],
                    'resolved': False
                }
                
                # Check if resolved
                if hasattr(memory, 'extracted_data') and memory.extracted_data:
                    if memory.extracted_data.get('resolved'):
                        blocker['resolved'] = True
                    
                    # Track themes
                    for topic in memory.extracted_data.get('topics', []):
                        blocker_themes[topic] += 1
                
                blockers.append(blocker)
        
        return {
            'blockers': blockers[:10],
            'blocker_count': len(blockers),
            'resolved_count': sum(1 for b in blockers if b['resolved']),
            'common_blocker_themes': dict(blocker_themes.most_common(5))
        }
    
    def _analyze_creative_timing(self, memories: List[Memory]) -> Dict[str, Any]:
        """Analyze when creative insights occur"""
        creative_times = []
        creative_days = Counter()
        
        for memory in memories:
            if hasattr(memory, 'thought_type') and memory.thought_type in ['idea', 'insight']:
                if hasattr(memory, 'timestamp') and memory.timestamp:
                    creative_times.append(memory.timestamp.hour)
                    creative_days[memory.timestamp.strftime('%A')] += 1
        
        return {
            'total_creative_insights': len(creative_times),
            'peak_creative_hour': Counter(creative_times).most_common(1)[0][0] if creative_times else None,
            'most_creative_day': creative_days.most_common(1)[0][0] if creative_days else None,
            'creative_distribution': dict(creative_days)
        }
    
    def _identify_stress_patterns(self, memories: List[Memory]) -> Dict[str, Any]:
        """Identify stress triggers and patterns"""
        stress_count = 0
        stress_contexts = Counter()
        stress_times = []
        
        stress_words = ['stress', 'anxious', 'worried', 'overwhelmed', 'frustrated', 'angry', 'upset']
        
        for memory in memories:
            text = memory.raw_text.lower() if hasattr(memory, 'raw_text') else str(memory).lower()
            
            if any(word in text for word in stress_words):
                stress_count += 1
                
                if hasattr(memory, 'timestamp') and memory.timestamp:
                    stress_times.append(memory.timestamp.hour)
                
                # Track context
                if hasattr(memory, 'extracted_data') and memory.extracted_data:
                    for topic in memory.extracted_data.get('topics', []):
                        stress_contexts[topic] += 1
        
        return {
            'stress_count': stress_count,
            'stress_triggers': dict(stress_contexts.most_common(5)),
            'peak_stress_time': Counter(stress_times).most_common(1)[0][0] if stress_times else None
        }
    
    def _identify_what_works(self, memories: List[Memory]) -> Dict[str, Any]:
        """Identify successful patterns"""
        success_count = 0
        success_contexts = Counter()
        success_times = []
        
        success_words = ['success', 'achieved', 'completed', 'solved', 'fixed', 'great', 'excellent', 'breakthrough']
        
        for memory in memories:
            text = memory.raw_text.lower() if hasattr(memory, 'raw_text') else str(memory).lower()
            
            if any(word in text for word in success_words):
                success_count += 1
                
                if hasattr(memory, 'timestamp') and memory.timestamp:
                    success_times.append(memory.timestamp.hour)
                
                # Track context
                if hasattr(memory, 'extracted_data') and memory.extracted_data:
                    for topic in memory.extracted_data.get('topics', []):
                        success_contexts[topic] += 1
        
        return {
            'success_count': success_count,
            'success_contexts': dict(success_contexts.most_common(5)),
            'peak_success_time': Counter(success_times).most_common(1)[0][0] if success_times else None
        }
    
    def _generate_recommendations(self, infrastructure: Dict) -> List[str]:
        """Generate actionable recommendations based on patterns"""
        recommendations = []
        
        # Productivity recommendations
        if 'productivity_patterns' in infrastructure:
            prod = infrastructure['productivity_patterns']
            if prod.get('peak_hours'):
                recommendations.append(f"Schedule important work during peak hours: {', '.join(str(h) + ':00' for h in prod['peak_hours'][:2])}")
            
            if prod.get('task_completion_rate', 0) < 0.5:
                recommendations.append("Break tasks into smaller pieces - completion rate is low")
        
        # Stress recommendations
        if 'stress_triggers' in infrastructure:
            stress = infrastructure['stress_triggers']
            if stress.get('stress_count', 0) > 5:
                triggers = list(stress.get('stress_triggers', {}).keys())[:2]
                if triggers:
                    recommendations.append(f"Address recurring stressors: {', '.join(triggers)}")
        
        # Blocker recommendations
        if 'blocker_patterns' in infrastructure:
            blockers = infrastructure['blocker_patterns']
            if blockers.get('resolved_count', 0) < blockers.get('blocker_count', 0) / 2:
                recommendations.append("Focus on resolving blockers - many remain unresolved")
        
        # Creative recommendations
        if 'creative_patterns' in infrastructure:
            creative = infrastructure['creative_patterns']
            if creative.get('peak_creative_hour') is not None:
                recommendations.append(f"Protect creative time at {creative['peak_creative_hour']}:00")
        
        return recommendations[:5]
    
    def _store_patterns(self, data: Dict):
        """Store weekly patterns in database"""
        infrastructure = data.get('infrastructure', {})
        
        query = """
            INSERT OR REPLACE INTO weekly_patterns (
                week_number, year, patterns, insights, recommendations,
                recurring_themes, productivity_patterns, collaboration_patterns,
                decision_patterns, blocker_patterns, creative_patterns,
                stress_triggers, success_patterns, source_consolidation_ids
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Get consolidation IDs
        consolidation_ids = [c.get('id', '') for c in infrastructure.get('daily_consolidations', [])]
        
        values = (
            data['week_number'],
            data['year'],
            json.dumps(infrastructure),
            data.get('synthesis', ''),
            json.dumps(data.get('recommendations', [])),
            json.dumps(infrastructure.get('recurring_themes', {})),
            json.dumps(infrastructure.get('productivity_patterns', {})),
            json.dumps(infrastructure.get('collaboration_patterns', {})),
            json.dumps(infrastructure.get('decision_patterns', {})),
            json.dumps(infrastructure.get('blocker_patterns', {})),
            json.dumps(infrastructure.get('creative_patterns', {})),
            json.dumps(infrastructure.get('stress_triggers', {})),
            json.dumps(infrastructure.get('success_patterns', {})),
            json.dumps(consolidation_ids)
        )
        
        self.db.conn.execute(query, values)
        self.db.conn.commit()