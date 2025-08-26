"""Semantic search using vector embeddings"""

from typing import List, Optional, Dict, Any
from ..storage import Database, Memory
from ..embeddings import EmbeddingGenerator, VectorStore


class SemanticSearch:
    """Semantic search for memories using vector similarity"""
    
    def __init__(self, db: Optional[Database] = None,
                 embedding_generator: Optional[EmbeddingGenerator] = None,
                 vector_store: Optional[VectorStore] = None):
        """Initialize semantic search
        
        Args:
            db: Database instance
            embedding_generator: Embedding generator instance
            vector_store: Vector store instance
        """
        self.db = db or Database()
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        self.vector_store = vector_store or VectorStore()
    
    def search(self, query: str, limit: int = 10, 
               filter_type: Optional[str] = None,
               filter_source: Optional[str] = None) -> List[Memory]:
        """Search for semantically similar memories
        
        Args:
            query: Natural language query
            limit: Maximum number of results
            filter_type: Optional filter by thought type
            filter_source: Optional filter by source (text/voice)
            
        Returns:
            List of Memory objects sorted by relevance
        """
        # Generate embedding for query
        query_embedding = self.embedding_generator.generate(query)
        
        # Build filter conditions if provided
        where_filter = {}
        if filter_type:
            where_filter['thought_type'] = filter_type
        if filter_source:
            where_filter['source'] = filter_source
        
        # Search vector store
        results = self.vector_store.search(
            query_embedding=query_embedding,
            limit=limit,
            where=where_filter if where_filter else None
        )
        
        # Fetch full memory objects from database
        memories = []
        for result in results:
            memory_uuid = result['id']
            memory = self.db.get_memory_by_uuid(memory_uuid)
            if memory:
                # Add relevance score to memory object
                memory.relevance_score = result['score']
                memories.append(memory)
        
        return memories
    
    def find_related(self, memory: Memory, limit: int = 5) -> List[Memory]:
        """Find memories related to a given memory
        
        Args:
            memory: Memory to find relations for
            limit: Maximum number of related memories
            
        Returns:
            List of related Memory objects
        """
        # Get embedding for this memory from vector store
        memory_uuid = memory.uuid or str(memory.id)
        stored_memory = self.vector_store.get_memory(memory_uuid)
        
        if not stored_memory or not stored_memory.get('embedding'):
            # Generate embedding if not stored
            embedding_text = memory.raw_text
            if memory.summary and memory.summary != memory.raw_text[:100]:
                embedding_text = f"{memory.summary}\n\n{memory.raw_text}"
            embedding = self.embedding_generator.generate(embedding_text)
        else:
            embedding = stored_memory['embedding']
        
        # Search for similar memories (excluding the original)
        results = self.vector_store.search(
            query_embedding=embedding,
            limit=limit + 1  # Get one extra in case we need to exclude the original
        )
        
        # Fetch full memory objects, excluding the original
        memories = []
        for result in results:
            if result['id'] != memory_uuid:
                related_memory = self.db.get_memory_by_uuid(result['id'])
                if related_memory:
                    related_memory.relevance_score = result['score']
                    memories.append(related_memory)
                    if len(memories) >= limit:
                        break
        
        return memories
    
    def search_by_context(self, people: Optional[List[str]] = None,
                         topics: Optional[List[str]] = None,
                         thought_type: Optional[str] = None,
                         limit: int = 10) -> List[Memory]:
        """Search memories by contextual filters
        
        Args:
            people: List of people names to filter by
            topics: List of topics to filter by
            thought_type: Type of thought to filter by
            limit: Maximum number of results
            
        Returns:
            List of Memory objects matching the context
        """
        # Build a contextual query
        query_parts = []
        
        if people:
            query_parts.append(f"conversations with {', '.join(people)}")
        
        if topics:
            query_parts.append(f"about {', '.join(topics)}")
        
        if thought_type:
            query_parts.append(f"{thought_type}s")
        
        if not query_parts:
            # No context provided, return recent memories
            return self.db.get_recent_memories(limit)
        
        # Create natural language query
        query = " ".join(query_parts)
        
        # Search with filters
        return self.search(
            query=query,
            limit=limit,
            filter_type=thought_type
        )
    
    def get_memory_cluster(self, memory: Memory, radius: int = 100) -> List[Memory]:
        """Get a cluster of memories around a given memory
        
        This is useful for context-aware retrieval, finding the
        "neighborhood" of memories around a specific thought.
        
        Args:
            memory: Central memory
            radius: Number of neighboring memories to retrieve
            
        Returns:
            List of Memory objects in the cluster
        """
        # Get embedding for the central memory
        memory_uuid = memory.uuid or str(memory.id)
        stored_memory = self.vector_store.get_memory(memory_uuid)
        
        if not stored_memory or not stored_memory.get('embedding'):
            # Generate embedding if not stored
            embedding_text = memory.raw_text
            if memory.summary and memory.summary != memory.raw_text[:100]:
                embedding_text = f"{memory.summary}\n\n{memory.raw_text}"
            embedding = self.embedding_generator.generate(embedding_text)
        else:
            embedding = stored_memory['embedding']
        
        # Find neighboring memories
        results = self.vector_store.search(
            query_embedding=embedding,
            limit=radius
        )
        
        # Fetch full memory objects
        cluster = []
        for result in results:
            cluster_memory = self.db.get_memory_by_uuid(result['id'])
            if cluster_memory:
                cluster_memory.relevance_score = result['score']
                cluster.append(cluster_memory)
        
        return cluster
    
    def reindex_all(self):
        """Reindex all memories in the vector store
        
        This is useful after changing embedding models or
        recovering from corruption.
        """
        print("🔄 Reindexing all memories...")
        
        # Clear existing vector store
        self.vector_store.reset()
        
        # Get all memories from database
        memories = self.db.get_all_memories()
        
        for i, memory in enumerate(memories):
            try:
                # Create text for embedding
                embedding_text = memory.raw_text
                if memory.summary and memory.summary != memory.raw_text[:100]:
                    embedding_text = f"{memory.summary}\n\n{memory.raw_text}"
                
                # Generate embedding
                embedding = self.embedding_generator.generate(embedding_text)
                
                # Prepare metadata
                metadata = {
                    'thought_type': memory.thought_type or 'memory',
                    'source': memory.source,
                    'timestamp': memory.timestamp,
                    'status': memory.status
                }
                
                # Add extracted data to metadata
                if memory.extracted_data:
                    if memory.extracted_data.get('people'):
                        metadata['people'] = ','.join(memory.extracted_data['people'])
                    if memory.extracted_data.get('topics'):
                        metadata['topics'] = ','.join(memory.extracted_data['topics'])
                    if memory.extracted_data.get('actions'):
                        metadata['has_actions'] = True
                        metadata['action_count'] = len(memory.extracted_data['actions'])
                
                # Store in vector database
                memory_uuid = memory.uuid or str(memory.id)
                self.vector_store.add_memory(
                    memory_id=memory_uuid,
                    embedding=embedding,
                    metadata=metadata,
                    document=memory.raw_text
                )
                
                if (i + 1) % 10 == 0:
                    print(f"  Reindexed {i + 1}/{len(memories)} memories...")
                    
            except Exception as e:
                print(f"  Warning: Failed to reindex memory {memory.id}: {e}")
        
        print(f"✅ Reindexed {len(memories)} memories")