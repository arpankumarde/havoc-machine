#!/usr/bin/env python3
"""Main entry point for the Havoc Machine CLI"""

import sys
import time
import signal
import subprocess
import tempfile
import os
from typing import Optional
from datetime import datetime, timedelta
import threading

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.live import Live
from rich.layout import Layout
from rich.prompt import Prompt, IntPrompt, FloatPrompt

from havoc_cli.api_client import APIClient
from havoc_cli.ui import TerminalUI

console = Console()


def get_configuration() -> dict:
    """Prompt user for configuration"""
    console.print(Panel.fit(
        "[bold cyan]Havoc Machine CLI[/bold cyan]\n"
        "[dim]Configure your parallel adversarial testing session[/dim]",
        border_style="cyan"
    ))
    console.print()
    
    try:
        websocket_url = Prompt.ask(
            "WebSocket URL",
            default="ws://localhost:8000"
        )
        
        num_sessions = IntPrompt.ask(
            "Number of sessions",
            default=3
        )
        
        if num_sessions < 1:
            console.print("[red]Number of sessions must be at least 1[/red]")
            sys.exit(1)
        
        duration_minutes = FloatPrompt.ask(
            "Duration (minutes)",
            default=2.0
        )
        
        if duration_minutes <= 0:
            console.print("[red]Duration must be greater than 0[/red]")
            sys.exit(1)
        
        return {
            'websocket_url': websocket_url,
            'num_sessions': num_sessions,
            'duration_minutes': duration_minutes
        }
    except KeyboardInterrupt:
        console.print("\n[red]Configuration cancelled[/red]")
        sys.exit(0)


def start_session(api_client: APIClient, config: dict) -> dict:
    """Start the parallel adversarial session"""
    console.print()
    console.print("[bold]Starting parallel adversarial testing...[/bold]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Initializing sessions...", total=None)
        
        try:
            response = api_client.start_parallel_adversarial(
                websocket_url=config['websocket_url'],
                parallel_executions=config['num_sessions'],
                duration_minutes=config['duration_minutes']
            )
            
            progress.update(task, description="[green]Sessions started successfully![/green]")
            time.sleep(0.5)
            
            return response
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)


def poll_messages(api_client: APIClient, ui: TerminalUI, duration_minutes: float, stop_event: threading.Event):
    """Poll messages for all sessions"""
    poll_interval = 6  # Poll every 6 seconds
    end_time = datetime.now() + timedelta(minutes=duration_minutes + 0.5)  # Add 30 seconds buffer
    
    while not stop_event.is_set() and datetime.now() < end_time:
        for session_id in ui.session_ids:
            if stop_event.is_set():
                break
            
            try:
                response = api_client.get_session_messages(session_id)
                messages = response.get('messages', [])
                ui.update_session(session_id, messages)
            except Exception as e:
                # Silently continue on errors
                pass
        
        # Wait for next poll
        time.sleep(poll_interval)
    
    # Mark as complete
    if ui.group_id and not ui.is_complete:
        ui.set_complete(ui.group_id)


def open_url_in_nano(url: str, ui: TerminalUI) -> bool:
    """Download URL content and open in nano. Returns True if successful."""
    try:
        import requests
        console.print(f"\n[dim]Downloading {url}...[/dim]")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(response.text)
            temp_file = f.name
        
        # Open in nano (don't clear screen, let nano handle it)
        console.print(f"[green]Opening file in nano. Press Ctrl+X to exit nano and return.[/green]")
        time.sleep(0.5)
        result = subprocess.run(['nano', temp_file])
        
        # Clean up
        os.unlink(temp_file)
        
        # Clear screen and show completion message again for clean terminal
        console.clear()
        ui.show_completion_message()
        
        return True
    except FileNotFoundError:
        console.print("[red]Error: nano editor not found. Please install nano or use a different editor.[/red]")
        console.print("[dim]Press Enter to continue...[/dim]")
        input()
        # Clear and show completion message again
        console.clear()
        ui.show_completion_message()
        return False
    except Exception as e:
        console.print(f"[red]Error opening URL: {e}[/red]")
        console.print("[dim]Press Enter to continue...[/dim]")
        input()
        # Clear and show completion message again
        console.clear()
        ui.show_completion_message()
        return False


def main():
    """Main entry point"""
    # Get configuration
    config = get_configuration()
    
    # Initialize API client
    # Extract base URL from websocket URL
    ws_url = config['websocket_url']
    if ws_url.startswith('ws://'):
        base_url = ws_url.replace('ws://', 'http://')
    elif ws_url.startswith('wss://'):
        base_url = ws_url.replace('wss://', 'https://')
    else:
        base_url = f"http://{ws_url}"
    
    # Remove /ws suffix if present
    if base_url.endswith('/ws'):
        base_url = base_url[:-3]
    
    api_client = APIClient(base_url=base_url)
    
    # Start session
    response = start_session(api_client, config)
    
    group_id = response.get('group_id')
    session_ids = response.get('session_ids', [])
    
    if not group_id or not session_ids:
        console.print("[red]Failed to start session. Invalid response from server.[/red]")
        sys.exit(1)
    
    console.print()
    console.print(Panel.fit(
        f"[bold green]Session Started![/bold green]\n\n"
        f"[cyan]Group ID:[/cyan] {group_id}\n"
        f"[cyan]Session IDs:[/cyan] {', '.join(session_ids[:3])}{'...' if len(session_ids) > 3 else ''}\n"
        f"[cyan]Duration:[/cyan] {config['duration_minutes']} minutes",
        border_style="green"
    ))
    console.print()
    input("Press Enter to start monitoring...")
    
    # Initialize UI
    ui = TerminalUI(session_ids, config['duration_minutes'])
    ui.group_id = group_id
    
    # Setup polling thread
    stop_event = threading.Event()
    poll_thread = threading.Thread(
        target=poll_messages,
        args=(api_client, ui, config['duration_minutes'], stop_event),
        daemon=True
    )
    poll_thread.start()
    
    # Track if user quit early and which file to open
    user_quit_early = False
    file_to_open = None  # 'j' for JSON, 'r' for report
    
    # Main UI loop
    try:
        import platform
        is_windows = platform.system() == 'Windows'
        
        if is_windows:
            # Windows: Use msvcrt for keyboard input
            try:
                import msvcrt
            except ImportError:
                msvcrt = None
                console.print("[yellow]Warning: msvcrt not available, keyboard input may not work[/yellow]")
            
            with Live(ui, refresh_per_second=2, screen=True) as live:
                while not stop_event.is_set():
                    # Check for keyboard input (non-blocking)
                    if msvcrt and msvcrt.kbhit():
                        try:
                            char = msvcrt.getch().decode('utf-8').lower()
                        except:
                            char = ''
                        
                        if char == 'q':
                            # User wants to quit early - will show progress bar
                            user_quit_early = True
                            break
                        elif char == 'j' and ui.is_complete:
                            # Exit Live view first, then open file
                            file_to_open = 'j'
                            break
                        elif char == 'r' and ui.is_complete:
                            # Exit Live view first, then open file
                            file_to_open = 'r'
                            break
                    
                    # Update UI
                    live.update(ui)
                    
                    # Check if complete
                    if ui.is_complete and not stop_event.is_set():
                        time.sleep(1)
                        stop_event.set()
                        ui.set_complete(group_id)
                        live.update(ui)
                        break
                    
                    time.sleep(0.5)
        else:
            # Unix: Use select for keyboard input
            import select
            import tty
            import termios
            
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
            
            try:
                with Live(ui, refresh_per_second=2, screen=True) as live:
                    while not stop_event.is_set():
                        # Check for keyboard input (non-blocking)
                        if select.select([sys.stdin], [], [], 0.5)[0]:
                            char = sys.stdin.read(1).lower()
                            
                            if char == 'q':
                                # User wants to quit early - will show progress bar
                                user_quit_early = True
                                break
                            elif char == 'j' and ui.is_complete:
                                # Exit Live view first, then open file
                                file_to_open = 'j'
                                break
                            elif char == 'r' and ui.is_complete:
                                # Exit Live view first, then open file
                                file_to_open = 'r'
                                break
                        
                        # Update UI
                        live.update(ui)
                        
                        # Check if complete
                        if ui.is_complete and not stop_event.is_set():
                            time.sleep(1)
                            stop_event.set()
                            ui.set_complete(group_id)
                            live.update(ui)
                            break
            finally:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        
        # If user quit early, show progress bar for remaining time
        if user_quit_early and not ui.is_complete:
            console.clear()
            console.print(Panel.fit(
                "[bold yellow]Waiting for sessions to complete...[/bold yellow]\n\n"
                "[dim]Sessions are still running in the background. Please wait for them to finish.[/dim]",
                border_style="yellow",
                title="Background Processing"
            ))
            console.print()
            
            # Calculate total and remaining time
            total_duration_seconds = (config['duration_minutes'] + 0.5) * 60  # Duration + 30 seconds
            elapsed_seconds = (datetime.now() - ui.start_time).total_seconds()
            remaining_seconds = max(0, total_duration_seconds - elapsed_seconds)
            
            # Show progress bar
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task = progress.add_task(
                    "[cyan]Waiting for sessions to complete...",
                    total=total_duration_seconds
                )
                
                # Set initial progress based on elapsed time
                progress.update(task, completed=elapsed_seconds)
                
                while remaining_seconds > 0 and not ui.is_complete:
                    # Update progress based on elapsed time
                    elapsed_seconds = (datetime.now() - ui.start_time).total_seconds()
                    progress.update(task, completed=min(total_duration_seconds, elapsed_seconds))
                    
                    # Continue polling in background
                    if not stop_event.is_set():
                        for session_id in ui.session_ids:
                            try:
                                response = api_client.get_session_messages(session_id)
                                messages = response.get('messages', [])
                                ui.update_session(session_id, messages)
                            except:
                                pass
                    
                    # Check if actually complete
                    if ui.is_complete:
                        progress.update(task, completed=total_duration_seconds)
                        break
                    
                    # Recalculate remaining time
                    elapsed_seconds = (datetime.now() - ui.start_time).total_seconds()
                    remaining_seconds = max(0, total_duration_seconds - elapsed_seconds)
                    
                    time.sleep(1)
                
                # Ensure we mark as complete
                if ui.group_id and not ui.is_complete:
                    ui.set_complete(group_id)
                
                progress.update(task, completed=total_duration_seconds)
                time.sleep(0.5)
        
        # Show completion and wait for user input
        console.clear()
        ui.set_complete(group_id)
        ui.show_completion_message()
        
        # If user pressed J or R during Live view, open that file now
        if file_to_open == 'j' and ui.log_url:
            open_url_in_nano(ui.log_url, ui)
        elif file_to_open == 'r' and ui.report_url:
            open_url_in_nano(ui.report_url, ui)
        
        # Final menu loop - just listen for input, completion message already shown
        while True:
            if is_windows:
                if msvcrt and msvcrt.kbhit():
                    try:
                        char = msvcrt.getch().decode('utf-8').lower()
                    except:
                        char = ''
                    if char == 'q':
                        break
                    elif char == 'j' and ui.log_url:
                        open_url_in_nano(ui.log_url, ui)
                    elif char == 'r' and ui.report_url:
                        open_url_in_nano(ui.report_url, ui)
                time.sleep(0.1)
            else:
                import select
                if select.select([sys.stdin], [], [], 0.5)[0]:
                    char = sys.stdin.read(1).lower()
                    if char == 'q':
                        break
                    elif char == 'j' and ui.log_url:
                        open_url_in_nano(ui.log_url, ui)
                    elif char == 'r' and ui.report_url:
                        open_url_in_nano(ui.report_url, ui)
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        stop_event.set()
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        stop_event.set()
        import traceback
        traceback.print_exc()
    finally:
        stop_event.set()
        console.print("\n[dim]Cleaning up...[/dim]")


if __name__ == "__main__":
    main()

