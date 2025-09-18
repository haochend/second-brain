"""Weekly pattern recognition - finds patterns across the week"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import Counter
from ..storage import Database, Memory
from ..processing.extraction import LLMExtractor


class WeeklyPatternRecognizer:
    """Find patterns and insights across a week of memories"""
    
    def __init__(self, db: Optional[Database] = None, extractor: Optional[LLMExtractor] = None):
        """Initialize weekly pattern recognizer"""
        self.db = db or Database()
        self.extractor = extractor or LLMExtractor()
    
    def identify_patterns(self, week_number: Optional[int] = None, year: Optional[int] = None) -> Dict[str, Any]:
        """Identify patterns for a specific week"""
        # Default to current week
        if week_number is None or year is None:
            now = datetime.now()
            year = now.year
            week_number = now.isocalendar()[1]
        
        # Check if already processed
        existing = self._get_existing_patterns(week_number, year)
        if existing:
            print(f"Week {week_number}/{year} already analyzed")
            return existing
        
        print(f"Analyzing patterns for week {week_number}/{year}...")
        
        # Get week's memories and consolidations
        week_memories = self._get_week_memories(week_number, year)
        daily_consolidations = self._get_week_consolidations(week_number, year)
        
        if not week_memories and not daily_consolidations:
            print(f"No data found for week {week_number}/{year}")
            return {}
        
        # Analyze various patterns
        patterns = {
            'recurring_themes': self._find_recurring_themes(week_memories),
            'productivity_patterns': self._analyze_productivity(week_memories),
            'collaboration_patterns': self._analyze_interactions(week_memories),
            'decision_patterns': self._analyze_decision_making(week_memories, daily_consolidations),
            'blocker_patterns': self._find_recurring_blockers(week_memories),
            'creative_patterns': self._analyze_creative_timing(week_memories),
            'stress_triggers': self._identify_stress_patterns(week_memories),
            'success_patterns': self._identify_what_works(week_memories)
        }
        
        # Generate insights
        insights = self._generate_weekly_insights(patterns, week_memories)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(patterns)
        
        # Store the patterns
        self._store_patterns({
            'week_number': week_number,
            'year': year,
            'patterns': patterns,
            'insights': insights,
            'recommendations': recommendations,
            'recurring_themes': patterns['recurring_themes'],
            'productivity_patterns': patterns['productivity_patterns'],
            'collaboration_patterns': patterns['collaboration_patterns'],
            'decision_patterns': patterns['decision_patterns'],
            'blocker_patterns': patterns['blocker_patterns'],
            'creative_patterns': patterns['creative_patterns'],
            'stress_triggers': patterns['stress_triggers'],
            'success_patterns': patterns['success_patterns'],
            'source_consolidation_ids': [c['id'] for c in daily_consolidations] if daily_consolidations else []
        })
        
        print(f"✓ Weekly pattern analysis complete for week {week_number}/{year}")
        
        return {
            'patterns': patterns,
            'insights': insights,
            'recommendations': recommendations
        }
    
    def _get_existing_patterns(self, week_number: int, year: int) -> Optional[Dict]:
        """Check if patterns already exist for this week"""
        query = "SELECT * FROM weekly_patterns WHERE week_number = ? AND year = ?"
        cursor = self.db.conn.execute(query, (week_number, year))
        row = cursor.fetchone()
        
        if row:
            data = dict(row)
            # Parse JSON fields
            for field in ['patterns', 'recommendations', 'recurring_themes', 'productivity_patterns',
                         'collaboration_patterns', 'decision_patterns', 'blocker_patterns',
                         'creative_patterns', 'stress_triggers', 'success_patterns']:
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
            for field in ['key_decisions', 'main_topics', 'emotional_arc', 
                         'interactions', 'insights', 'completed_actions',
                         'open_questions', 'energy_pattern']:
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
        theme_contexts = {}
        
        for memory in memories:
            if memory.extracted_data and memory.extracted_data.get('topics'):
                day = memory.timestamp.date() if memory.timestamp else None
                
                for topic in memory.extracted_data['topics']:
                    # Count occurrences
                    theme_occurrences[topic] = theme_occurrences.get(topic, 0) + 1
                    
                    # Track which days
                    if topic not in theme_days:
                        theme_days[topic] = set()
                    if day:
                        theme_days[topic].add(day.isoformat())
                    
                    # Track contexts
                    if topic not in theme_contexts:
                        theme_contexts[topic] = []
                    theme_contexts[topic].append(memory.summary or memory.raw_text[:50])
        
        # Analyze patterns
        recurring_themes = {}
        for theme, count in theme_occurrences.items():
            if count >= 3:  # Theme appeared at least 3 times
                recurring_themes[theme] = {
                    'count': count,
                    'days_present': len(theme_days.get(theme, [])),
                    'trend': self._analyze_trend(theme, memories),
                    'sentiment': self._analyze_theme_sentiment(theme, theme_contexts.get(theme, [])),
                    'example_contexts': theme_contexts.get(theme, [])[:3]
                }
        
        # Sort by count
        sorted_themes = dict(sorted(recurring_themes.items(), 
                                  key=lambda x: x[1]['count'], 
                                  reverse=True))
        
        return sorted_themes
    
    def _analyze_trend(self, theme: str, memories: List[Memory]) -> str:
        """Analyze if a theme is increasing, decreasing, or stable"""
        # Simple heuristic: compare first half vs second half of week
        midpoint = len(memories) // 2
        first_half_count = 0
        second_half_count = 0
        
        for i, memory in enumerate(memories):
            if memory.extracted_data and memory.extracted_data.get('topics'):
                if theme in memory.extracted_data['topics']:
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
    
    def _analyze_theme_sentiment(self, theme: str, contexts: List[str]) -> str:
        """Analyze overall sentiment around a theme"""
        if not contexts:
            return 'neutral'
        
        # Simple keyword-based sentiment
        positive_words = ['good', 'great', 'excellent', 'happy', 'success', 'completed', 'achieved']
        negative_words = ['bad', 'issue', 'problem', 'failed', 'stuck', 'blocked', 'difficult']
        
        positive_count = 0
        negative_count = 0
        
        for context in contexts:
            context_lower = context.lower()
            for word in positive_words:
                if word in context_lower:
                    positive_count += 1
            for word in negative_words:
                if word in context_lower:
                    negative_count += 1
        
        if positive_count > negative_count * 2:
            return 'positive'
        elif negative_count > positive_count * 2:
            return 'negative'
        else:
            return 'mixed'
    
    def _analyze_productivity(self, memories: List[Memory]) -> Dict[str, Any]:
        """Analyze productivity patterns"""
        # Track by day and hour
        productivity_by_day = {}
        productivity_by_hour = {}
        task_completion_times = []
        focus_sessions = []
        
        for memory in memories:
            if memory.timestamp:
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
                if memory.extracted_data:
                    if memory.extracted_data.get('completed'):
                        productivity_by_day[day]['completed'] += 1
                        productivity_by_hour[hour]['completed'] += 1
                        task_completion_times.append(hour)
                    
                    if memory.extracted_data.get('actionable'):
                        productivity_by_day[day]['actionable'] += 1
                        productivity_by_hour[hour]['actionable'] += 1
        
        # Calculate metrics
        peak_hours = sorted(productivity_by_hour.keys(), 
                           key=lambda h: productivity_by_hour[h]['total'], 
                           reverse=True)[:3]
        
        most_productive_day = max(productivity_by_day.keys(), 
                                 key=lambda d: productivity_by_day[d]['completed']) if productivity_by_day else None
        
        completion_rate = sum(d['completed'] for d in productivity_by_day.values()) / max(sum(d['actionable'] for d in productivity_by_day.values()), 1)
        
        return {
            'peak_hours': peak_hours,
            'most_productive_day': most_productive_day,
            'task_completion_rate': round(completion_rate, 2),
            'average_completions_per_day': round(sum(d['completed'] for d in productivity_by_day.values()) / max(len(productivity_by_day), 1), 1),
            'productivity_by_day': productivity_by_day,
            'productivity_by_hour': productivity_by_hour
        }
    
    def _analyze_interactions(self, memories: List[Memory]) -> Dict[str, Any]:
        """Analyze collaboration and interaction patterns"""
        people_interactions = {}
        interaction_types = Counter()
        interaction_outcomes = []
        
        for memory in memories:
            if memory.extracted_data and memory.extracted_data.get('people'):
                for person in memory.extracted_data['people']:
                    if person not in people_interactions:
                        people_interactions[person] = {
                            'count': 0,
                            'contexts': [],
                            'days': set(),
                            'thought_types': Counter()
                        }
                    
                    people_interactions[person]['count'] += 1
                    people_interactions[person]['contexts'].append(memory.summary or memory.raw_text[:50])
                    if memory.timestamp:
                        people_interactions[person]['days'].add(memory.timestamp.date().isoformat())
                    people_interactions[person]['thought_types'][memory.thought_type] += 1
        
        # Analyze patterns
        frequent_collaborators = sorted(people_interactions.items(), 
                                       key=lambda x: x[1]['count'], 
                                       reverse=True)[:5]
        
        collaboration_insights = []
        for person, stats in frequent_collaborators:
            collaboration_insights.append({
                'person': person,
                'interaction_count': stats['count'],
                'days_interacted': len(stats['days']),
                'primary_context': max(stats['thought_types'].items(), key=lambda x: x[1])[0] if stats['thought_types'] else 'general',
                'sample_context': stats['contexts'][0] if stats['contexts'] else ''
            })
        
        return {
            'frequent_collaborators': collaboration_insights,
            'total_people_interacted': len(people_interactions),
            'average_interactions_per_person': round(sum(p['count'] for p in people_interactions.values()) / max(len(people_interactions), 1), 1)
        }
    
    def _analyze_decision_making(self, memories: List[Memory], consolidations: List[Dict]) -> Dict[str, Any]:
        """Analyze decision-making patterns"""
        decisions = []
        decision_times = []
        decision_contexts = {}
        
        # From memories
        for memory in memories:
            if memory.thought_type == 'decision':
                decisions.append({
                    'decision': memory.summary or memory.raw_text[:100],
                    'time': memory.timestamp,
                    'day': memory.timestamp.strftime('%A') if memory.timestamp else None
                })
                if memory.timestamp:
                    decision_times.append(memory.timestamp.hour)
                
                # Track context
                if memory.extracted_data and memory.extracted_data.get('topics'):
                    for topic in memory.extracted_data['topics']:
                        decision_contexts[topic] = decision_contexts.get(topic, 0) + 1
        
        # From daily consolidations
        for consolidation in consolidations:
            if consolidation.get('key_decisions'):
                for decision in consolidation['key_decisions']:
                    decisions.append(decision)
        
        # Analyze patterns
        decision_patterns = {
            'total_decisions': len(decisions),
            'decisions_per_day': round(len(decisions) / max(len(consolidations), 1), 1),
            'peak_decision_hour': max(set(decision_times), key=decision_times.count) if decision_times else None,
            'main_decision_contexts': dict(sorted(decision_contexts.items(), key=lambda x: x[1], reverse=True)[:5]),
            'sample_decisions': [d['decision'] for d in decisions[:3]]
        }
        
        return decision_patterns
    
    def _find_recurring_blockers(self, memories: List[Memory]) -> List[Dict]:
        """Find patterns in what blocks progress"""
        blockers = []
        blocker_themes = Counter()
        
        for memory in memories:
            # Look for blocker indicators
            text_lower = memory.raw_text.lower()
            if any(word in text_lower for word in ['blocked', 'stuck', 'waiting', 'can\'t', 'unable', 'issue', 'problem']):
                blocker = {
                    'description': memory.summary or memory.raw_text[:100],
                    'time': memory.timestamp.isoformat() if memory.timestamp else None,
                    'resolved': False
                }
                
                # Check if resolved
                if memory.extracted_data and memory.extracted_data.get('resolved'):
                    blocker['resolved'] = True
                
                blockers.append(blocker)
                
                # Track themes
                if memory.extracted_data and memory.extracted_data.get('topics'):
                    for topic in memory.extracted_data['topics']:
                        blocker_themes[topic] += 1
        
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
        ideas_by_hour = {}
        
        for memory in memories:
            if memory.thought_type in ['idea', 'insight']:
                if memory.timestamp:
                    creative_times.append(memory.timestamp.hour)
                    creative_days[memory.timestamp.strftime('%A')] += 1
                    
                    hour = memory.timestamp.hour
                    if hour not in ideas_by_hour:
                        ideas_by_hour[hour] = []
                    ideas_by_hour[hour].append(memory.summary or memory.raw_text[:50])
        
        # Find patterns
        peak_creative_hour = max(set(creative_times), key=creative_times.count) if creative_times else None
        most_creative_day = creative_days.most_common(1)[0][0] if creative_days else None
        
        return {
            'total_creative_insights': len(creative_times),
            'peak_creative_hour': peak_creative_hour,
            'most_creative_day': most_creative_day,
            'creative_distribution': dict(creative_days),
            'ideas_by_time': {h: len(ideas) for h, ideas in ideas_by_hour.items()}
        }
    
    def _identify_stress_patterns(self, memories: List[Memory]) -> Dict[str, Any]:
        """Identify stress triggers and patterns"""
        stress_indicators = []
        stress_contexts = Counter()
        stress_times = []
        
        stress_words = ['stress', 'anxious', 'worried', 'overwhelmed', 'frustrated', 'angry', 'upset']
        
        for memory in memories:
            text_lower = memory.raw_text.lower()
            
            # Check for stress indicators
            if any(word in text_lower for word in stress_words):
                stress_indicators.append({
                    'description': memory.summary or memory.raw_text[:100],
                    'time': memory.timestamp,
                    'day': memory.timestamp.strftime('%A') if memory.timestamp else None
                })
                
                if memory.timestamp:
                    stress_times.append(memory.timestamp.hour)
                
                # Track context
                if memory.extracted_data and memory.extracted_data.get('topics'):
                    for topic in memory.extracted_data['topics']:
                        stress_contexts[topic] += 1
        
        return {
            'stress_count': len(stress_indicators),
            'stress_triggers': dict(stress_contexts.most_common(5)),
            'peak_stress_time': max(set(stress_times), key=stress_times.count) if stress_times else None,
            'stress_examples': [s['description'] for s in stress_indicators[:3]]
        }
    
    def _identify_what_works(self, memories: List[Memory]) -> Dict[str, Any]:
        """Identify successful patterns and what leads to positive outcomes"""
        success_patterns = []
        success_contexts = Counter()
        success_times = []
        
        success_words = ['success', 'achieved', 'completed', 'solved', 'fixed', 'great', 'excellent', 'breakthrough']
        
        for memory in memories:
            text_lower = memory.raw_text.lower()
            
            # Check for success indicators
            if any(word in text_lower for word in success_words):
                success_patterns.append({
                    'description': memory.summary or memory.raw_text[:100],
                    'time': memory.timestamp,
                    'thought_type': memory.thought_type
                })
                
                if memory.timestamp:
                    success_times.append(memory.timestamp.hour)
                
                # Track context
                if memory.extracted_data and memory.extracted_data.get('topics'):
                    for topic in memory.extracted_data['topics']:
                        success_contexts[topic] += 1
        
        return {
            'success_count': len(success_patterns),
            'success_contexts': dict(success_contexts.most_common(5)),
            'peak_success_time': max(set(success_times), key=success_times.count) if success_times else None,
            'success_examples': [s['description'] for s in success_patterns[:5]]
        }
    
    def _generate_weekly_insights(self, patterns: Dict, memories: List[Memory]) -> str:
        """Generate natural language insights from patterns"""
        insights_parts = []
        
        # Recurring themes insight
        if patterns['recurring_themes']:
            top_themes = list(patterns['recurring_themes'].keys())[:3]
            insights_parts.append(f"Your week focused heavily on: {', '.join(top_themes)}")
        
        # Productivity insight
        if patterns['productivity_patterns']:
            prod = patterns['productivity_patterns']
            if prod.get('peak_hours'):
                insights_parts.append(f"You're most productive at {prod['peak_hours'][0]}:00")
            if prod.get('task_completion_rate'):
                rate_pct = int(prod['task_completion_rate'] * 100)
                insights_parts.append(f"Task completion rate: {rate_pct}%")
        
        # Collaboration insight
        if patterns['collaboration_patterns'] and patterns['collaboration_patterns']['frequent_collaborators']:
            top_person = patterns['collaboration_patterns']['frequent_collaborators'][0]
            insights_parts.append(f"Most frequent interaction: {top_person['person']} ({top_person['interaction_count']} times)")
        
        # Creative insight
        if patterns['creative_patterns'] and patterns['creative_patterns']['peak_creative_hour'] is not None:
            insights_parts.append(f"Creative peak at {patterns['creative_patterns']['peak_creative_hour']}:00")
        
        # Stress insight
        if patterns['stress_triggers'] and patterns['stress_triggers']['stress_count'] > 3:
            triggers = list(patterns['stress_triggers']['stress_triggers'].keys())[:2]
            if triggers:
                insights_parts.append(f"Stress triggers: {', '.join(triggers)}")
        
        # Success insight
        if patterns['success_patterns'] and patterns['success_patterns']['success_count'] > 0:
            insights_parts.append(f"{patterns['success_patterns']['success_count']} successes this week")
        
        # Combine insights
        if insights_parts:
            prompt = f"""
            Create a coherent paragraph summarizing these weekly insights:
            {chr(10).join('- ' + i for i in insights_parts)}
            
            Write 2-3 sentences that connect these observations into meaningful patterns.
            Focus on actionable observations.
            """
            
            try:
                result = self.extractor.extract(prompt)
                return result.get('insights', result.get('summary', '. '.join(insights_parts)))
            except:
                return '. '.join(insights_parts)
        
        return "Week analyzed successfully."
    
    def _generate_recommendations(self, patterns: Dict) -> List[str]:
        """Generate actionable recommendations based on patterns"""
        recommendations = []
        
        # Productivity recommendations
        if patterns['productivity_patterns']:
            prod = patterns['productivity_patterns']
            if prod.get('peak_hours'):
                recommendations.append(f"Schedule important work during your peak hours: {', '.join(str(h) + ':00' for h in prod['peak_hours'][:2])}")
            
            if prod.get('task_completion_rate', 0) < 0.5:
                recommendations.append("Consider breaking down tasks into smaller, more manageable pieces")
        
        # Collaboration recommendations
        if patterns['collaboration_patterns']:
            collab = patterns['collaboration_patterns']
            if collab.get('average_interactions_per_person', 0) < 2:
                recommendations.append("Increase follow-up frequency with key collaborators")
        
        # Blocker recommendations
        if patterns['blocker_patterns']:
            blockers = patterns['blocker_patterns']
            if blockers.get('resolved_count', 0) < blockers.get('blocker_count', 0) / 2:
                recommendations.append("Focus on resolving blockers more quickly - many remain unresolved")
        
        # Creative recommendations
        if patterns['creative_patterns']:
            creative = patterns['creative_patterns']
            if creative.get('peak_creative_hour') is not None:
                recommendations.append(f"Protect your creative time at {creative['peak_creative_hour']}:00 for ideation")
        
        # Stress recommendations
        if patterns['stress_triggers']:
            stress = patterns['stress_triggers']
            if stress.get('stress_count', 0) > 5:
                triggers = list(stress.get('stress_triggers', {}).keys())[:2]
                if triggers:
                    recommendations.append(f"Address recurring stressors: {', '.join(triggers)}")
        
        # Theme recommendations
        if patterns['recurring_themes']:
            declining_themes = [theme for theme, data in patterns['recurring_themes'].items() 
                              if data.get('trend') == 'decreasing']
            if declining_themes:
                recommendations.append(f"Revisit declining focus areas: {', '.join(declining_themes[:2])}")
        
        return recommendations[:5]  # Top 5 recommendations
    
    def _store_patterns(self, data: Dict):
        """Store weekly patterns in database"""
        query = """
            INSERT INTO weekly_patterns (
                week_number, year, patterns, insights, recommendations,
                recurring_themes, productivity_patterns, collaboration_patterns,
                decision_patterns, blocker_patterns, creative_patterns,
                stress_triggers, success_patterns, source_consolidation_ids
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        values = (
            data['week_number'],
            data['year'],
            json.dumps(data['patterns']),
            data['insights'],
            json.dumps(data['recommendations']),
            json.dumps(data['recurring_themes']),
            json.dumps(data['productivity_patterns']),
            json.dumps(data['collaboration_patterns']),
            json.dumps(data['decision_patterns']),
            json.dumps(data['blocker_patterns']),
            json.dumps(data['creative_patterns']),
            json.dumps(data['stress_triggers']),
            json.dumps(data['success_patterns']),
            json.dumps(data['source_consolidation_ids'])
        )
        
        self.db.conn.execute(query, values)
        self.db.conn.commit()
    
    def analyze_recent_weeks(self, weeks: int = 4):
        """Analyze the last N weeks"""
        for i in range(weeks):
            target_date = datetime.now() - timedelta(weeks=i)
            week_number = target_date.isocalendar()[1]
            year = target_date.year
            
            try:
                self.identify_patterns(week_number, year)
            except Exception as e:
                print(f"Failed to analyze week {week_number}/{year}: {e}")