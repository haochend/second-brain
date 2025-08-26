"""Improved LLM extraction with Pydantic validation and better prompting"""

import json
import os
from typing import Dict, Any, Optional
import ollama
from datetime import datetime
import re
from pydantic import ValidationError

from .extraction_models import ExtractedMemory, SIMPLIFIED_SCHEMA_PROMPT


class RobustLLMExtractor:
    """Extract structured information with validation and retries"""
    
    def __init__(self, model_name: Optional[str] = None):
        """Initialize LLM extractor"""
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "llama3.2")
        self._check_ollama()
    
    def _check_ollama(self):
        """Check if Ollama is available"""
        try:
            models = ollama.list()
            model_names = [m['name'] for m in models.get('models', [])]
            
            # Check if our model exists
            if not any(self.model_name in name for name in model_names):
                print(f"⚠️  Model '{self.model_name}' not found")
                available_models = [n for n in model_names if 'llama' in n.lower() or 'gpt' in n.lower()]
                if available_models:
                    print(f"Available models: {available_models}")
        except Exception as e:
            print(f"⚠️  Ollama check failed: {e}")
    
    def extract(self, text: str, max_retries: int = 3) -> Dict[str, Any]:
        """Extract with validation and retries"""
        
        for attempt in range(max_retries):
            try:
                # Try different prompting strategies based on attempt
                if attempt == 0:
                    # First attempt: detailed prompt with examples
                    result = self._extract_with_examples(text)
                elif attempt == 1:
                    # Second attempt: simplified prompt
                    result = self._extract_simple(text)
                else:
                    # Final attempt: minimal prompt
                    result = self._extract_minimal(text)
                
                # Validate with Pydantic
                validated = self._validate_extraction(result)
                return validated.to_simple_dict()
                
            except (ValidationError, json.JSONDecodeError) as e:
                if attempt == max_retries - 1:
                    print(f"Extraction failed after {max_retries} attempts: {e}")
                    return self._fallback_extraction(text)
                continue
            except Exception as e:
                print(f"Unexpected error: {e}")
                return self._fallback_extraction(text)
    
    def _extract_with_examples(self, text: str) -> dict:
        """Full extraction with examples"""
        prompt = f'''Analyze this thought and extract structured information.

INPUT: "{text}"

INSTRUCTIONS:
1. Identify the type of thought (action, idea, question, observation, etc.)
2. Create a one-line summary
3. Extract any actions, people, dates, ideas, questions, etc.
4. Return ONLY valid JSON

EXAMPLES:

Input: "I need to review Sarah's PR about authentication by Friday"
Output: {{"thought_type": "action", "summary": "Review Sarah's authentication PR by Friday", "actions": [{{"text": "Review Sarah's PR about authentication", "priority": "high", "deadline": "Friday"}}], "entities": {{"people": ["Sarah"], "topics": ["authentication", "PR review"]}}}}

Input: "Had an idea: we could use vector embeddings for search"
Output: {{"thought_type": "idea", "summary": "Use vector embeddings to improve search", "ideas": [{{"idea": "Use vector embeddings for search", "trigger": "thinking about search improvement"}}], "entities": {{"topics": ["vector embeddings", "search"]}}}}

NOW EXTRACT FROM THE INPUT:
{SIMPLIFIED_SCHEMA_PROMPT}

Return ONLY the JSON object, no markdown, no explanation.'''
        
        response = ollama.generate(
            model=self.model_name,
            prompt=prompt,
            options={
                'temperature': 0.2,  # Lower for more consistent output
                'top_p': 0.9,
                'num_predict': 500,  # Limit output length
            }
        )
        
        return self._parse_json_response(response['response'])
    
    def _extract_simple(self, text: str) -> dict:
        """Simplified extraction"""
        prompt = f'''Extract structured data from: "{text}"

Return JSON with:
- thought_type: action|idea|observation|question|decision|memory
- summary: one line summary
- actions: [{{"text": "...", "priority": "high|medium|low"}}] (if any)
- entities: {{"people": [...], "topics": [...]}} (if any)
- ideas/questions/observations as appropriate

IMPORTANT: Return ONLY valid JSON, no other text.'''
        
        response = ollama.generate(
            model=self.model_name,
            prompt=prompt,
            options={'temperature': 0.3}
        )
        
        return self._parse_json_response(response['response'])
    
    def _extract_minimal(self, text: str) -> dict:
        """Minimal extraction prompt"""
        prompt = f'''JSON extraction from: "{text}"
        
{{
  "thought_type": "...",
  "summary": "...",
  "actions": [...],
  "entities": {{...}}
}}'''
        
        response = ollama.generate(
            model=self.model_name,
            prompt=prompt,
            options={'temperature': 0.1}
        )
        
        return self._parse_json_response(response['response'])
    
    def _parse_json_response(self, response_text: str) -> dict:
        """Parse JSON from LLM response, handling various formats"""
        
        # Remove any markdown code blocks
        if '```json' in response_text:
            start = response_text.find('```json') + 7
            end = response_text.find('```', start)
            if end > start:
                response_text = response_text[start:end]
        elif '```' in response_text:
            start = response_text.find('```') + 3
            end = response_text.find('```', start)
            if end > start:
                response_text = response_text[start:end]
        
        # Clean up the text
        response_text = response_text.strip()
        
        # Try to find JSON object
        if '{' in response_text:
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if end > start:
                response_text = response_text[start:end]
        
        # Fix common JSON issues
        response_text = self._fix_json_issues(response_text)
        
        # Parse JSON
        return json.loads(response_text)
    
    def _fix_json_issues(self, json_str: str) -> str:
        """Fix common JSON formatting issues"""
        
        # Fix single quotes (simple approach)
        # This is risky but works for simple cases
        if '"' not in json_str and "'" in json_str:
            json_str = json_str.replace("'", '"')
        
        # Fix trailing commas
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Ensure boolean values are lowercase
        json_str = json_str.replace('True', 'true').replace('False', 'false')
        json_str = json_str.replace('None', 'null')
        
        return json_str
    
    def _validate_extraction(self, result: dict) -> ExtractedMemory:
        """Validate extraction result with Pydantic"""
        
        # Handle different field formats
        # Some models might return 'people' directly instead of nested in 'entities'
        if 'people' in result and 'entities' not in result:
            result['entities'] = {
                'people': result.pop('people', []),
                'projects': result.pop('projects', []),
                'topics': result.pop('topics', [])
            }
        
        # Ensure summary exists
        if 'summary' not in result or not result['summary']:
            # Try to generate from other fields
            if result.get('actions'):
                result['summary'] = result['actions'][0].get('text', '')[:100]
            else:
                result['summary'] = "Memory captured"
        
        # Create and validate with Pydantic
        return ExtractedMemory(**result)
    
    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """Fallback extraction using simple heuristics"""
        
        # Determine thought type
        thought_type = 'memory'
        actions = []
        questions = []
        ideas = []
        
        text_lower = text.lower()
        
        # Check for actions
        action_indicators = ['need to', 'should', 'must', 'will', 'have to', 'going to', 'todo', 'task']
        if any(indicator in text_lower for indicator in action_indicators):
            thought_type = 'action'
            actions.append({'text': text[:200], 'priority': 'medium'})
        
        # Check for questions
        if '?' in text:
            thought_type = 'question'
            questions.append({'question': text[:200]})
        
        # Check for ideas
        idea_indicators = ['idea', 'what if', 'could', 'maybe', 'perhaps', 'thinking']
        if any(indicator in text_lower for indicator in idea_indicators):
            thought_type = 'idea'
            ideas.append({'idea': text[:200]})
        
        # Extract people (simple capitalized word detection)
        words = text.split()
        people = [w for w in words if w[0].isupper() and len(w) > 2 and w not in ['I', 'The', 'This', 'That']]
        
        # Build result
        result = {
            'thought_type': thought_type,
            'summary': text[:100],
            'actions': actions,
            'questions': questions,
            'ideas': ideas,
            'entities': {
                'people': people[:3],  # Limit to 3 people
                'projects': [],
                'topics': []
            },
            'temporal': {
                'dates': [],
                'relative': []
            }
        }
        
        # Look for temporal references
        if 'tomorrow' in text_lower:
            result['temporal']['relative'].append('tomorrow')
        if 'today' in text_lower:
            result['temporal']['relative'].append('today')
        if 'friday' in text_lower or 'monday' in text_lower:
            result['temporal']['relative'].append(text_lower.split()[0])
        
        try:
            validated = ExtractedMemory(**result)
            return validated.to_simple_dict()
        except ValidationError:
            # Ultimate fallback
            return {
                'thought_type': 'memory',
                'summary': text[:100],
                'actions': [],
                'entities': {'people': [], 'projects': [], 'topics': []},
                'temporal': {'dates': [], 'relative': []},
                'questions': [],
                'ideas': [],
                'decisions': [],
                'observations': [],
                'mood': {}
            }