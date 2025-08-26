"""LLM-based extraction for understanding memories"""

import json
import os
from typing import Dict, Any, Optional
import ollama
from datetime import datetime


class LLMExtractor:
    """Extract structured information from text using LLM"""
    
    def __init__(self, model_name: Optional[str] = None):
        """Initialize LLM extractor"""
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "llama3.2")
        self._check_ollama()
    
    def _check_ollama(self):
        """Check if Ollama is available"""
        try:
            # Check if model is available
            response = ollama.list()
            
            # Access models from the response object
            if hasattr(response, 'models'):
                models = response.models
            else:
                # Handle as iterator of tuples
                for key, value in response:
                    if key == 'models':
                        models = value
                        break
                else:
                    models = []
            
            # Get model names
            model_names = []
            for model in models:
                if hasattr(model, 'model'):
                    model_names.append(model.model)
                elif isinstance(model, dict):
                    model_names.append(model.get('name', ''))
            
            # Handle model names with/without tags
            base_model = self.model_name.split(':')[0]
            if not any(base_model in name for name in model_names):
                print(f"⚠️  Model '{self.model_name}' not found. Available models: {model_names}")
                print(f"Please run: ollama pull {self.model_name}")
                # Try falling back to a simpler model
                if any('llama' in name.lower() or 'gpt' in name.lower() for name in model_names):
                    for name in model_names:
                        if 'llama' in name.lower() or 'gpt' in name.lower():
                            self.model_name = name
                            print(f"Using available model: {self.model_name}")
                            break
        except Exception as e:
            print(f"⚠️  Ollama not available: {e}")
            print("Please install Ollama from https://ollama.ai")
    
    def extract(self, text: str) -> Dict[str, Any]:
        """Extract structured information from text"""
        
        prompt = f"""Analyze this thought and extract structured information.

Thought: "{text}"

Return a JSON object with this structure:
{{
    "thought_type": "action|idea|observation|question|feeling|decision|memory|mixed",
    "summary": "one line summary of the thought",
    "actions": [
        {{"text": "action to take", "priority": "high|medium|low", "deadline": "optional deadline"}}
    ],
    "people": ["names of people mentioned"],
    "projects": ["project names mentioned"],
    "topics": ["topics discussed"],
    "questions": [
        {{"question": "question asked", "context": "optional context"}}
    ],
    "ideas": [
        {{"idea": "the creative thought", "trigger": "what sparked it"}}
    ],
    "decisions": [
        {{"decision": "what was decided", "reason": "why"}}
    ],
    "observations": [
        {{"observation": "what was noticed", "context": "optional"}}
    ],
    "mood": {{
        "feeling": "emotional state if expressed",
        "energy": "high|normal|low|anxious|excited"
    }},
    "temporal": {{
        "dates": ["specific dates mentioned"],
        "relative": ["tomorrow", "next week", etc.]
    }}
}}

Only include fields that are actually present in the thought.
Arrays can be empty if nothing relevant is found.
Be concise and accurate.
"""

        try:
            # Call Ollama
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                # Note: format='json' doesn't work with all models
                options={
                    'temperature': 0.3,  # Lower temperature for more consistent extraction
                }
            )
            
            # Parse the response - extract JSON from the response
            response_text = response['response']
            
            # Try to find JSON in the response (might be wrapped in markdown code blocks)
            if '```json' in response_text:
                # Extract JSON from markdown code block
                start = response_text.find('```json') + 7
                end = response_text.find('```', start)
                json_str = response_text[start:end].strip()
            elif '```' in response_text:
                # Extract from generic code block
                start = response_text.find('```') + 3
                end = response_text.find('```', start)
                json_str = response_text[start:end].strip()
            elif '{' in response_text:
                # Try to find raw JSON
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                json_str = response_text[start:end]
            else:
                json_str = response_text
            
            # Parse the JSON
            result = json.loads(json_str)
            
            # Validate and clean the result
            return self._validate_extraction(result)
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse LLM response as JSON: {e}")
            # Return a minimal extraction
            return self._minimal_extraction(text)
        except Exception as e:
            print(f"LLM extraction failed: {e}")
            return self._minimal_extraction(text)
    
    def _validate_extraction(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean extraction results"""
        # Default structure
        defaults = {
            'thought_type': 'memory',
            'summary': '',
            'actions': [],
            'people': [],
            'projects': [],
            'topics': [],
            'questions': [],
            'ideas': [],
            'decisions': [],
            'observations': [],
            'mood': {},
            'temporal': {'dates': [], 'relative': []}
        }
        
        # Merge with defaults
        validated = defaults.copy()
        validated.update(result)
        
        # Ensure thought_type is valid
        valid_types = ['action', 'idea', 'observation', 'question', 'feeling', 'decision', 'memory', 'mixed']
        if validated['thought_type'] not in valid_types:
            validated['thought_type'] = 'memory'
        
        # Ensure summary exists
        if not validated['summary'] and result:
            # Try to generate a simple summary
            if validated['actions']:
                validated['summary'] = validated['actions'][0].get('text', '')[:100]
            elif validated['ideas']:
                validated['summary'] = validated['ideas'][0].get('idea', '')[:100]
            elif validated['questions']:
                validated['summary'] = validated['questions'][0].get('question', '')[:100]
        
        return validated
    
    def _minimal_extraction(self, text: str) -> Dict[str, Any]:
        """Fallback minimal extraction when LLM fails"""
        # Simple heuristics
        thought_type = 'memory'
        actions = []
        questions = []
        
        # Look for action indicators
        action_words = ['need to', 'should', 'must', 'will', 'have to', 'going to']
        for word in action_words:
            if word in text.lower():
                thought_type = 'action'
                actions.append({'text': text[:100], 'priority': 'medium'})
                break
        
        # Look for questions
        if '?' in text:
            thought_type = 'question'
            questions.append({'question': text[:100]})
        
        return {
            'thought_type': thought_type,
            'summary': text[:100],
            'actions': actions,
            'people': [],
            'projects': [],
            'topics': [],
            'questions': questions,
            'ideas': [],
            'decisions': [],
            'observations': [],
            'mood': {},
            'temporal': {'dates': [], 'relative': []}
        }