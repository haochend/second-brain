"""Pydantic models for structured extraction validation"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime


class Action(BaseModel):
    """An action or task to be done"""
    text: str = Field(..., min_length=1, description="The action to take")
    priority: Literal["high", "medium", "low"] = Field(default="medium")
    deadline: Optional[str] = Field(default=None, description="Optional deadline")
    
    @validator('text')
    def text_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Action text cannot be empty')
        return v.strip()


class EntityCollection(BaseModel):
    """Collection of entities mentioned"""
    people: List[str] = Field(default_factory=list, description="Names of people mentioned")
    projects: List[str] = Field(default_factory=list, description="Project names mentioned")
    topics: List[str] = Field(default_factory=list, description="Topics discussed")
    
    @validator('people', 'projects', 'topics', pre=True)
    def clean_list(cls, v):
        if not v:
            return []
        # Ensure it's a list and filter out empty strings
        if isinstance(v, str):
            v = [v]
        return [item.strip() for item in v if item and item.strip()]


class TemporalInfo(BaseModel):
    """Temporal references in the thought"""
    dates: List[str] = Field(default_factory=list, description="Specific dates mentioned")
    relative: List[str] = Field(default_factory=list, description="Relative time references like 'tomorrow', 'next week'")


class Question(BaseModel):
    """A question or wondering"""
    question: str = Field(..., min_length=1)
    context: Optional[str] = Field(default=None)


class Idea(BaseModel):
    """A creative thought or idea"""
    idea: str = Field(..., min_length=1)
    trigger: Optional[str] = Field(default=None, description="What sparked the idea")
    potential: Optional[str] = Field(default=None, description="Potential impact or use")


class Decision(BaseModel):
    """A decision that was made"""
    decision: str = Field(..., min_length=1)
    reason: Optional[str] = Field(default=None, description="Why the decision was made")
    date: Optional[str] = Field(default=None)


class Observation(BaseModel):
    """Something that was noticed or observed"""
    observation: str = Field(..., min_length=1)
    context: Optional[str] = Field(default=None)


class Mood(BaseModel):
    """Emotional state if expressed"""
    feeling: Optional[str] = Field(default=None)
    energy: Optional[Literal["high", "normal", "low", "anxious", "excited"]] = Field(default=None)


class ExtractedMemory(BaseModel):
    """Complete extracted memory structure with Pydantic validation"""
    
    thought_type: Literal["action", "idea", "observation", "question", "feeling", "decision", "memory", "mixed"] = Field(
        default="memory",
        description="The primary type of thought"
    )
    
    summary: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="One line summary of the thought"
    )
    
    # Optional collections - all default to empty
    actions: List[Action] = Field(default_factory=list)
    entities: Optional[EntityCollection] = Field(default_factory=EntityCollection)
    temporal: Optional[TemporalInfo] = Field(default_factory=TemporalInfo)
    questions: List[Question] = Field(default_factory=list)
    ideas: List[Idea] = Field(default_factory=list)
    decisions: List[Decision] = Field(default_factory=list)
    observations: List[Observation] = Field(default_factory=list)
    mood: Optional[Mood] = Field(default_factory=Mood)
    
    @validator('summary')
    def summary_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Summary cannot be empty')
        return v.strip()
    
    @validator('thought_type')
    def validate_thought_type_with_content(cls, v, values):
        """Ensure thought_type matches the content"""
        # If we have actions and thought_type isn't action/mixed, adjust it
        if 'actions' in values and values['actions'] and v not in ['action', 'mixed']:
            return 'action'
        if 'ideas' in values and values['ideas'] and v not in ['idea', 'mixed']:
            return 'idea'
        if 'questions' in values and values['questions'] and v not in ['question', 'mixed']:
            return 'question'
        return v
    
    def to_simple_dict(self) -> dict:
        """Convert to simplified dictionary format for storage"""
        # Convert nested models to dicts, removing empty lists and None values
        result = {}
        
        result['thought_type'] = self.thought_type
        result['summary'] = self.summary
        
        if self.actions:
            result['actions'] = [a.dict(exclude_none=True) for a in self.actions]
        
        # Handle entities
        if self.entities:
            entities_dict = self.entities.dict(exclude_none=True)
            # Only include if there's actual content
            if any(entities_dict.values()):
                result['entities'] = entities_dict
            
            # Also flatten common fields for backward compatibility
            if self.entities.people:
                result['people'] = self.entities.people
            if self.entities.projects:
                result['projects'] = self.entities.projects
            if self.entities.topics:
                result['topics'] = self.entities.topics
        
        # Handle temporal
        if self.temporal:
            temporal_dict = self.temporal.dict(exclude_none=True)
            if any(temporal_dict.values()):
                result['temporal'] = temporal_dict
        
        # Add other fields only if they have content
        if self.questions:
            result['questions'] = [q.dict(exclude_none=True) for q in self.questions]
        if self.ideas:
            result['ideas'] = [i.dict(exclude_none=True) for i in self.ideas]
        if self.decisions:
            result['decisions'] = [d.dict(exclude_none=True) for d in self.decisions]
        if self.observations:
            result['observations'] = [o.dict(exclude_none=True) for o in self.observations]
        
        if self.mood:
            mood_dict = self.mood.dict(exclude_none=True)
            if mood_dict:
                result['mood'] = mood_dict
        
        return result


# Example usage for prompting
EXTRACTION_SCHEMA = ExtractedMemory.schema()

# Simplified schema for LLM prompting
SIMPLIFIED_SCHEMA_PROMPT = """
{
    "thought_type": "action|idea|observation|question|feeling|decision|memory|mixed",
    "summary": "one line summary (required)",
    "actions": [{"text": "...", "priority": "high|medium|low", "deadline": "..."}],
    "entities": {
        "people": ["names"],
        "projects": ["project names"],
        "topics": ["topics"]
    },
    "temporal": {
        "dates": ["2024-01-15", "next Friday"],
        "relative": ["tomorrow", "next week"]
    },
    "questions": [{"question": "...", "context": "..."}],
    "ideas": [{"idea": "...", "trigger": "..."}],
    "decisions": [{"decision": "...", "reason": "..."}],
    "observations": [{"observation": "...", "context": "..."}],
    "mood": {"feeling": "...", "energy": "high|normal|low"}
}
"""