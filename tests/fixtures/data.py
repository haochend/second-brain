"""Test data generators and samples"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.memory.storage import Memory


class TestDataGenerator:
    """Generate test data for various scenarios"""
    
    THOUGHT_TYPES = ["action", "idea", "observation", "question", "feeling", "decision", "memory"]
    
    SAMPLE_ACTIONS = [
        "Review the pull request",
        "Send email to client",
        "Update documentation",
        "Fix the bug in authentication",
        "Schedule meeting with team",
        "Deploy to production",
        "Write unit tests",
        "Refactor the database module"
    ]
    
    SAMPLE_IDEAS = [
        "Use caching to improve performance",
        "Implement dark mode",
        "Add keyboard shortcuts",
        "Create a mobile app",
        "Use machine learning for predictions",
        "Simplify the user interface"
    ]
    
    SAMPLE_QUESTIONS = [
        "How does the authentication work?",
        "What's the best database for this?",
        "Should we use microservices?",
        "When is the deadline?",
        "Who is responsible for deployment?"
    ]
    
    SAMPLE_PEOPLE = ["Alice", "Bob", "Sarah", "John", "Emma", "Michael", "Lisa", "David"]
    
    SAMPLE_TOPICS = [
        "authentication", "database", "API", "frontend", "backend",
        "testing", "deployment", "security", "performance", "design",
        "documentation", "meeting", "planning", "review", "bug"
    ]
    
    @classmethod
    def generate_memory(cls, thought_type: str = None) -> Memory:
        """Generate a single random memory"""
        if thought_type is None:
            thought_type = random.choice(cls.THOUGHT_TYPES)
        
        # Generate appropriate content based on type
        if thought_type == "action":
            raw_text = random.choice(cls.SAMPLE_ACTIONS)
            summary = raw_text
            extracted_data = {
                'thought_type': 'action',
                'summary': summary,
                'actions': [
                    {
                        'text': raw_text,
                        'priority': random.choice(['high', 'medium', 'low'])
                    }
                ],
                'topics': random.sample(cls.SAMPLE_TOPICS, k=random.randint(1, 3))
            }
        
        elif thought_type == "idea":
            raw_text = random.choice(cls.SAMPLE_IDEAS)
            summary = raw_text
            extracted_data = {
                'thought_type': 'idea',
                'summary': summary,
                'ideas': [raw_text],
                'topics': random.sample(cls.SAMPLE_TOPICS, k=random.randint(1, 3))
            }
        
        elif thought_type == "question":
            raw_text = random.choice(cls.SAMPLE_QUESTIONS)
            summary = raw_text
            extracted_data = {
                'thought_type': 'question',
                'summary': summary,
                'questions': [raw_text],
                'topics': random.sample(cls.SAMPLE_TOPICS, k=random.randint(1, 2))
            }
        
        else:
            # Generic memory
            raw_text = f"This is a {thought_type} about {random.choice(cls.SAMPLE_TOPICS)}"
            summary = raw_text[:50]
            extracted_data = {
                'thought_type': thought_type,
                'summary': summary,
                'topics': random.sample(cls.SAMPLE_TOPICS, k=random.randint(1, 2))
            }
        
        # Add random people sometimes
        if random.random() > 0.5:
            extracted_data['people'] = random.sample(cls.SAMPLE_PEOPLE, k=random.randint(1, 2))
        
        # Create memory
        memory = Memory(
            raw_text=raw_text,
            source=random.choice(['text', 'voice']),
            thought_type=thought_type,
            summary=summary,
            status='completed',
            extracted_data=extracted_data,
            timestamp=datetime.now() - timedelta(days=random.randint(0, 30))
        )
        
        return memory
    
    @classmethod
    def generate_memories(cls, count: int = 10) -> List[Memory]:
        """Generate multiple random memories"""
        memories = []
        for _ in range(count):
            memories.append(cls.generate_memory())
        return memories
    
    @classmethod
    def generate_edge_case_memories(cls) -> List[Memory]:
        """Generate memories with edge cases for testing"""
        edge_cases = []
        
        # Very long text
        edge_cases.append(Memory(
            raw_text="This is a very long memory. " * 500,  # ~3500 characters
            summary="Very long memory",
            thought_type="observation"
        ))
        
        # Special characters
        edge_cases.append(Memory(
            raw_text="Test with special chars: \"quotes\", 'apostrophe's, & symbols, 日本語",
            summary="Special characters test",
            thought_type="memory"
        ))
        
        # Empty or minimal
        edge_cases.append(Memory(
            raw_text="",
            summary="Empty memory",
            thought_type="memory"
        ))
        
        # SQL injection attempt (should be handled safely)
        edge_cases.append(Memory(
            raw_text="'; DROP TABLE memories; --",
            summary="SQL injection test",
            thought_type="memory"
        ))
        
        # Unicode and emojis
        edge_cases.append(Memory(
            raw_text="Test with emojis 🚀 and unicode ñ é ü 中文",
            summary="Unicode test",
            thought_type="memory"
        ))
        
        # Nested JSON in extracted_data
        edge_cases.append(Memory(
            raw_text="Complex data structure",
            extracted_data={
                'nested': {
                    'level1': {
                        'level2': {
                            'data': 'deep nesting'
                        }
                    }
                },
                'list': [1, 2, {'key': 'value'}]
            },
            thought_type="memory"
        ))
        
        return edge_cases
    
    @classmethod
    def generate_search_test_set(cls) -> List[Memory]:
        """Generate memories specifically for testing search"""
        search_set = [
            Memory(
                raw_text="Meeting with Sarah about authentication system",
                summary="Auth meeting with Sarah",
                thought_type="action",
                extracted_data={
                    'people': ['Sarah'],
                    'topics': ['authentication', 'meeting']
                }
            ),
            Memory(
                raw_text="Implement OAuth2 authentication flow",
                summary="OAuth2 implementation",
                thought_type="action",
                extracted_data={
                    'topics': ['authentication', 'OAuth2', 'security']
                }
            ),
            Memory(
                raw_text="Sarah mentioned concerns about security",
                summary="Security concerns from Sarah",
                thought_type="observation",
                extracted_data={
                    'people': ['Sarah'],
                    'topics': ['security']
                }
            ),
            Memory(
                raw_text="Buy groceries: milk, eggs, bread",
                summary="Grocery shopping",
                thought_type="action",
                extracted_data={
                    'actions': [{'text': 'Buy groceries', 'priority': 'medium'}],
                    'topics': ['shopping', 'groceries']
                }
            ),
            Memory(
                raw_text="Interesting article about vector databases",
                summary="Vector database article",
                thought_type="observation",
                extracted_data={
                    'topics': ['database', 'vectors', 'search']
                }
            )
        ]
        
        return search_set


def generate_test_audio_data(duration_seconds: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate raw audio data for testing"""
    import struct
    import math
    
    # Generate a simple sine wave
    frequency = 440  # A4 note
    amplitude = 0.5
    
    samples = []
    for i in range(int(sample_rate * duration_seconds)):
        t = i / sample_rate
        value = amplitude * math.sin(2 * math.pi * frequency * t)
        # Convert to 16-bit PCM
        samples.append(struct.pack('<h', int(value * 32767)))
    
    return b''.join(samples)