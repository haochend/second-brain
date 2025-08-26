#!/usr/bin/env python3
"""Test script for the memory system pipeline"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from memory.storage import Database, Memory
from memory.capture import Queue, TextCapture
from memory.processing import MemoryProcessor, LLMExtractor
from memory.query import MemorySearch


def test_pipeline():
    """Test the complete pipeline"""
    
    print("🧠 Testing Second Brain Pipeline\n")
    
    # Initialize components
    print("1️⃣  Initializing components...")
    db = Database()
    queue = Queue()
    extractor = LLMExtractor()
    processor = MemoryProcessor(queue, db, extractor)
    capture = TextCapture(queue, db)
    search = MemorySearch(db)
    print("   ✓ Components initialized\n")
    
    # Test memories
    test_thoughts = [
        "I need to review the pull request from Sarah about the authentication system",
        "Just had an idea: what if we use voice notes but with automatic structure extraction?",
        "Feeling overwhelmed with all the tasks today, but excited about the new project",
        "Meeting with John tomorrow at 2pm to discuss the API design",
        "Remember to buy coffee and milk on the way home",
        "The new architecture pattern we discussed yesterday could solve our scaling issues"
    ]
    
    # Capture thoughts
    print("2️⃣  Capturing test thoughts...")
    for thought in test_thoughts:
        item_id = capture.capture(thought)
        print(f"   ✓ Captured: {thought[:50]}...")
    print()
    
    # Check queue status
    stats = queue.get_stats()
    print(f"3️⃣  Queue status: {stats}\n")
    
    # Process the queue
    print("4️⃣  Processing memories (this may take a moment)...")
    process_stats = processor.process_batch(limit=10)
    print(f"   ✓ Processed: {process_stats}\n")
    
    # Test search
    print("5️⃣  Testing search...")
    
    # Search for "Sarah"
    results = search.search("Sarah", limit=5)
    print(f"   Search 'Sarah': Found {len(results)} results")
    if results:
        print(f"   → {results[0].summary or results[0].raw_text[:50]}")
    
    # Search for "idea"
    results = search.search("idea", limit=5)
    print(f"   Search 'idea': Found {len(results)} results")
    if results:
        print(f"   → {results[0].summary or results[0].raw_text[:50]}")
    print()
    
    # Get recent memories
    print("6️⃣  Recent memories:")
    recent = search.get_recent(limit=3)
    for memory in recent:
        print(f"   • [{memory.thought_type}] {memory.summary or memory.raw_text[:50]}")
        if memory.extracted_data:
            if memory.extracted_data.get('actions'):
                for action in memory.extracted_data['actions']:
                    print(f"     → Action: {action['text']}")
            if memory.extracted_data.get('people'):
                print(f"     → People: {', '.join(memory.extracted_data['people'])}")
    print()
    
    # Show extracted structure for one memory
    print("7️⃣  Example extraction detail:")
    if recent:
        memory = recent[0]
        print(f"   Raw text: {memory.raw_text}")
        print(f"   Thought type: {memory.thought_type}")
        print(f"   Summary: {memory.summary}")
        if memory.extracted_data:
            import json
            print("   Extracted data:")
            print(json.dumps(memory.extracted_data, indent=4))
    
    print("\n✅ Pipeline test complete!")
    
    # Cleanup
    db.close()


if __name__ == "__main__":
    try:
        test_pipeline()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()