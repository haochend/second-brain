"""CLI commands for memory system"""

import click
import json
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from typing import Optional

from ..capture import Queue, TextCapture
from ..capture.voice import VoiceCapture
from ..storage import Database
from ..processing import MemoryProcessor, LLMExtractor
from ..processing.transcription import WhisperTranscriber
from ..query import MemorySearch

console = Console()


@click.group()
@click.option('--debug/--no-debug', default=False, help='Enable debug output')
@click.pass_context
def cli(ctx, debug):
    """Second Brain - Your unified memory system"""
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    
    # Initialize components
    ctx.obj['db'] = Database()
    ctx.obj['queue'] = Queue()
    ctx.obj['extractor'] = LLMExtractor()
    ctx.obj['processor'] = MemoryProcessor(
        queue=ctx.obj['queue'],
        db=ctx.obj['db'],
        extractor=ctx.obj['extractor']
    )
    ctx.obj['capture'] = TextCapture(
        queue=ctx.obj['queue'],
        db=ctx.obj['db']
    )
    ctx.obj['search'] = MemorySearch(db=ctx.obj['db'])


@cli.command()
@click.argument('text', required=False)
@click.option('--voice', '-v', is_flag=True, help='Capture voice input')
@click.pass_context
def add(ctx, text, voice):
    """Add a new memory (text or voice)"""
    if voice:
        # Voice capture mode
        try:
            voice_capture = VoiceCapture()
            console.print("[cyan]Starting voice capture...[/cyan]")
            audio_path = voice_capture.start_recording()
            
            # Add to queue for processing
            queue = ctx.obj['queue']
            item_id = queue.add(
                item_type="voice",
                content="",  # Will be transcribed later
                metadata={"audio_path": audio_path}
            )
            
            # Also add to database as pending
            db = ctx.obj['db']
            from ..storage import Memory
            memory = Memory(
                raw_text="[Voice recording - pending transcription]",
                source="voice",
                status="pending",
                timestamp=datetime.now()
            )
            db.add_memory(memory)
            
            console.print(f"[green]✓ Voice captured![/green] ID: {item_id}")
            console.print(f"[dim]Audio saved: {audio_path}[/dim]")
            console.print("[dim]Will be transcribed and processed in the background[/dim]")
            
            # Optionally process immediately
            if click.confirm("Process now?", default=True):
                ctx.invoke(process, now=True)
        
        except Exception as e:
            console.print(f"[red]Error capturing voice: {e}[/red]")
            if ctx.obj.get('debug'):
                console.print_exception()
        return
    
    if not text:
        # Interactive text input
        console.print("[cyan]Enter your thought (press Ctrl+D when done):[/cyan]")
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            text = '\n'.join(lines)
    
    if not text.strip():
        console.print("[red]No text provided[/red]")
        return
    
    try:
        # Capture the text
        capture = ctx.obj['capture']
        item_id = capture.capture(text)
        
        console.print(f"[green]✓ Captured![/green] ID: {item_id}")
        console.print("[dim]Will be processed in the background[/dim]")
        
        # Optionally process immediately
        if click.confirm("Process now?", default=False):
            ctx.invoke(process, now=True)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if ctx.obj.get('debug'):
            console.print_exception()


@cli.command()
@click.option('--now', is_flag=True, help='Process immediately')
@click.option('--limit', default=10, help='Number of items to process')
@click.pass_context
def process(ctx, now, limit):
    """Process pending memories"""
    processor = ctx.obj['processor']
    
    with console.status("[cyan]Processing memories...[/cyan]"):
        stats = processor.process_batch(limit=limit)
    
    # Show results
    table = Table(title="Processing Results")
    table.add_column("Status", style="cyan")
    table.add_column("Count", justify="right")
    
    table.add_row("Processed", f"[green]{stats['processed']}[/green]")
    table.add_row("Failed", f"[red]{stats['failed']}[/red]")
    table.add_row("Skipped", f"[yellow]{stats['skipped']}[/yellow]")
    
    console.print(table)


@cli.command()
@click.argument('query')
@click.option('--limit', default=10, help='Number of results')
@click.pass_context
def search(ctx, query, limit):
    """Search memories"""
    search_engine = ctx.obj['search']
    results = search_engine.search(query, limit=limit)
    
    if not results:
        console.print("[yellow]No memories found[/yellow]")
        return
    
    for memory in results:
        # Create a panel for each memory
        content = f"[white]{memory.raw_text}[/white]\n"
        
        if memory.summary and memory.summary != memory.raw_text[:100]:
            content += f"\n[dim]Summary: {memory.summary}[/dim]\n"
        
        if memory.extracted_data:
            if memory.extracted_data.get('actions'):
                content += "\n[cyan]Actions:[/cyan]\n"
                for action in memory.extracted_data['actions']:
                    priority = action.get('priority', 'medium')
                    color = {'high': 'red', 'medium': 'yellow', 'low': 'green'}.get(priority, 'white')
                    content += f"  • [{color}]{action['text']}[/{color}]\n"
            
            if memory.extracted_data.get('people'):
                content += f"\n[magenta]People:[/magenta] {', '.join(memory.extracted_data['people'])}\n"
            
            if memory.extracted_data.get('topics'):
                content += f"\n[blue]Topics:[/blue] {', '.join(memory.extracted_data['topics'])}\n"
        
        timestamp = memory.timestamp.strftime("%Y-%m-%d %H:%M") if memory.timestamp else "Unknown"
        panel = Panel(
            content,
            title=f"[bold]{memory.thought_type or 'memory'}[/bold] - {timestamp}",
            expand=False
        )
        console.print(panel)


@cli.command()
@click.option('--pending', is_flag=True, help='Show only pending tasks')
@click.option('--limit', default=20, help='Number of tasks to show')
@click.pass_context
def tasks(ctx, pending, limit):
    """Show extracted tasks"""
    db = ctx.obj['db']
    memories = db.get_tasks()
    
    if not memories:
        console.print("[yellow]No tasks found[/yellow]")
        return
    
    table = Table(title="Tasks")
    table.add_column("Priority", style="cyan", width=8)
    table.add_column("Task", style="white")
    table.add_column("Date", style="dim", width=16)
    
    for memory in memories[:limit]:
        if memory.extracted_data and memory.extracted_data.get('actions'):
            for action in memory.extracted_data['actions']:
                priority = action.get('priority', 'medium')
                color = {'high': 'red', 'medium': 'yellow', 'low': 'green'}.get(priority, 'white')
                
                timestamp = memory.timestamp.strftime("%Y-%m-%d %H:%M") if memory.timestamp else ""
                
                table.add_row(
                    f"[{color}]{priority}[/{color}]",
                    action['text'],
                    timestamp
                )
    
    console.print(table)


@cli.command()
@click.option('--date', help='Specific date (YYYY-MM-DD)')
@click.pass_context
def today(ctx, date):
    """Show today's memories (or specific date)"""
    db = ctx.obj['db']
    
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            console.print("[red]Invalid date format. Use YYYY-MM-DD[/red]")
            return
    else:
        target_date = datetime.now()
    
    memories = db.get_memories_by_date(target_date)
    
    if not memories:
        console.print(f"[yellow]No memories for {target_date.strftime('%Y-%m-%d')}[/yellow]")
        return
    
    console.print(f"\n[bold cyan]Memories for {target_date.strftime('%A, %B %d, %Y')}[/bold cyan]\n")
    
    for memory in memories:
        time_str = memory.timestamp.strftime("%H:%M") if memory.timestamp else "??:??"
        
        # Color code by thought type
        type_colors = {
            'action': 'red',
            'idea': 'yellow',
            'question': 'cyan',
            'observation': 'green',
            'decision': 'magenta',
            'feeling': 'blue'
        }
        color = type_colors.get(memory.thought_type, 'white')
        
        console.print(f"[dim]{time_str}[/dim] [{color}]●[/{color}] {memory.summary or memory.raw_text[:100]}")


@cli.command()
@click.pass_context
def status(ctx):
    """Show system status"""
    queue = ctx.obj['queue']
    db = ctx.obj['db']
    
    # Queue stats
    queue_stats = queue.get_stats()
    
    # Database stats
    recent = db.get_recent_memories(1)
    
    # Create status panel
    status_text = f"""[cyan]Queue Status:[/cyan]
  Pending: [yellow]{queue_stats['pending']}[/yellow]
  Processing: [blue]{queue_stats['processing']}[/blue]
  Completed: [green]{queue_stats['completed']}[/green]
  Failed: [red]{queue_stats['failed']}[/red]

[cyan]System Info:[/cyan]
  Memory Home: {ctx.obj['db'].db_path}
  LLM Model: {ctx.obj['extractor'].model_name}
"""
    
    if recent:
        last_memory = recent[0]
        last_time = last_memory.timestamp.strftime("%Y-%m-%d %H:%M") if last_memory.timestamp else "Unknown"
        status_text += f"\n[cyan]Last Memory:[/cyan]\n  {last_time} - {last_memory.summary or 'No summary'}"
    
    panel = Panel(status_text, title="[bold]Second Brain Status[/bold]", expand=False)
    console.print(panel)


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize the memory system"""
    console.print("[cyan]Initializing Second Brain...[/cyan]")
    
    # Database is already initialized in context
    console.print("[green]✓[/green] Database initialized")
    
    # Check Ollama
    try:
        import ollama
        models = ollama.list()
        console.print("[green]✓[/green] Ollama connected")
        
        # Check for recommended model
        model_names = [m['name'] for m in models.get('models', [])]
        if not any('llama' in name.lower() for name in model_names):
            console.print("[yellow]⚠[/yellow]  No Llama model found. Run: [cyan]ollama pull llama3.2[/cyan]")
    except Exception as e:
        console.print(f"[red]✗[/red] Ollama not available: {e}")
        console.print("    Install from: https://ollama.ai")
    
    console.print("\n[green]Ready to use![/green] Try: [cyan]memory add \"Your first thought\"[/cyan]")


if __name__ == "__main__":
    cli()