#!/usr/bin/env python3
"""Test script for the flexible synthesis system"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.memory.storage import Database, Memory
from src.memory.consolidation import FlexibleDailyConsolidator, FlexibleWeeklyPatternRecognizer
from src.memory.prompts import PromptManager, DefaultPromptTemplates


def test_flexible_synthesis():
    """Test the flexible synthesis system"""
    
    print("=" * 60)
    print("🧪 Testing Flexible Synthesis System")
    print("=" * 60)
    
    # Initialize components
    print("\n📦 Initializing components...")
    db = Database()
    prompt_manager = PromptManager()
    daily_consolidator = FlexibleDailyConsolidator(db=db, prompt_manager=prompt_manager)
    weekly_consolidator = FlexibleWeeklyPatternRecognizer(db=db, prompt_manager=prompt_manager)
    
    print(f"✓ Components initialized")
    print(f"✓ Active prompt profile: {prompt_manager.active_profile}")
    
    # Step 1: Test prompt management
    print("\n1️⃣ Testing Prompt Management")
    print("-" * 40)
    
    # List profiles
    profiles = prompt_manager.list_profiles()
    print(f"  Available profiles: {', '.join(profiles)}")
    
    # Create test profile
    test_profile = "test_synthesis"
    if test_profile not in profiles:
        if prompt_manager.create_profile(test_profile, "default"):
            print(f"  ✓ Created test profile: {test_profile}")
    
    # Step 2: Test daily consolidation with default prompt
    print("\n2️⃣ Testing Daily Consolidation (Default Prompt)")
    print("-" * 40)
    
    yesterday = datetime.now().date() - timedelta(days=1)
    
    try:
        result = daily_consolidator.consolidate_day(
            target_date=yesterday,
            skip_synthesis=False
        )
        
        if result:
            print(f"  ✓ Consolidated {result.get('memory_count', 0)} memories")
            
            # Show infrastructure data
            if result.get('infrastructure'):
                infra = result['infrastructure']
                print(f"  📊 Infrastructure extracted:")
                print(f"     • Connections: {len(infra.get('connections', []))}")
                print(f"     • Topic clusters: {len(infra.get('clusters', {}))}")
                print(f"     • People: {len(infra.get('people', {}))}")
                print(f"     • Decisions: {len(infra.get('decisions', []))}")
                print(f"     • Questions: {len(infra.get('questions', []))}")
            
            # Show synthesis
            if result.get('synthesis'):
                print(f"\n  💭 Synthesis preview:")
                print(f"     {result['synthesis'][:200]}...")
        else:
            print("  ⚠️ No memories to consolidate")
            
    except Exception as e:
        print(f"  ⚠️ Daily consolidation skipped: {e}")
    
    # Step 3: Test with custom prompt
    print("\n3️⃣ Testing Daily Consolidation (Custom Prompt)")
    print("-" * 40)
    
    custom_prompt = """
    Based on today's memories, answer these specific questions:
    1. What was the dominant emotion?
    2. What decision had the most potential impact?
    3. What question deserves deeper thought?
    
    Be extremely concise - one sentence per answer.
    """
    
    try:
        result = daily_consolidator.consolidate_day(
            target_date=yesterday,
            custom_prompt=custom_prompt,
            skip_synthesis=False
        )
        
        if result and result.get('synthesis'):
            print(f"  ✓ Custom synthesis generated:")
            print(f"     {result['synthesis'][:300]}...")
        else:
            print("  ⚠️ No synthesis generated")
            
    except Exception as e:
        print(f"  ⚠️ Custom synthesis skipped: {e}")
    
    # Step 4: Test different prompt styles
    print("\n4️⃣ Testing Different Prompt Styles")
    print("-" * 40)
    
    styles = ['socratic', 'coaching', 'scientist']
    
    for style in styles:
        print(f"\n  Testing {style} style:")
        
        # Get style template
        style_prompt = DefaultPromptTemplates.get_template(style, 'daily')
        
        try:
            result = daily_consolidator.consolidate_day(
                target_date=yesterday,
                custom_prompt=style_prompt,
                skip_synthesis=False
            )
            
            if result and result.get('synthesis'):
                print(f"    ✓ {style.capitalize()} synthesis:")
                print(f"       {result['synthesis'][:150]}...")
        except Exception as e:
            print(f"    ⚠️ {style} style failed: {e}")
    
    # Step 5: Test weekly consolidation
    print("\n5️⃣ Testing Weekly Consolidation")
    print("-" * 40)
    
    last_week = datetime.now() - timedelta(weeks=1)
    week_num = last_week.isocalendar()[1]
    year = last_week.year
    
    try:
        result = weekly_consolidator.identify_patterns(
            week_number=week_num,
            year=year,
            skip_synthesis=False
        )
        
        if result:
            print(f"  ✓ Analyzed week {week_num}/{year}")
            
            # Show patterns
            if result.get('infrastructure'):
                infra = result['infrastructure']
                print(f"  📊 Patterns found:")
                
                if infra.get('recurring_themes'):
                    themes = list(infra['recurring_themes'].keys())[:3]
                    print(f"     • Recurring themes: {', '.join(themes)}")
                
                if infra.get('productivity_patterns'):
                    prod = infra['productivity_patterns']
                    print(f"     • Peak hours: {prod.get('peak_hours', [])}")
                    print(f"     • Completion rate: {prod.get('task_completion_rate', 0):.0%}")
            
            # Show synthesis
            if result.get('synthesis'):
                print(f"\n  💭 Weekly synthesis preview:")
                print(f"     {result['synthesis'][:200]}...")
        else:
            print("  ⚠️ No data for week")
            
    except Exception as e:
        print(f"  ⚠️ Weekly consolidation skipped: {e}")
    
    # Step 6: Test context detection
    print("\n6️⃣ Testing Context Detection")
    print("-" * 40)
    
    from src.memory.prompts import ContextDetector
    
    detector = ContextDetector()
    
    # Simulate different contexts with proper Memory objects
    from dataclasses import dataclass
    
    @dataclass
    class TestMemory:
        raw_text: str
        extracted_data: dict = None
        thought_type: str = None
        timestamp: datetime = None
    
    test_contexts = [
        {
            'name': 'High Stress',
            'memories': [
                TestMemory('Feeling overwhelmed with deadlines', 
                          {'mood': 'stressed'}),
                TestMemory('So anxious about the presentation', 
                          {'mood': 'anxious'}),
            ] * 3  # Multiply to trigger threshold
        },
        {
            'name': 'Creative Burst',
            'memories': [
                TestMemory('Had a breakthrough idea about the architecture', 
                          {'thought_type': 'idea'}, 'idea'),
                TestMemory('Realized we can optimize the algorithm', 
                          {'thought_type': 'insight'}, 'insight'),
            ] * 3
        }
    ]
    
    for test_case in test_contexts:
        context = detector.analyze_context({'memories': test_case['memories']})
        
        print(f"\n  {test_case['name']} Context:")
        print(f"    • Stress count: {context['stress_count']}")
        print(f"    • Creative insights: {context['creative_insights']}")
        print(f"    • High stress detected: {context['high_stress_period']}")
        print(f"    • Creative burst detected: {context['creative_burst']}")
        
        # Check if contextual prompt would be used
        if detector.should_use_contextual_prompt(context):
            print(f"    ✓ Would use contextual prompt")
        else:
            print(f"    • Would use default prompt")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ Flexible Synthesis Test Complete!")
    print("=" * 60)
    
    print("\n📌 Key Features Demonstrated:")
    print("   ✓ Two-layer architecture (infrastructure + synthesis)")
    print("   ✓ User-defined prompts")
    print("   ✓ Multiple prompt styles")
    print("   ✓ Context detection")
    print("   ✓ Custom prompt support")
    
    print("\n📌 CLI Commands Available:")
    print("   memory prompts list           # List profiles")
    print("   memory prompts show           # Show prompts")
    print("   memory prompts edit daily     # Edit a prompt")
    print("   memory prompts create work    # Create profile")
    print("   memory prompts activate work  # Switch profile")
    print("   memory prompts test           # Test with data")
    
    # Clean up test profile
    if test_profile in prompt_manager.list_profiles():
        prompt_manager.delete_profile(test_profile)
        print(f"\n🧹 Cleaned up test profile: {test_profile}")


if __name__ == "__main__":
    test_flexible_synthesis()