"""Default prompt templates for memory synthesis"""


class DefaultPromptTemplates:
    """Collection of default prompt templates"""
    
    DAILY_DEFAULT = """Analyze today's memories and provide insights on:

1. UNFINISHED BUSINESS
   - What threads were started but not completed?
   - What commitments were made but not acted upon?
   - What questions were raised but not answered?

2. PATTERNS & ANOMALIES
   - What behaviors or thoughts were unusual compared to normal?
   - What patterns repeated from previous days?
   - What new patterns emerged?

3. ACTIONABLE INTELLIGENCE
   - What specific actions should be taken tomorrow based on today?
   - What decisions need to be made?
   - What follow-ups are required?

4. KNOWLEDGE GAPS
   - What topics came up repeatedly that I don't fully understand?
   - What skills or information would have helped today?

Be specific and reference actual memories. Focus on what's actionable, not generic observations."""

    WEEKLY_DEFAULT = """Analyze this week's patterns and provide strategic insights:

1. INVISIBLE PATTERNS
   - What am I doing repeatedly without realizing it?
   - What cycles or loops am I stuck in?
   - What patterns are helping vs hindering?

2. ALIGNMENT CHECK
   - Where are my actions misaligned with my stated goals?
   - What am I saying vs what am I doing?
   - What intentions didn't translate to action?

3. LEVERAGE POINTS
   - What 1-2 changes would have the biggest positive impact?
   - What's the root cause behind multiple surface issues?
   - What's working well that I should do more of?

4. STRATEGIC QUESTIONS
   - What questions should I be asking but aren't?
   - What assumptions need challenging?
   - What am I avoiding that needs attention?

Don't summarize—challenge and provoke deeper thinking. Be specific about patterns observed."""

    MONTHLY_DEFAULT = """Synthesize this month's memories into strategic knowledge:

1. EMERGENT THEMES
   - What larger themes have emerged across multiple weeks?
   - How have my priorities actually shifted (vs stated priorities)?
   - What unexpected connections exist between different areas?

2. LEARNING & GROWTH
   - What have I learned that changes how I approach things?
   - Where have I grown? Where have I stagnated?
   - What experiments worked? What failed? Why?

3. SYSTEM-LEVEL INSIGHTS
   - What systems or processes need redesigning?
   - What recurring problems have systemic causes?
   - What would an outside observer say about my patterns?

4. FORWARD LOOKING
   - Based on trends, what's likely to happen next month?
   - What should I start/stop/continue?
   - What capabilities do I need to develop?

Focus on insights that would only be visible at monthly scale, not weekly summaries."""

    # Contextual templates that activate based on conditions
    CONTEXTUAL_TEMPLATES = [
        {
            'when': 'stress_count > 5',
            'prompt': """This was a high-stress period. Focus on:
            1. What specific triggers caused stress?
            2. What coping mechanisms were used? Were they effective?
            3. What could have prevented or reduced the stress?
            4. What support or resources were missing?
            
            Be specific about stressors and solutions."""
        },
        {
            'when': 'decision_count > 10',
            'prompt': """Many decisions were made. Analyze:
            1. Which decisions were reactive vs strategic?
            2. What information was missing for better decisions?
            3. Which decisions contradict each other?
            4. What decision patterns are emerging?
            
            Focus on decision quality, not just quantity."""
        },
        {
            'when': 'task_completion_rate < 0.5',
            'prompt': """Low task completion detected. Investigate:
            1. What prevented tasks from being completed?
            2. Were tasks overambitious or poorly defined?
            3. What patterns exist in incomplete vs complete tasks?
            4. What system changes would improve completion?
            
            Be specific about blockers and solutions."""
        },
        {
            'when': 'collaboration_heavy',
            'prompt': """Heavy collaboration period. Examine:
            1. Who added energy vs drained it?
            2. What collaboration patterns were most effective?
            3. Where was communication clear vs confused?
            4. What team dynamics need attention?
            
            Focus on relationship and communication patterns."""
        },
        {
            'when': 'creative_burst',
            'prompt': """Creative period detected. Explore:
            1. What conditions enabled creativity?
            2. What patterns exist in creative vs non-creative times?
            3. How can these conditions be replicated?
            4. What ideas have the most potential?
            
            Focus on understanding and replicating creative conditions."""
        }
    ]
    
    # Alternative style templates for different approaches
    SOCRATIC_STYLE = """Using the Socratic method, ask questions about these memories:

Instead of telling me what happened, ask me:
- Why do you think you [specific pattern observed]?
- What would happen if you didn't [repeated behavior]?
- How does [action] serve you? How does it limit you?
- What are you not seeing about [situation]?
- If your best friend did this, what would you tell them?

Generate 5-7 probing questions that challenge assumptions and promote self-discovery."""

    COACHING_STYLE = """As an executive coach, analyze these memories:

OBSERVATIONS (without judgment):
- What patterns are clearly visible?
- What stated vs actual priorities emerge?

POWERFUL QUESTIONS:
- What would success look like here?
- What's the real challenge underneath?
- What are you tolerating that you shouldn't?

EXPERIMENTS TO TRY:
- Suggest 2-3 specific behavioral experiments
- Make them small, measurable, time-bound

Focus on empowerment and action, not problems."""

    SCIENTIST_STYLE = """Analyze these memories like a scientist:

HYPOTHESES:
- Based on patterns, form 2-3 testable hypotheses
- Example: "Meetings after 3pm result in lower follow-through"

EVIDENCE:
- What data supports or refutes each hypothesis?
- What data is missing to reach conclusions?

EXPERIMENTS:
- Design specific experiments to test hypotheses
- Include success metrics and timeline

CONCLUSIONS:
- What can be stated with confidence?
- What remains uncertain?

Be rigorous and evidence-based."""

    PHILOSOPHER_STYLE = """Reflect on these memories philosophically:

EXISTENTIAL THEMES:
- What does this reveal about your values?
- What meaning are you creating or avoiding?

PARADOXES:
- What contradictions exist in your thinking/actions?
- What tensions are you trying to resolve?

DEEPER QUESTIONS:
- What would [philosopher name] say about this?
- How does this connect to larger life questions?

WISDOM:
- What timeless principles apply here?
- What would you tell your younger self?

Focus on meaning and wisdom, not productivity."""

    @classmethod
    def get_template(cls, style: str = "default", consolidation_type: str = "daily") -> str:
        """Get a template by style and type"""
        style_map = {
            "default": {
                "daily": cls.DAILY_DEFAULT,
                "weekly": cls.WEEKLY_DEFAULT,
                "monthly": cls.MONTHLY_DEFAULT
            },
            "socratic": {"all": cls.SOCRATIC_STYLE},
            "coaching": {"all": cls.COACHING_STYLE},
            "scientist": {"all": cls.SCIENTIST_STYLE},
            "philosopher": {"all": cls.PHILOSOPHER_STYLE}
        }
        
        if style in style_map:
            templates = style_map[style]
            return templates.get(consolidation_type, templates.get("all", cls.DAILY_DEFAULT))
        
        return cls.DAILY_DEFAULT