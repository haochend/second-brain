"""Context detection for dynamic prompt selection"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class ContextDetector:
    """Detect context patterns for dynamic prompt selection"""
    
    def __init__(self):
        """Initialize context detector"""
        self.thresholds = {
            'high_stress': 5,
            'many_decisions': 10,
            'low_completion': 0.5,
            'heavy_collaboration': 8,
            'creative_burst': 5
        }
    
    def analyze_context(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze memory data to detect context patterns
        
        Args:
            memory_data: Dictionary containing:
                - memories: List of Memory objects
                - patterns: Extracted patterns
                - statistics: Computed statistics
        
        Returns:
            Context dictionary with detected patterns
        """
        context = {
            'timestamp': datetime.now().isoformat(),
            'memory_count': 0,
            'stress_count': 0,
            'decision_count': 0,
            'task_count': 0,
            'completed_count': 0,
            'task_completion_rate': 0.0,
            'people_mentioned': 0,
            'unique_people': [],
            'creative_insights': 0,
            'questions_raised': 0,
            'emotional_volatility': 0,
            'collaboration_heavy': False,
            'creative_burst': False,
            'high_stress_period': False
        }
        
        memories = memory_data.get('memories', [])
        context['memory_count'] = len(memories)
        
        if not memories:
            return context
        
        # Analyze each memory
        stress_indicators = ['stress', 'anxious', 'worried', 'overwhelmed', 'frustrated']
        creative_indicators = ['idea', 'insight', 'realized', 'discovered', 'breakthrough']
        people_set = set()
        emotions = []
        
        for memory in memories:
            # Check for stress
            text_lower = memory.raw_text.lower() if hasattr(memory, 'raw_text') else str(memory).lower()
            
            if any(indicator in text_lower for indicator in stress_indicators):
                context['stress_count'] += 1
            
            # Check for creative insights
            if any(indicator in text_lower for indicator in creative_indicators):
                context['creative_insights'] += 1
            
            # Count decisions, tasks, people
            if hasattr(memory, 'extracted_data') and memory.extracted_data:
                data = memory.extracted_data
                
                # Decisions
                if memory.thought_type == 'decision' or data.get('decisions'):
                    context['decision_count'] += 1
                
                # Tasks
                if data.get('actionable'):
                    context['task_count'] += 1
                    if data.get('completed'):
                        context['completed_count'] += 1
                
                # People
                if data.get('people'):
                    for person in data['people']:
                        people_set.add(person)
                
                # Questions
                if data.get('questions'):
                    context['questions_raised'] += len(data['questions'])
                
                # Emotions
                if data.get('mood'):
                    emotions.append(data['mood'])
        
        # Calculate derived metrics
        context['unique_people'] = list(people_set)
        context['people_mentioned'] = len(people_set)
        
        if context['task_count'] > 0:
            context['task_completion_rate'] = context['completed_count'] / context['task_count']
        
        # Calculate emotional volatility
        if emotions:
            unique_emotions = len(set(emotions))
            context['emotional_volatility'] = unique_emotions / len(emotions) if emotions else 0
        
        # Detect special contexts
        context['high_stress_period'] = context['stress_count'] >= self.thresholds['high_stress']
        context['collaboration_heavy'] = context['people_mentioned'] >= self.thresholds['heavy_collaboration']
        context['creative_burst'] = context['creative_insights'] >= self.thresholds['creative_burst']
        
        # Add patterns if available
        if 'patterns' in memory_data:
            self._add_pattern_context(context, memory_data['patterns'])
        
        return context
    
    def _add_pattern_context(self, context: Dict[str, Any], patterns: Dict[str, Any]):
        """Add pattern-based context information"""
        # Productivity patterns
        if 'productivity_patterns' in patterns:
            prod = patterns['productivity_patterns']
            context['peak_hours'] = prod.get('peak_hours', [])
            context['most_productive_day'] = prod.get('most_productive_day')
            
            # Update task completion rate if available
            if 'task_completion_rate' in prod:
                context['task_completion_rate'] = prod['task_completion_rate']
        
        # Stress patterns
        if 'stress_triggers' in patterns:
            stress = patterns['stress_triggers']
            context['stress_triggers'] = stress.get('stress_triggers', {})
            context['peak_stress_time'] = stress.get('peak_stress_time')
        
        # Collaboration patterns
        if 'collaboration_patterns' in patterns:
            collab = patterns['collaboration_patterns']
            context['frequent_collaborators'] = collab.get('frequent_collaborators', [])
        
        # Creative patterns
        if 'creative_patterns' in patterns:
            creative = patterns['creative_patterns']
            context['peak_creative_hour'] = creative.get('peak_creative_hour')
            context['creative_insights'] = creative.get('total_creative_insights', context['creative_insights'])
    
    def suggest_prompt_focus(self, context: Dict[str, Any]) -> str:
        """
        Suggest what the synthesis prompt should focus on based on context
        
        Returns:
            A string describing the recommended focus area
        """
        suggestions = []
        
        # High stress period
        if context.get('high_stress_period'):
            suggestions.append("stress_management")
        
        # Low task completion
        if context.get('task_completion_rate', 1) < self.thresholds['low_completion']:
            suggestions.append("productivity_blockers")
        
        # Many decisions
        if context.get('decision_count', 0) >= self.thresholds['many_decisions']:
            suggestions.append("decision_quality")
        
        # Heavy collaboration
        if context.get('collaboration_heavy'):
            suggestions.append("team_dynamics")
        
        # Creative burst
        if context.get('creative_burst'):
            suggestions.append("creative_exploration")
        
        # High emotional volatility
        if context.get('emotional_volatility', 0) > 0.7:
            suggestions.append("emotional_patterns")
        
        # Many questions
        if context.get('questions_raised', 0) > 10:
            suggestions.append("knowledge_gaps")
        
        # Default to balanced if no special context
        if not suggestions:
            suggestions.append("balanced_review")
        
        return suggestions[0] if suggestions else "balanced_review"
    
    def get_context_variables(self, context: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract variables for template interpolation
        
        Returns:
            Dictionary of variable names to values for prompt templates
        """
        variables = {
            'memory_count': str(context.get('memory_count', 0)),
            'stress_level': str(context.get('stress_count', 0)),
            'task_count': str(context.get('task_count', 0)),
            'completion_rate': f"{context.get('task_completion_rate', 0):.0%}",
            'people_count': str(context.get('people_mentioned', 0)),
            'decision_count': str(context.get('decision_count', 0)),
            'creative_count': str(context.get('creative_insights', 0)),
            'date': datetime.now().strftime('%Y-%m-%d'),
            'day_name': datetime.now().strftime('%A'),
        }
        
        # Add people names if available
        if context.get('unique_people'):
            variables['people_list'] = ', '.join(context['unique_people'][:5])
        
        # Add peak hours if available
        if context.get('peak_hours'):
            variables['peak_hours'] = ', '.join(str(h) for h in context['peak_hours'][:3])
        
        # Add stress triggers if available
        if context.get('stress_triggers'):
            triggers = list(context['stress_triggers'].keys())[:3]
            variables['stress_triggers'] = ', '.join(triggers)
        
        return variables
    
    def should_use_contextual_prompt(self, context: Dict[str, Any]) -> bool:
        """
        Determine if a contextual prompt should be used instead of default
        
        Returns:
            True if context warrants a special prompt
        """
        # Use contextual prompt if any special condition is met
        special_conditions = [
            context.get('high_stress_period', False),
            context.get('collaboration_heavy', False),
            context.get('creative_burst', False),
            context.get('task_completion_rate', 1) < self.thresholds['low_completion'],
            context.get('decision_count', 0) >= self.thresholds['many_decisions'],
            context.get('emotional_volatility', 0) > 0.7
        ]
        
        return any(special_conditions)