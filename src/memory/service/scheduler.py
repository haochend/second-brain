"""Background service scheduler for memory consolidation"""

import os
import signal
import sys
import time
import schedule
import threading
from datetime import datetime, timedelta
from typing import Optional
from ..processing.enhanced_processor import EnhancedMemoryProcessor
from ..consolidation import DailyConsolidator, WeeklyPatternRecognizer, KnowledgeSynthesizer
from ..storage import Database
from ..capture import Queue


class MemoryConsolidationScheduler:
    """Schedules and runs all memory consolidation tasks"""
    
    def __init__(self):
        """Initialize the scheduler"""
        self.db = Database()
        self.queue = Queue()
        self.processor = EnhancedMemoryProcessor(db=self.db, queue=self.queue)
        self.daily_consolidator = DailyConsolidator(db=self.db)
        self.weekly_patterns = WeeklyPatternRecognizer(db=self.db)
        self.knowledge_synthesizer = KnowledgeSynthesizer(db=self.db)
        
        self.running = False
        self.threads = []
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print("\n🛑 Received shutdown signal, stopping scheduler...")
        self.stop()
        sys.exit(0)
    
    def setup_schedule(self):
        """Configure the schedule for all tasks"""
        
        # Process queue every 5 minutes
        schedule.every(5).minutes.do(self._run_threaded, self.process_queue)
        
        # Daily consolidation at 2 AM
        schedule.every().day.at("02:00").do(self._run_threaded, self.consolidate_daily)
        
        # Weekly pattern recognition on Sundays at 3 AM
        schedule.every().sunday.at("03:00").do(self._run_threaded, self.recognize_weekly_patterns)
        
        # Monthly knowledge synthesis on 1st of month at 4 AM
        schedule.every().day.at("04:00").do(self._check_and_run_monthly, self.synthesize_knowledge)
        
        # Quarterly wisdom extraction (1st of Jan, Apr, Jul, Oct) at 5 AM
        schedule.every().day.at("05:00").do(self._check_and_run_quarterly, self.extract_wisdom)
        
        print("📅 Schedule configured:")
        print("  • Queue processing: Every 5 minutes")
        print("  • Daily consolidation: 2:00 AM")
        print("  • Weekly patterns: Sunday 3:00 AM")
        print("  • Knowledge synthesis: 1st of month 4:00 AM")
        print("  • Wisdom extraction: Quarterly 5:00 AM")
    
    def _run_threaded(self, job_func):
        """Run job in a separate thread"""
        job_thread = threading.Thread(target=job_func)
        job_thread.daemon = True
        job_thread.start()
        self.threads.append(job_thread)
    
    def _check_and_run_monthly(self, job_func):
        """Check if it's the 1st of the month and run job"""
        if datetime.now().day == 1:
            self._run_threaded(job_func)
    
    def _check_and_run_quarterly(self, job_func):
        """Check if it's the 1st of a quarter month and run job"""
        now = datetime.now()
        if now.day == 1 and now.month in [1, 4, 7, 10]:
            self._run_threaded(job_func)
    
    def process_queue(self):
        """Process pending memories in queue"""
        try:
            print(f"\n🔄 Processing queue at {datetime.now().strftime('%H:%M:%S')}")
            stats = self.processor.process_batch(limit=20)
            
            if stats['processed'] > 0:
                print(f"  ✓ Processed: {stats['processed']} memories")
                if stats['tasks_detected'] > 0:
                    print(f"  📋 Tasks detected: {stats['tasks_detected']}")
            if stats['failed'] > 0:
                print(f"  ⚠️ Failed: {stats['failed']}")
                
        except Exception as e:
            print(f"❌ Queue processing error: {e}")
    
    def consolidate_daily(self):
        """Run daily consolidation for yesterday"""
        try:
            yesterday = datetime.now().date() - timedelta(days=1)
            print(f"\n🌅 Running daily consolidation for {yesterday}")
            
            result = self.daily_consolidator.consolidate_day(yesterday)
            
            if result:
                print(f"  ✓ Consolidated {result.get('memory_count', 0)} memories")
                print(f"  📊 Importance score: {result.get('importance_score', 0):.1f}/10")
                
        except Exception as e:
            print(f"❌ Daily consolidation error: {e}")
    
    def recognize_weekly_patterns(self):
        """Run weekly pattern recognition for last week"""
        try:
            last_week = datetime.now() - timedelta(weeks=1)
            week_num = last_week.isocalendar()[1]
            year = last_week.year
            
            print(f"\n📊 Running weekly pattern recognition for week {week_num}/{year}")
            
            result = self.weekly_patterns.identify_patterns(week_num, year)
            
            if result:
                patterns = result.get('patterns', {})
                print(f"  ✓ Found {len(patterns.get('recurring_themes', {}))} recurring themes")
                print(f"  💡 Generated {len(result.get('recommendations', []))} recommendations")
                
        except Exception as e:
            print(f"❌ Weekly pattern recognition error: {e}")
    
    def synthesize_knowledge(self):
        """Run monthly knowledge synthesis"""
        try:
            print(f"\n🧠 Running monthly knowledge synthesis")
            
            nodes = self.knowledge_synthesizer.build_knowledge_nodes(days=30)
            
            print(f"  ✓ Created {len(nodes)} knowledge nodes")
            
            if nodes:
                # Show top topics
                topics = [node['topic'] for node in nodes[:5]]
                print(f"  📚 Top topics: {', '.join(topics)}")
                
        except Exception as e:
            print(f"❌ Knowledge synthesis error: {e}")
    
    def extract_wisdom(self):
        """Run quarterly wisdom extraction"""
        try:
            print(f"\n✨ Running quarterly wisdom extraction")
            
            wisdom_items = self.knowledge_synthesizer.extract_wisdom(months=3)
            
            print(f"  ✓ Extracted {len(wisdom_items)} wisdom items")
            
            if wisdom_items:
                # Show sample wisdom
                for item in wisdom_items[:3]:
                    print(f"  💎 {item['content'][:80]}...")
                    
        except Exception as e:
            print(f"❌ Wisdom extraction error: {e}")
    
    def run_initial_tasks(self):
        """Run any immediate tasks on startup"""
        print("\n🚀 Running initial tasks...")
        
        # Process any pending queue items immediately
        self.process_queue()
        
        # Check if today needs consolidation (in case service was down)
        self._check_missed_consolidations()
    
    def _check_missed_consolidations(self):
        """Check and run any missed consolidations"""
        # Check if yesterday was consolidated
        yesterday = datetime.now().date() - timedelta(days=1)
        
        query = "SELECT COUNT(*) as count FROM daily_consolidations WHERE date = ?"
        cursor = self.db.conn.execute(query, (yesterday.isoformat(),))
        row = cursor.fetchone()
        
        if row['count'] == 0:
            print(f"  📅 Running missed daily consolidation for {yesterday}")
            self.consolidate_daily()
    
    def start(self):
        """Start the scheduler"""
        print("\n🎯 Memory Consolidation Service Starting...")
        print(f"📍 Data directory: {os.path.expanduser(os.getenv('MEMORY_HOME', '~/.memory'))}")
        
        self.running = True
        
        # Setup schedule
        self.setup_schedule()
        
        # Run initial tasks
        self.run_initial_tasks()
        
        print("\n✅ Service started. Press Ctrl+C to stop.\n")
        
        # Main loop
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Scheduler error: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        
        # Wait for threads to complete
        print("⏳ Waiting for active tasks to complete...")
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=10)
        
        # Close database connection
        if self.db:
            self.db.close()
        
        print("✅ Scheduler stopped cleanly")
    
    def run_once(self, task: str):
        """Run a specific task once (for testing)"""
        tasks = {
            'queue': self.process_queue,
            'daily': self.consolidate_daily,
            'weekly': self.recognize_weekly_patterns,
            'knowledge': self.synthesize_knowledge,
            'wisdom': self.extract_wisdom
        }
        
        if task in tasks:
            print(f"Running task: {task}")
            tasks[task]()
        else:
            print(f"Unknown task: {task}")
            print(f"Available tasks: {', '.join(tasks.keys())}")


def main():
    """Main entry point for the scheduler service"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Memory Consolidation Background Service')
    parser.add_argument('--once', choices=['queue', 'daily', 'weekly', 'knowledge', 'wisdom'],
                       help='Run a specific task once and exit')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as a daemon (detached)')
    
    args = parser.parse_args()
    
    scheduler = MemoryConsolidationScheduler()
    
    if args.once:
        # Run single task and exit
        scheduler.run_once(args.once)
    elif args.daemon:
        # Run as daemon (would need proper daemonization)
        print("Daemon mode not fully implemented. Running in foreground...")
        scheduler.start()
    else:
        # Run in foreground
        scheduler.start()


if __name__ == '__main__':
    main()