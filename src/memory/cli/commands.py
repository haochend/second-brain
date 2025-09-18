"""CLI commands for memory system"""

import click
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from typing import Optional

# Load environment variables
load_dotenv()

from ..capture import Queue, TextCapture
from ..capture.voice import VoiceCapture
from ..storage import Database
from ..processing import MemoryProcessor, LLMExtractor
from ..processing.transcription_mlx import MLXWhisperTranscriber
from ..query import MemorySearch, SemanticSearch
from ..embeddings import EmbeddingGenerator, VectorStore
from .prompt_commands import prompt_commands

console = Console()


def get_processor(ctx):
    """Lazy-load the processor with all its dependencies"""
    if ctx.obj['processor'] is None:
        # Initialize dependencies if needed
        if ctx.obj['extractor'] is None:
            ctx.obj['extractor'] = LLMExtractor()
        if ctx.obj['embedding_generator'] is None:
            ctx.obj['embedding_generator'] = EmbeddingGenerator()
        if ctx.obj['vector_store'] is None:
            ctx.obj['vector_store'] = VectorStore()
        
        # Create processor
        ctx.obj['processor'] = MemoryProcessor(
            queue=ctx.obj['queue'],
            db=ctx.obj['db'],
            extractor=ctx.obj['extractor'],
            embedding_generator=ctx.obj['embedding_generator'],
            vector_store=ctx.obj['vector_store']
        )
    return ctx.obj['processor']


def get_semantic_search(ctx):
    """Lazy-load semantic search with embeddings"""
    if ctx.obj['semantic_search'] is None:
        # Initialize dependencies if needed
        if ctx.obj['embedding_generator'] is None:
            ctx.obj['embedding_generator'] = EmbeddingGenerator()
        if ctx.obj['vector_store'] is None:
            ctx.obj['vector_store'] = VectorStore()
        
        ctx.obj['semantic_search'] = SemanticSearch(
            db=ctx.obj['db'],
            embedding_generator=ctx.obj['embedding_generator'],
            vector_store=ctx.obj['vector_store']
        )
    return ctx.obj['semantic_search']


def get_vector_store(ctx):
    """Lazy-load vector store"""
    if ctx.obj['vector_store'] is None:
        ctx.obj['vector_store'] = VectorStore()
    return ctx.obj['vector_store']


@click.group()
@click.option('--debug/--no-debug', default=False, help='Enable debug output')
@click.pass_context
def cli(ctx, debug):
    """Second Brain - Your unified memory system"""
    ctx.ensure_object(dict)
    ctx.obj['debug'] = debug
    
    # Initialize core components (always needed)
    ctx.obj['db'] = Database()
    ctx.obj['queue'] = Queue()
    
    # Lazy initialization flags
    ctx.obj['embedding_generator'] = None
    ctx.obj['vector_store'] = None
    ctx.obj['extractor'] = None
    ctx.obj['processor'] = None
    ctx.obj['semantic_search'] = None
    
    # Initialize capture (lightweight)
    ctx.obj['capture'] = TextCapture(
        queue=ctx.obj['queue'],
        db=ctx.obj['db']
    )
    
    # Initialize basic search (no embeddings needed)
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
            
            # Create a shared UUID for both queue and database
            import uuid
            memory_uuid = str(uuid.uuid4())
            
            # Add to queue for processing
            queue = ctx.obj['queue']
            item_id = queue.add(
                item_type="voice",
                content="",  # Will be transcribed later
                metadata={"audio_path": audio_path, "memory_uuid": memory_uuid}
            )
            
            # Also add to database as pending with same UUID
            db = ctx.obj['db']
            from ..storage import Memory
            memory = Memory(
                uuid=memory_uuid,
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
    processor = get_processor(ctx)
    
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
@click.option('--semantic', '-s', is_flag=True, help='Use semantic search instead of keyword search')
@click.pass_context
def search(ctx, query, limit, semantic):
    """Search memories (keyword or semantic)"""
    if semantic:
        search_engine = get_semantic_search(ctx)
    else:
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
        
        # Add relevance score if available (from semantic search)
        if hasattr(memory, 'relevance_score'):
            content += f"\n[dim]Relevance: {memory.relevance_score:.2%}[/dim]"
        
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
@click.option('--days', default=7, help='Delete audio files older than N days')
@click.option('--all', is_flag=True, help='Delete all processed audio files')
@click.pass_context
def cleanup(ctx, days, all):
    """Clean up old audio files (for files kept with KEEP_AUDIO_AFTER_PROCESSING=true)"""
    import os
    from datetime import datetime, timedelta
    from pathlib import Path
    
    audio_dir = Path(os.path.expanduser("~/.memory/audio"))
    if not audio_dir.exists():
        console.print("[yellow]No audio directory found[/yellow]")
        return
    
    db = ctx.obj['db']
    
    # Get all audio files
    audio_files = list(audio_dir.glob("*.wav"))
    if not audio_files:
        console.print("[yellow]No audio files found[/yellow]")
        return
    
    deleted_count = 0
    total_size = 0
    cutoff_date = datetime.now() - timedelta(days=days)
    
    for audio_file in audio_files:
        # Check if file is old enough
        file_age = datetime.fromtimestamp(audio_file.stat().st_mtime)
        
        if all or file_age < cutoff_date:
            # Check if it's been processed
            # Search for the audio path in extracted_data
            cursor = db.conn.execute(
                "SELECT COUNT(*) FROM memories WHERE extracted_data LIKE ? AND status = 'completed'",
                (f'%{audio_file.name}%',)
            )
            is_processed = cursor.fetchone()[0] > 0
            
            if is_processed or all:
                file_size = audio_file.stat().st_size
                try:
                    audio_file.unlink()
                    deleted_count += 1
                    total_size += file_size
                    console.print(f"[green]✓[/green] Deleted {audio_file.name} ({file_size/1024:.1f} KB)")
                except Exception as e:
                    console.print(f"[red]✗[/red] Failed to delete {audio_file.name}: {e}")
    
    if deleted_count > 0:
        console.print(f"\n[green]Cleaned up {deleted_count} files, freed {total_size/1024/1024:.1f} MB[/green]")
    else:
        console.print("[yellow]No files to clean up[/yellow]")

@cli.command()
@click.argument('memory_id', required=False)
@click.option('--limit', default=5, help='Number of related memories to find')
@click.pass_context
def related(ctx, memory_id, limit):
    """Find memories related to a specific memory or the latest one"""
    db = ctx.obj['db']
    semantic_search = get_semantic_search(ctx)
    
    if not memory_id:
        # Get the most recent memory
        recent = db.get_recent_memories(1)
        if not recent:
            console.print("[yellow]No memories found[/yellow]")
            return
        memory = recent[0]
        console.print(f"[cyan]Finding memories related to latest memory...[/cyan]\n")
    else:
        # Try to get memory by UUID or ID
        memory = db.get_memory_by_uuid(memory_id)
        if not memory:
            try:
                memory_id_int = int(memory_id)
                # Need to implement get_memory_by_id if not available
                memories = db.get_recent_memories(1000)  # Get many and filter
                memory = next((m for m in memories if m.id == memory_id_int), None)
            except ValueError:
                pass
        
        if not memory:
            console.print(f"[red]Memory not found: {memory_id}[/red]")
            return
    
    # Show the source memory
    console.print("[bold cyan]Source Memory:[/bold cyan]")
    console.print(f"{memory.summary or memory.raw_text[:100]}...")
    console.print()
    
    # Find related memories
    related_memories = semantic_search.find_related(memory, limit=limit)
    
    if not related_memories:
        console.print("[yellow]No related memories found[/yellow]")
        return
    
    console.print(f"[bold cyan]Related Memories:[/bold cyan]\n")
    
    for i, related_memory in enumerate(related_memories, 1):
        relevance = getattr(related_memory, 'relevance_score', 0)
        timestamp = related_memory.timestamp.strftime("%Y-%m-%d") if related_memory.timestamp else "Unknown"
        
        console.print(f"[cyan]{i}.[/cyan] [{relevance:.1%} similar] {timestamp}")
        console.print(f"   {related_memory.summary or related_memory.raw_text[:80]}...")
        console.print()


@cli.command()
@click.option('--force', is_flag=True, help='Force reindex without confirmation')
@click.pass_context
def reindex(ctx, force):
    """Reindex all memories in the vector database"""
    semantic_search = get_semantic_search(ctx)
    
    if not force:
        if not click.confirm("This will rebuild the entire vector index. Continue?"):
            return
    
    semantic_search.reindex_all()


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize the memory system"""
    console.print("[cyan]Initializing Second Brain...[/cyan]")
    
    # Database is already initialized in context
    console.print("[green]✓[/green] Database initialized")
    
    # Check vector store (only if initialized)
    if ctx.obj['vector_store'] is not None:
        vector_store = ctx.obj['vector_store']
        console.print(f"[green]✓[/green] Vector store initialized ({vector_store.count()} embeddings)")
    else:
        console.print("[dim]Vector store not yet initialized[/dim]")
    
    # Check Ollama
    try:
        import ollama
        models = ollama.list()
        console.print("[green]✓[/green] Ollama connected")
        
        # Check for recommended models
        if hasattr(models, 'models'):
            model_list = models.models
        else:
            model_list = models.get('models', [])
        
        model_names = []
        for m in model_list:
            if isinstance(m, dict):
                model_names.append(m.get('name', ''))
            else:
                model_names.append(getattr(m, 'name', ''))
        
        # Check for LLM model
        if not any('llama' in name.lower() or 'gpt' in name.lower() for name in model_names):
            console.print("[yellow]⚠[/yellow]  No LLM model found. Run: [cyan]ollama pull gpt-oss:120b[/cyan]")
        
        # Check for embedding model
        if not any('nomic' in name.lower() or 'embed' in name.lower() for name in model_names):
            console.print("[yellow]⚠[/yellow]  No embedding model found. Run: [cyan]ollama pull nomic-embed-text[/cyan]")
            
    except Exception as e:
        console.print(f"[red]✗[/red] Ollama not available: {e}")
        console.print("    Install from: https://ollama.ai")
    
    console.print("\n[green]Ready to use![/green] Try: [cyan]memory add \"Your first thought\"[/cyan]")


# Add prompt management commands to the CLI
cli.add_command(prompt_commands)

if __name__ == "__main__":
    cli()