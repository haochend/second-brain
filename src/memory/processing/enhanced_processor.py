"""Enhanced background processor with semantic context and task detection"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
from ..capture import Queue
from ..storage import Database, Memory
from .extraction import LLMExtractor
from .transcription_mlx import MLXWhisperTranscriber
from ..embeddings import EmbeddingGenerator, VectorStore


class EnhancedMemoryProcessor:
    """Process queued memories with full semantic context and understanding"""
    
    def __init__(self, 
                 queue: Optional[Queue] = None, 
                 db: Optional[Database] = None, 
                 extractor: Optional[LLMExtractor] = None, 
                 transcriber: Optional[MLXWhisperTranscriber] = None,
                 embedding_generator: Optional[EmbeddingGenerator] = None,
                 vector_store: Optional[VectorStore] = None):
        """Initialize enhanced processor"""
        self.queue = queue or Queue()
        self.db = db or Database()
        self.extractor = extractor or LLMExtractor()
        self.transcriber = transcriber or MLXWhisperTranscriber()
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.vector_store = vector_store or VectorStore()
    
    def process_batch(self, limit: int = 10) -> Dict[str, int]:
        """Process a batch of pending memories with semantic understanding"""
        stats = {'processed': 0, 'failed': 0, 'tasks_detected': 0}
        
        # Get pending items from queue
        items = self.queue.get_pending(limit)
        
        if not items:
            return stats
        
        # Batch transcribe voice items first
        voice_items = [i for i in items if i['type'] == 'voice']
        if voice_items:
            self._batch_transcribe(voice_items)
        
        # Process each memory with full context
        for item in items:
            try:
                # Mark as processing
                self.queue.mark_processing(item['id'])
                
                # Get the corresponding memory
                memory = self._get_memory_for_item(item)
                if not memory:
                    self.queue.mark_failed(item['id'], "No matching database entry")
                    stats['failed'] += 1
                    continue
                
                # Get text content
                text = self._get_text_for_item(memory, item)
                if not text:
                    self.queue.mark_failed(item['id'], "No text content")
                    stats['failed'] += 1
                    continue
                
                # Step 1: Generate embedding for semantic search
                embedding = self.embedding_generator.generate(text)
                
                # Step 2: Find related memories through semantic search
                related_memories = self._find_related_memories(embedding, limit=20)
                
                # Step 3: Extract understanding WITH context from related memories
                context = self._build_context(related_memories)
                understanding = self._extract_with_context(text, context)
                
                # Step 4: Task detection happens HERE
                actionable = self._has_actionable_intent(understanding, text)
                if actionable:
                    stats['tasks_detected'] += 1
                    # Check if this updates an existing task
                    existing_task = self._find_similar_task(understanding, related_memories)
                    if existing_task:
                        self._update_task(existing_task, understanding)
                    else:
                        understanding['urgency'] = self._detect_urgency(understanding, text)
                    
                    # Check if this completes a previous task
                    self._check_task_completion(understanding, related_memories)
                
                # Step 5: Update memory with enriched data
                memory.raw_text = text
                memory.extracted_data = understanding
                memory.thought_type = understanding.get('thought_type', 'memory')
                memory.summary = understanding.get('summary', text[:100])
                memory.status = 'completed'
                memory.processed_at = datetime.now()
                
                # Add task-related fields
                memory.extracted_data['actionable'] = actionable
                memory.extracted_data['connections'] = [m.uuid for m in related_memories[:5]]  # Top 5 connections
                
                # Save to database
                self.db.update_memory(memory)
                
                # Store embedding with enhanced metadata
                self._store_enhanced_embedding(memory, embedding)
                
                # Mark as completed
                self.queue.mark_completed(item['id'])
                stats['processed'] += 1
                
            except Exception as e:
                print(f"Error processing item {item['id']}: {e}")
                self.queue.mark_failed(item['id'], str(e))
                stats['failed'] += 1
        
        # After storing all, build additional relationships
        self._build_relationships(items)
        
        return stats
    
    def _batch_transcribe(self, voice_items: List[Dict]):
        """Batch transcribe voice items for efficiency"""
        for item in voice_items:
            try:
                audio_path = item.get('metadata', {}).get('audio_path')
                if audio_path:
                    text = self.transcriber.transcribe(audio_path)
                    item['transcribed_text'] = text
                    
                    # Clean up audio if configured
                    if os.getenv('KEEP_AUDIO_AFTER_PROCESSING', 'false').lower() != 'true':
                        try:
                            os.remove(audio_path)
                        except:
                            pass
            except Exception as e:
                print(f"Failed to transcribe {audio_path}: {e}")
    
    def _get_memory_for_item(self, item: Dict) -> Optional[Memory]:
        """Get memory associated with queue item"""
        memory_uuid = item.get('metadata', {}).get('memory_uuid')
        
        if memory_uuid:
            return self.db.get_memory_by_uuid(memory_uuid)
        else:
            # Fallback for old items
            memories = self.db.get_pending_memories(1)
            return memories[0] if memories else None
    
    def _get_text_for_item(self, memory: Memory, item: Dict) -> str:
        """Get text content for processing"""
        if item['type'] == 'text':
            return memory.raw_text
        elif item['type'] == 'voice':
            return item.get('transcribed_text', '')
        return ''
    
    def _find_related_memories(self, embedding: List[float], limit: int = 20) -> List[Memory]:
        """Find semantically related memories"""
        try:
            # Search vector store for similar memories
            results = self.vector_store.search(embedding, k=limit)
            
            # Convert results to Memory objects
            related = []
            for result in results:
                memory_uuid = result['id']
                memory = self.db.get_memory_by_uuid(memory_uuid)
                if memory and memory.status == 'completed':
                    related.append(memory)
            
            return related
        except Exception as e:
            print(f"Warning: Semantic search failed: {e}")
            return []
    
    def _build_context(self, related_memories: List[Memory]) -> str:
        """Build context from related memories"""
        if not related_memories:
            return "No related context found."
        
        context_parts = []
        for i, mem in enumerate(related_memories[:10], 1):  # Top 10 for context
            summary = mem.summary or mem.raw_text[:100]
            context_parts.append(f"{i}. [{mem.timestamp.strftime('%Y-%m-%d')}] {summary}")
        
        return "\n".join(context_parts)
    
    def _extract_with_context(self, text: str, context: str) -> Dict[str, Any]:
        """Extract understanding with awareness of related memories"""
        prompt = f'''
        Current thought: "{text}"
        
        Related context from previous memories:
        {context}
        
        Understand this thought naturally. Extract whatever is meaningful:
        - thought_type: action/idea/observation/question/feeling/decision/memory
        - Is this actionable? (task, commitment, todo)
        - What entities are involved? (people, projects, topics)
        - Any decisions being made?
        - Questions or uncertainties?
        - Ideas or insights?
        - Emotional context?
        - Does this complete or update a previous thought?
        - summary: One-line summary
        
        Return as flexible JSON. Include only what's actually there.
        Don't force structure where it doesn't exist.
        '''
        
        try:
            # Use the existing extractor with our enhanced prompt
            extracted = self.extractor.extract(prompt)
            
            # Ensure we have the fields we need
            if 'thought_type' not in extracted:
                extracted['thought_type'] = 'memory'
            if 'summary' not in extracted:
                extracted['summary'] = text[:100]
            
            return extracted
        except Exception as e:
            print(f"Extraction failed: {e}")
            return {
                'thought_type': 'memory',
                'summary': text[:100],
                'raw_text': text
            }
    
    def _has_actionable_intent(self, understanding: Dict, text: str) -> bool:
        """Determine if this memory contains something to be done"""
        # Check understanding fields
        if understanding.get('actionable'):
            return True
        
        if understanding.get('thought_type') == 'action':
            return True
        
        if understanding.get('actions'):
            return True
        
        # Check for action words in text
        text_lower = text.lower()
        action_indicators = [
            'need to', 'should', 'must', 'will', 'going to',
            'todo', 'task', 'remember to', 'don\'t forget',
            'deadline', 'by tomorrow', 'by next week'
        ]
        
        for indicator in action_indicators:
            if indicator in text_lower:
                return True
        
        # Check for commitment or future action in understanding
        indicators = [
            understanding.get('contains_commitment'),
            understanding.get('future_action'),
            understanding.get('deadline_mentioned'),
            understanding.get('blocking_something')
        ]
        
        return any(indicators)
    
    def _detect_urgency(self, understanding: Dict, text: str) -> str:
        """Detect urgency level of an actionable item"""
        text_lower = text.lower()
        
        # High urgency indicators
        if any(word in text_lower for word in ['urgent', 'asap', 'immediately', 'critical', 'emergency']):
            return 'high'
        
        # Today/tomorrow
        if any(word in text_lower for word in ['today', 'tonight', 'tomorrow', 'by eod', 'by end of day']):
            return 'high'
        
        # This week
        if any(word in text_lower for word in ['this week', 'by friday', 'next few days']):
            return 'medium'
        
        # Default
        return 'normal'
    
    def _find_similar_task(self, understanding: Dict, related_memories: List[Memory]) -> Optional[Memory]:
        """Find if this is updating an existing task"""
        for memory in related_memories:
            if memory.extracted_data and memory.extracted_data.get('actionable'):
                # Check if it's about the same topic
                current_topics = set(understanding.get('topics', []))
                memory_topics = set(memory.extracted_data.get('topics', []))
                
                if current_topics & memory_topics:  # Overlapping topics
                    # Check if it's still open
                    if not memory.extracted_data.get('completed'):
                        return memory
        
        return None
    
    def _update_task(self, existing_task: Memory, new_understanding: Dict):
        """Update an existing task with new information"""
        # Merge the understanding
        existing_task.extracted_data.update(new_understanding)
        existing_task.updated_at = datetime.now()
        
        # Update in database
        self.db.update_memory(existing_task)
    
    def _check_task_completion(self, understanding: Dict, related_memories: List[Memory]):
        """Check if this memory marks a previous task as complete"""
        completion_indicators = ['done', 'completed', 'finished', 'resolved', 'fixed']
        
        text_lower = understanding.get('summary', '').lower()
        
        for indicator in completion_indicators:
            if indicator in text_lower:
                # Look for related actionable memories
                for memory in related_memories:
                    if memory.extracted_data and memory.extracted_data.get('actionable'):
                        # Mark as completed
                        memory.extracted_data['completed'] = True
                        memory.extracted_data['completed_at'] = datetime.now().isoformat()
                        self.db.update_memory(memory)
                        break
    
    def _store_enhanced_embedding(self, memory: Memory, embedding: List[float]):
        """Store embedding with enhanced metadata"""
        try:
            # Prepare enhanced metadata
            metadata = {
                'thought_type': memory.thought_type or 'memory',
                'source': memory.source,
                'timestamp': memory.timestamp.isoformat() if memory.timestamp else None,
                'status': memory.status,
                'actionable': memory.extracted_data.get('actionable', False),
                'urgency': memory.extracted_data.get('urgency', 'normal')
            }
            
            # Add extracted entities
            if memory.extracted_data:
                if memory.extracted_data.get('people'):
                    metadata['people'] = ','.join(memory.extracted_data['people'])
                if memory.extracted_data.get('topics'):
                    metadata['topics'] = ','.join(memory.extracted_data['topics'])
                if memory.extracted_data.get('projects'):
                    metadata['projects'] = ','.join(memory.extracted_data['projects'])
                if memory.extracted_data.get('actions'):
                    metadata['has_actions'] = True
                    metadata['action_count'] = len(memory.extracted_data['actions'])
            
            # Store in vector database
            self.vector_store.add_memory(
                memory_id=memory.uuid,
                embedding=embedding,
                metadata=metadata,
                document=memory.raw_text
            )
            
        except Exception as e:
            print(f"Warning: Failed to store embedding: {e}")
    
    def _build_relationships(self, processed_items: List[Dict]):
        """Build relationships between processed memories"""
        # This would analyze the batch for cross-references, follow-ups, etc.
        # For now, relationships are stored in the 'connections' field
        pass
    
    def get_actionable_memories(self) -> List[Memory]:
        """Get all actionable memories that aren't completed"""
        query = """
            SELECT * FROM memories 
            WHERE json_extract(extracted_data, '$.actionable') = 1
            AND (json_extract(extracted_data, '$.completed') IS NULL 
                 OR json_extract(extracted_data, '$.completed') = 0)
            ORDER BY 
                CASE json_extract(extracted_data, '$.urgency')
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    ELSE 3
                END,
                timestamp DESC
        """
        
        cursor = self.db.conn.execute(query)
        return [Memory.from_row(row) for row in cursor]
    
    def get_ai_context(self) -> Dict[str, Any]:
        """Get pre-processed context for AI tools"""
        return {
            'active_tasks': self.get_actionable_memories(),
            'recent_decisions': self.get_recent_decisions(),
            'current_context': self.get_relevant_context(),
            'blockers': self.get_blockers()
        }
    
    def get_recent_decisions(self) -> List[Memory]:
        """Get recent decision memories"""
        query = """
            SELECT * FROM memories 
            WHERE thought_type = 'decision'
            AND status = 'completed'
            ORDER BY timestamp DESC
            LIMIT 10
        """
        cursor = self.db.conn.execute(query)
        return [Memory.from_row(row) for row in cursor]
    
    def get_relevant_context(self) -> List[Memory]:
        """Get contextually relevant memories"""
        # Get memories from the last 24 hours
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        
        query = """
            SELECT * FROM memories 
            WHERE timestamp > ?
            AND status = 'completed'
            ORDER BY timestamp DESC
            LIMIT 20
        """
        cursor = self.db.conn.execute(query, (cutoff,))
        return [Memory.from_row(row) for row in cursor]
    
    def get_blockers(self) -> List[Memory]:
        """Get memories marked as blockers"""
        query = """
            SELECT * FROM memories 
            WHERE json_extract(extracted_data, '$.blocking_something') = 1
            AND (json_extract(extracted_data, '$.resolved') IS NULL 
                 OR json_extract(extracted_data, '$.resolved') = 0)
            ORDER BY timestamp DESC
        """
        cursor = self.db.conn.execute(query)
        return [Memory.from_row(row) for row in cursor]