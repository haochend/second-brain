"""CLI commands for prompt management"""

import click
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from pathlib import Path
from typing import Optional

from ..prompts import PromptManager, DefaultPromptTemplates

console = Console()


@click.group(name='prompts')
def prompt_commands():
    """Manage synthesis prompts"""
    pass


@prompt_commands.command(name='list')
def list_profiles():
    """List all available prompt profiles"""
    manager = PromptManager()
    profiles = manager.list_profiles()
    active = manager.active_profile
    
    table = Table(title="💭 Prompt Profiles", show_header=True, header_style="bold magenta")
    table.add_column("Profile", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Location")
    
    for profile in profiles:
        status = "✓ Active" if profile == active else ""
        
        if profile == "default":
            location = "Built-in"
        else:
            location = f"~/.memory/prompts/custom/{profile}.yaml"
        
        table.add_row(profile, status, location)
    
    console.print(table)
    console.print(f"\n[bold]Active profile:[/bold] [green]{active}[/green]")


@prompt_commands.command(name='show')
@click.argument('profile', required=False)
@click.option('--type', '-t', 'prompt_type', 
              type=click.Choice(['daily', 'weekly', 'monthly', 'contextual', 'all']),
              default='all',
              help='Type of prompt to show')
def show_prompts(profile: Optional[str], prompt_type: str):
    """Show prompts for a profile"""
    manager = PromptManager()
    profile = profile or manager.active_profile
    
    prompts = manager.get_profile_prompts(profile)
    
    if not prompts:
        console.print(f"[red]No prompts found for profile '{profile}'[/red]")
        return
    
    console.print(Panel(f"[bold cyan]Prompts for profile: {profile}[/bold cyan]"))
    
    if prompt_type == 'all':
        types_to_show = ['daily', 'weekly', 'monthly', 'contextual']
    else:
        types_to_show = [prompt_type]
    
    for ptype in types_to_show:
        if ptype in prompts:
            content = prompts[ptype]
            
            # Handle contextual prompts (list of rules)
            if ptype == 'contextual' and isinstance(content, list):
                console.print(f"\n[bold yellow]{ptype.upper()} PROMPTS:[/bold yellow]")
                for i, rule in enumerate(content, 1):
                    if isinstance(rule, dict):
                        console.print(f"\n[cyan]Rule {i}:[/cyan]")
                        console.print(f"  When: {rule.get('when', 'N/A')}")
                        console.print(f"  Prompt: {rule.get('prompt', 'N/A')[:200]}...")
            else:
                console.print(f"\n[bold yellow]{ptype.upper()} PROMPT:[/bold yellow]")
                # Show first 500 chars for readability
                display_content = content[:500] + "..." if len(content) > 500 else content
                console.print(Panel(display_content, border_style="dim"))


@prompt_commands.command(name='edit')
@click.argument('prompt_type', type=click.Choice(['daily', 'weekly', 'monthly']))
@click.option('--profile', '-p', help='Profile to edit (default: active profile)')
def edit_prompt(prompt_type: str, profile: Optional[str]):
    """Edit a synthesis prompt"""
    manager = PromptManager()
    profile = profile or manager.active_profile
    
    # Get current prompt
    current_prompt = manager.get_prompt(prompt_type, profile=profile)
    
    console.print(f"\n[bold]Editing {prompt_type} prompt for profile: {profile}[/bold]")
    console.print("\n[dim]Current prompt:[/dim]")
    console.print(Panel(current_prompt[:300] + "...", border_style="dim"))
    
    # Get editor preference
    editor = os.environ.get('EDITOR', 'nano')
    
    # Create temp file with current prompt
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(current_prompt)
        temp_path = f.name
    
    try:
        # Open in editor
        click.edit(filename=temp_path, editor=editor)
        
        # Read edited content
        with open(temp_path, 'r') as f:
            new_prompt = f.read().strip()
        
        if new_prompt and new_prompt != current_prompt:
            # Save the new prompt
            if manager.save_prompt(profile, prompt_type, new_prompt):
                console.print(f"[green]✓ {prompt_type} prompt updated for profile '{profile}'[/green]")
            else:
                console.print(f"[red]Failed to save prompt[/red]")
        else:
            console.print("[yellow]No changes made[/yellow]")
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@prompt_commands.command(name='create')
@click.argument('profile_name')
@click.option('--base', '-b', default='default', help='Base profile to copy from')
def create_profile(profile_name: str, base: str):
    """Create a new prompt profile"""
    manager = PromptManager()
    
    if manager.create_profile(profile_name, base):
        console.print(f"[green]✓ Created profile '{profile_name}' based on '{base}'[/green]")
        
        # Ask if they want to activate it
        if Confirm.ask(f"Activate profile '{profile_name}'?"):
            manager.set_active_profile(profile_name)
            console.print(f"[green]✓ Profile '{profile_name}' is now active[/green]")
    else:
        console.print(f"[red]Failed to create profile '{profile_name}'[/red]")


@prompt_commands.command(name='activate')
@click.argument('profile_name')
def activate_profile(profile_name: str):
    """Set the active prompt profile"""
    manager = PromptManager()
    
    if manager.set_active_profile(profile_name):
        console.print(f"[green]✓ Profile '{profile_name}' is now active[/green]")
    else:
        console.print(f"[red]Profile '{profile_name}' not found[/red]")


@prompt_commands.command(name='delete')
@click.argument('profile_name')
def delete_profile(profile_name: str):
    """Delete a custom prompt profile"""
    if profile_name == 'default':
        console.print("[red]Cannot delete the default profile[/red]")
        return
    
    # Confirm deletion
    if not Confirm.ask(f"Delete profile '{profile_name}'?"):
        console.print("[yellow]Cancelled[/yellow]")
        return
    
    manager = PromptManager()
    
    if manager.delete_profile(profile_name):
        console.print(f"[green]✓ Deleted profile '{profile_name}'[/green]")
    else:
        console.print(f"[red]Failed to delete profile '{profile_name}'[/red]")


@prompt_commands.command(name='test')
@click.option('--type', '-t', 'prompt_type', 
              type=click.Choice(['daily', 'weekly', 'monthly']),
              default='daily',
              help='Type of consolidation to test')
@click.option('--profile', '-p', help='Profile to test (default: active profile)')
def test_prompt(prompt_type: str, profile: Optional[str]):
    """Test a prompt with sample data"""
    from ..consolidation import FlexibleDailyConsolidator, FlexibleWeeklyPatternRecognizer
    from ..storage import Database
    
    manager = PromptManager()
    profile = profile or manager.active_profile
    
    console.print(f"\n[bold]Testing {prompt_type} prompt from profile: {profile}[/bold]\n")
    
    # Get the prompt
    prompt = manager.get_prompt(prompt_type, profile=profile)
    
    # Create consolidator
    db = Database()
    
    if prompt_type == 'daily':
        consolidator = FlexibleDailyConsolidator(db=db)
        
        # Try to get yesterday's memories
        from datetime import datetime, timedelta
        yesterday = datetime.now().date() - timedelta(days=1)
        
        console.print(f"[dim]Using memories from {yesterday}...[/dim]\n")
        
        result = consolidator.consolidate_day(
            target_date=yesterday,
            custom_prompt=prompt,
            skip_synthesis=False
        )
        
    elif prompt_type == 'weekly':
        consolidator = FlexibleWeeklyPatternRecognizer(db=db)
        
        # Use last week
        from datetime import datetime, timedelta
        last_week = datetime.now() - timedelta(weeks=1)
        week_num = last_week.isocalendar()[1]
        year = last_week.year
        
        console.print(f"[dim]Using week {week_num}/{year}...[/dim]\n")
        
        result = consolidator.identify_patterns(
            week_number=week_num,
            year=year,
            custom_prompt=prompt,
            skip_synthesis=False
        )
    
    else:
        console.print("[red]Monthly testing not yet implemented[/red]")
        return
    
    # Display results
    if result and result.get('synthesis'):
        console.print(Panel(result['synthesis'], 
                          title="[bold green]Synthesis Result[/bold green]",
                          border_style="green"))
        
        # Show some infrastructure stats
        if result.get('infrastructure'):
            infra = result['infrastructure']
            console.print("\n[bold]Infrastructure Data:[/bold]")
            console.print(f"  • Memory count: {infra.get('memory_count', 0)}")
            console.print(f"  • People mentioned: {len(infra.get('people', {}))}")
            console.print(f"  • Topics: {len(infra.get('topics', []))}")
            console.print(f"  • Decisions: {len(infra.get('decisions', []))}")
            console.print(f"  • Questions: {len(infra.get('questions', []))}")
    else:
        console.print("[yellow]No data available for testing[/yellow]")


@prompt_commands.command(name='styles')
def show_styles():
    """Show available prompt styles"""
    styles = {
        'default': 'Balanced analysis focusing on actionable insights',
        'socratic': 'Questions that challenge assumptions and promote self-discovery',
        'coaching': 'Empowering observations with experiments to try',
        'scientist': 'Evidence-based analysis with hypotheses and experiments',
        'philosopher': 'Deep reflection on meaning, values, and wisdom'
    }
    
    table = Table(title="🎨 Available Prompt Styles", show_header=True, header_style="bold magenta")
    table.add_column("Style", style="cyan", width=15)
    table.add_column("Description", style="white")
    
    for style, desc in styles.items():
        table.add_row(style, desc)
    
    console.print(table)
    
    console.print("\n[dim]To use a style, create a new profile and copy prompts from templates:[/dim]")
    console.print("[green]memory prompts create mystyle --base default[/green]")
    console.print("[green]memory prompts edit daily --profile mystyle[/green]")


@prompt_commands.command(name='import')
@click.argument('style', type=click.Choice(['socratic', 'coaching', 'scientist', 'philosopher']))
@click.option('--profile', '-p', help='Profile to import into (default: active profile)')
@click.option('--type', '-t', 'prompt_type',
              type=click.Choice(['daily', 'weekly', 'monthly', 'all']),
              default='all',
              help='Which prompts to import')
def import_style(style: str, profile: Optional[str], prompt_type: str):
    """Import a predefined style into a profile"""
    manager = PromptManager()
    profile = profile or manager.active_profile
    
    console.print(f"\n[bold]Importing {style} style into profile: {profile}[/bold]")
    
    # Get the style templates
    templates_to_import = []
    
    if prompt_type == 'all':
        # Import the style for all types
        style_prompt = DefaultPromptTemplates.get_template(style, 'all')
        templates_to_import = [('daily', style_prompt), 
                              ('weekly', style_prompt), 
                              ('monthly', style_prompt)]
    else:
        style_prompt = DefaultPromptTemplates.get_template(style, prompt_type)
        templates_to_import = [(prompt_type, style_prompt)]
    
    # Import each template
    success_count = 0
    for ptype, template in templates_to_import:
        if manager.save_prompt(profile, ptype, template):
            console.print(f"  [green]✓ Imported {ptype} prompt[/green]")
            success_count += 1
        else:
            console.print(f"  [red]✗ Failed to import {ptype} prompt[/red]")
    
    if success_count > 0:
        console.print(f"\n[green]Successfully imported {success_count} prompt(s)[/green]")
    else:
        console.print("[red]No prompts were imported[/red]")