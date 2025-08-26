"""Search functionality for memories"""

from typing import List, Optional
from ..storage import Database, Memory


class MemorySearch:
    """Search and retrieve memories"""
    
    def __init__(self, db: Optional[Database] = None):
        """Initialize search engine"""
        self.db = db or Database()
    
    def search(self, query: str, limit: int = 20) -> List[Memory]:
        """Search memories using various strategies"""
        # For now, use database search
        # Later we can add vector search, semantic search, etc.
        return self.db.search_memories(query, limit)
    
    def get_recent(self, limit: int = 20) -> List[Memory]:
        """Get recent memories"""
        return self.db.get_recent_memories(limit)
    
    def get_by_type(self, thought_type: str, limit: int = 20) -> List[Memory]:
        """Get memories by thought type"""
        # This could be optimized with a specific query
        all_memories = self.db.get_recent_memories(limit * 2)
        return [m for m in all_memories if m.thought_type == thought_type][:limit]
    
    def get_by_project(self, project: str, limit: int = 20) -> List[Memory]:
        """Get memories related to a project"""
        # Search in extracted data for project mentions
        all_memories = self.search(project, limit * 2)
        results = []
        
        for memory in all_memories:
            if memory.extracted_data:
                projects = memory.extracted_data.get('projects', [])
                if any(project.lower() in p.lower() for p in projects):
                    results.append(memory)
                elif project.lower() in memory.raw_text.lower():
                    results.append(memory)
        
        return results[:limit]
    
    def get_by_person(self, person: str, limit: int = 20) -> List[Memory]:
        """Get memories related to a person"""
        # Search in extracted data for person mentions
        all_memories = self.search(person, limit * 2)
        results = []
        
        for memory in all_memories:
            if memory.extracted_data:
                people = memory.extracted_data.get('people', [])
                if any(person.lower() in p.lower() for p in people):
                    results.append(memory)
                elif person.lower() in memory.raw_text.lower():
                    results.append(memory)
        
        return results[:limit]