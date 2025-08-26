"""Background processor for memory queue"""

from datetime import datetime
from typing import Optional, Dict
from ..capture import Queue
from ..storage import Database, Memory
from .extraction import LLMExtractor
from .transcription_mlx import MLXWhisperTranscriber


class MemoryProcessor:
    """Process queued memories"""
    
    def __init__(self, queue: Optional[Queue] = None, db: Optional[Database] = None, 
                 extractor: Optional[LLMExtractor] = None, transcriber: Optional[MLXWhisperTranscriber] = None):
        """Initialize processor"""
        self.queue = queue or Queue()
        self.db = db or Database()
        self.extractor = extractor or LLMExtractor()
        self.transcriber = transcriber or MLXWhisperTranscriber()
    
    def process_batch(self, limit: int = 10) -> Dict[str, int]:
        """Process a batch of pending memories"""
        stats = {'processed': 0, 'failed': 0, 'skipped': 0}
        
        # Get pending items from queue
        items = self.queue.get_pending(limit)
        
        for item in items:
            try:
                # Mark as processing
                self.queue.mark_processing(item['id'])
                
                # Get the corresponding memory from database
                # For voice items, use the memory_uuid from metadata
                memory_uuid = item.get('metadata', {}).get('memory_uuid')
                
                if memory_uuid:
                    # Get memory by UUID
                    memory = self.db.get_memory_by_uuid(memory_uuid)
                    if not memory:
                        self.queue.mark_failed(item['id'], f"No memory found with UUID: {memory_uuid}")
                        stats['failed'] += 1
                        continue
                else:
                    # Fallback to old behavior for text items
                    memories = self.db.get_pending_memories(1)
                    if not memories:
                        self.queue.mark_failed(item['id'], "No matching database entry")
                        stats['failed'] += 1
                        continue
                    memory = memories[0]
                
                # Process based on type
                if item['type'] == 'text':
                    self._process_text_memory(memory, item)
                elif item['type'] == 'voice':
                    self._process_voice_memory(memory, item)
                else:
                    self.queue.mark_failed(item['id'], f"Unknown type: {item['type']}")
                    stats['skipped'] += 1
                    continue
                
                # Mark as completed
                self.queue.mark_completed(item['id'])
                stats['processed'] += 1
                
            except Exception as e:
                print(f"Error processing item {item['id']}: {e}")
                self.queue.mark_failed(item['id'], str(e))
                stats['failed'] += 1
        
        return stats
    
    def _process_text_memory(self, memory: Memory, queue_item: Dict):
        """Process a text memory"""
        # Extract structured data using LLM
        extracted = self.extractor.extract(memory.raw_text)
        
        # Update memory with extracted data
        memory.extracted_data = extracted
        memory.thought_type = extracted.get('thought_type', 'memory')
        memory.summary = extracted.get('summary', memory.raw_text[:100])
        memory.status = 'completed'
        memory.processed_at = datetime.now()
        
        # Save to database
        self.db.update_memory(memory)
    
    def _process_voice_memory(self, memory: Memory, queue_item: Dict):
        """Process a voice memory"""
        # Get audio path from queue item
        audio_path = queue_item.get('metadata', {}).get('audio_path')
        
        if not audio_path:
            raise ValueError("No audio path provided for voice memory")
        
        # Transcribe audio to text
        text = self.transcriber.transcribe(audio_path)
        
        # Update memory with transcribed text
        memory.raw_text = text
        
        # Now process as text
        extracted = self.extractor.extract(text)
        
        # Update memory with extracted data
        memory.extracted_data = extracted
        memory.thought_type = extracted.get('thought_type', 'memory')
        memory.summary = extracted.get('summary', text[:100])
        memory.status = 'completed'
        memory.processed_at = datetime.now()
        
        # Add audio path to metadata
        if not memory.extracted_data:
            memory.extracted_data = {}
        memory.extracted_data['audio_path'] = audio_path
        
        # Save to database
        self.db.update_memory(memory)
    
    def process_single(self, text: str) -> Memory:
        """Process a single text immediately (for testing)"""
        # Create memory
        memory = Memory(
            raw_text=text,
            source='text',
            timestamp=datetime.now()
        )
        
        # Extract
        extracted = self.extractor.extract(text)
        
        # Update with extraction
        memory.extracted_data = extracted
        memory.thought_type = extracted.get('thought_type', 'memory')
        memory.summary = extracted.get('summary', text[:100])
        memory.status = 'completed'
        memory.processed_at = datetime.now()
        
        # Save to database
        memory_id = self.db.add_memory(memory)
        memory.id = memory_id
        
        return memory