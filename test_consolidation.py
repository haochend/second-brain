#!/usr/bin/env python3
"""Test script for the complete memory consolidation pipeline"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.memory.storage import Database, Memory
from src.memory.processing.enhanced_processor import EnhancedMemoryProcessor
from src.memory.consolidation import DailyConsolidator, WeeklyPatternRecognizer, KnowledgeSynthesizer
from src.memory.query.enhanced_search import EnhancedQueryInterface
from src.memory.capture import Queue


def test_pipeline():
    """Test the complete consolidation pipeline"""
    
    print("=" * 60)
    print("🧪 Testing Memory Consolidation Pipeline")
    print("=" * 60)
    
    # Initialize components
    print("\n📦 Initializing components...")
    db = Database()
    queue = Queue()
    processor = EnhancedMemoryProcessor(db=db, queue=queue)
    daily_consolidator = DailyConsolidator(db=db)
    weekly_patterns = WeeklyPatternRecognizer(db=db)
    knowledge_synthesizer = KnowledgeSynthesizer(db=db)
    query_interface = EnhancedQueryInterface(db=db)
    
    print("✓ Components initialized")
    
    # Step 1: Process any pending queue items
    print("\n1️⃣ Processing Queue")
    print("-" * 40)
    stats = processor.process_batch(limit=10)
    print(f"  • Processed: {stats['processed']}")
    print(f"  • Failed: {stats['failed']}")
    print(f"  • Tasks detected: {stats['tasks_detected']}")
    
    # Step 2: Show actionable memories
    print("\n2️⃣ Actionable Memories")
    print("-" * 40)
    actionable = processor.get_actionable_memories()
    if actionable:
        print(f"  Found {len(actionable)} actionable items:")
        for memory in actionable[:3]:
            print(f"  📋 {memory.summary or memory.raw_text[:60]}...")
            if memory.extracted_data and memory.extracted_data.get('urgency'):
                print(f"     Priority: {memory.extracted_data['urgency']}")
    else:
        print("  No actionable items found")
    
    # Step 3: Test daily consolidation
    print("\n3️⃣ Daily Consolidation")
    print("-" * 40)
    yesterday = datetime.now().date() - timedelta(days=1)
    
    try:
        result = daily_consolidator.consolidate_day(yesterday)
        if result:
            print(f"  ✓ Consolidated {result.get('memory_count', 0)} memories from {yesterday}")
            print(f"  📊 Importance score: {result.get('importance_score', 0):.1f}/10")
            
            if result.get('key_decisions'):
                print(f"  🎯 Key decisions: {len(result['key_decisions'])}")
            
            if result.get('main_topics'):
                topics = [t['topic'] for t in result['main_topics'][:3]]
                print(f"  📚 Main topics: {', '.join(topics)}")
    except Exception as e:
        print(f"  ⚠️ Consolidation skipped: {e}")
    
    # Step 4: Test weekly patterns
    print("\n4️⃣ Weekly Pattern Recognition")
    print("-" * 40)
    last_week = datetime.now() - timedelta(weeks=1)
    week_num = last_week.isocalendar()[1]
    year = last_week.year
    
    try:
        patterns = weekly_patterns.identify_patterns(week_num, year)
        if patterns:
            pattern_data = patterns.get('patterns', {})
            
            if pattern_data.get('recurring_themes'):
                print(f"  🔄 Recurring themes: {len(pattern_data['recurring_themes'])}")
                for theme, data in list(pattern_data['recurring_themes'].items())[:3]:
                    print(f"    • {theme}: {data['count']} occurrences ({data['trend']})")
            
            if pattern_data.get('productivity_patterns'):
                prod = pattern_data['productivity_patterns']
                print(f"  ⏰ Peak hours: {prod.get('peak_hours', [])}")
                print(f"  📈 Task completion rate: {prod.get('task_completion_rate', 0):.0%}")
            
            if patterns.get('recommendations'):
                print(f"  💡 Recommendations:")
                for rec in patterns['recommendations'][:3]:
                    print(f"    • {rec}")
    except Exception as e:
        print(f"  ⚠️ Pattern recognition skipped: {e}")
    
    # Step 5: Test knowledge synthesis
    print("\n5️⃣ Knowledge Synthesis")
    print("-" * 40)
    
    try:
        nodes = knowledge_synthesizer.build_knowledge_nodes(days=7)
        print(f"  🧠 Created {len(nodes)} knowledge nodes")
        
        if nodes:
            for node in nodes[:3]:
                print(f"  📌 {node['topic']}: {node['summary'][:80]}...")
                print(f"     Confidence: {node['confidence']:.2f}")
    except Exception as e:
        print(f"  ⚠️ Knowledge synthesis skipped: {e}")
    
    # Step 6: Test wisdom extraction
    print("\n6️⃣ Wisdom Extraction")
    print("-" * 40)
    
    try:
        wisdom_items = knowledge_synthesizer.extract_wisdom(months=1)
        print(f"  ✨ Extracted {len(wisdom_items)} wisdom items")
        
        for item in wisdom_items[:3]:
            print(f"  💎 {item['content'][:100]}...")
            print(f"     Type: {item['type']}, Confidence: {item.get('confidence', 0):.2f}")
    except Exception as e:
        print(f"  ⚠️ Wisdom extraction skipped: {e}")
    
    # Step 7: Test enhanced query interface
    print("\n7️⃣ Enhanced Query Interface")
    print("-" * 40)
    
    test_queries = [
        "What tasks do I have?",
        "Show me patterns from last week",
        "What have I learned?",
        "What did I do yesterday?"
    ]
    
    for query in test_queries:
        print(f"\n  🔍 Query: '{query}'")
        try:
            results = query_interface.query(query, limit=5)
            print(f"     Type: {results.get('type')}")
            
            # Show sample results based on type
            if results['type'] == 'tasks':
                active = results.get('active_tasks', [])
                print(f"     Active tasks: {len(active)}")
                if active:
                    print(f"     Sample: {active[0]['summary'][:60]}...")
                    
            elif results['type'] == 'patterns_and_wisdom':
                patterns = results.get('patterns', [])
                wisdom = results.get('wisdom', [])
                print(f"     Patterns found: {len(patterns)}")
                print(f"     Wisdom found: {len(wisdom)}")
                
            elif results['type'] == 'daily_consolidations':
                consolidations = results.get('consolidations', [])
                print(f"     Consolidations: {len(consolidations)}")
                if consolidations:
                    print(f"     Latest: {consolidations[0].get('date')}")
                    
            else:
                # Generic result count
                if 'merged' in results:
                    print(f"     Results: {len(results['merged'])}")
                
            # Show suggestions
            if results.get('suggestions'):
                print(f"     💡 Suggestions: {', '.join(results['suggestions'][:2])}")
                
        except Exception as e:
            print(f"     ❌ Query failed: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ Pipeline Test Complete!")
    print("=" * 60)
    
    # Show service control instructions
    print("\n📌 To run the service continuously:")
    print("   1. Install: ./scripts/service-control.sh install")
    print("   2. Status:  ./scripts/service-control.sh status")
    print("   3. Logs:    ./scripts/service-control.sh logs")
    print("\n📌 To run tasks manually:")
    print("   ./scripts/service-control.sh run queue     # Process queue")
    print("   ./scripts/service-control.sh run daily     # Daily consolidation")
    print("   ./scripts/service-control.sh run weekly    # Weekly patterns")
    print("   ./scripts/service-control.sh run knowledge # Knowledge synthesis")
    print("   ./scripts/service-control.sh run wisdom    # Wisdom extraction")


if __name__ == "__main__":
    test_pipeline()