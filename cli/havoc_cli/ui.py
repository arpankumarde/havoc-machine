"""Terminal UI components for the CLI"""

import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.align import Align

console = Console()


class SessionWindow:
    """Represents a single session window in the terminal"""
    
    def __init__(self, session_id: str, index: int):
        self.session_id = session_id
        self.index = index
        self.messages: List[Dict[str, Any]] = []
        self.last_update = None
    
    def update_messages(self, messages: List[Dict[str, Any]]):
        """Update messages for this session"""
        # Messages come in descending order (newest first), reverse for display
        self.messages = list(reversed(messages))
        self.last_update = datetime.now()
    
    def render(self, width: int, height: int) -> Panel:
        """Render this session window"""
        # Header
        header_text = Text(f"Session {self.index + 1} - {self.session_id[:20]}...", style="bold cyan")
        if self.last_update:
            header_text.append(f" | Last update: {self.last_update.strftime('%H:%M:%S')}", style="dim")
        
        # Messages content
        if not self.messages:
            content = Text("Waiting for messages...", style="dim italic")
        else:
            content = Text()
            # Calculate available width for messages (account for padding and borders)
            # Panel has ~4 chars padding, timestamp is ~10 chars, label is ~5 chars
            # Use more width on larger screens - only leave small margin
            if width > 100:
                available_width = width - 25  # Large screen: use most of the width
            elif width > 60:
                available_width = width - 20  # Medium screen: reasonable margin
            else:
                available_width = max(40, width - 15)  # Small screen: minimum 40 chars
            
            # Calculate how many messages to show based on available height
            # Each message takes ~2-3 lines, so we can show more on larger screens
            available_height = max(5, height - 4)  # Account for panel borders
            max_messages = min(len(self.messages), max(10, available_height // 2))
            
            for msg in self.messages[-max_messages:]:  # Show messages based on available space
                msg_type = msg.get('type', 'unknown')
                timestamp = msg.get('timestamp', '')
                msg_content = msg.get('content', '')
                
                # Format timestamp
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime('%H:%M:%S')
                    except:
                        time_str = timestamp[:8] if len(timestamp) > 8 else timestamp
                else:
                    time_str = ""
                
                # Format message with smart wrapping/truncation
                if msg_type == 'human':
                    content.append(f"[{time_str}] ", style="dim")
                    content.append("YOU: ", style="bold red")
                    # Use more of the available width, only truncate if really necessary
                    if len(msg_content) <= available_width:
                        content.append(msg_content, style="white")
                    else:
                        # Show as much as possible, but allow some truncation for very long messages
                        truncate_at = available_width - 3  # Leave room for "..."
                        content.append(msg_content[:truncate_at] + "...", style="white")
                elif msg_type == 'ai':
                    content.append(f"[{time_str}] ", style="dim")
                    content.append("AI: ", style="bold green")
                    # Use more of the available width
                    if len(msg_content) <= available_width:
                        content.append(msg_content, style="white")
                    else:
                        truncate_at = available_width - 3
                        content.append(msg_content[:truncate_at] + "...", style="white")
                else:
                    if len(msg_content) <= available_width:
                        content.append(f"[{time_str}] {msg_content}", style="dim")
                    else:
                        truncate_at = available_width - len(time_str) - 5
                        content.append(f"[{time_str}] {msg_content[:truncate_at]}...", style="dim")
                
                content.append("\n")
        
        return Panel(
            content,
            title=header_text,
            border_style="cyan",
            width=width,
            height=height
        )


class TerminalUI:
    """Main terminal UI manager"""
    
    def __init__(self, session_ids: List[str], duration_minutes: float):
        self.session_ids = session_ids
        self.duration_minutes = duration_minutes
        self.session_windows = [
            SessionWindow(sid, i) for i, sid in enumerate(session_ids)
        ]
        self.start_time = datetime.now()
        self.is_complete = False
        self.group_id: Optional[str] = None
        self.report_url: Optional[str] = None
        self.log_url: Optional[str] = None
    
    def update_session(self, session_id: str, messages: List[Dict[str, Any]]):
        """Update messages for a specific session"""
        for window in self.session_windows:
            if window.session_id == session_id:
                window.update_messages(messages)
                break
    
    def set_complete(self, group_id: str):
        """Mark the test as complete and set URLs"""
        self.is_complete = True
        self.group_id = group_id
        
        # Remove "grp-" prefix if present
        group_id_without_prefix = group_id[4:] if group_id.startswith("grp-") else group_id
        
        self.report_url = f"https://sprintingn.s3.amazonaws.com/havoc-machine/{group_id_without_prefix}.md"
        self.log_url = f"https://sprintingn.s3.amazonaws.com/havoc-machine/{group_id_without_prefix}.json"
    
    def create_layout(self, console_width: int, console_height: int) -> Layout:
        """Create the terminal layout"""
        layout = Layout()
        
        # Calculate window dimensions
        num_sessions = len(self.session_windows)
        if num_sessions == 0:
            num_sessions = 1  # Prevent division by zero
        window_width = max(40, console_width // num_sessions)  # Minimum width of 40
        window_height = max(10, console_height - 6)  # Leave space for header and footer, minimum height 10
        
        # Create header
        elapsed = datetime.now() - self.start_time
        elapsed_str = str(elapsed).split('.')[0]  # Remove microseconds
        
        header_text = Text()
        header_text.append("HAVOC MACHINE - Parallel Adversarial Testing", style="bold red")
        header_text.append(f" | Duration: {self.duration_minutes} min | Elapsed: {elapsed_str}", style="dim")
        if self.is_complete:
            header_text.append(" | [COMPLETE]", style="bold green")
        
        header = Panel(
            Align.center(header_text),
            border_style="red",
            height=3
        )
        
        # Create session windows
        session_panels = []
        for window in self.session_windows:
            panel = window.render(window_width - 2, window_height)
            session_panels.append(panel)
        
        # Create footer with menu
        footer_text = Text()
        if self.is_complete:
            footer_text.append("Press ", style="dim")
            footer_text.append("J", style="bold yellow")
            footer_text.append(" to view JSON logs | ", style="dim")
            footer_text.append("R", style="bold yellow")
            footer_text.append(" to view Report | ", style="dim")
            footer_text.append("Q", style="bold yellow")
            footer_text.append(" to quit", style="dim")
        else:
            footer_text.append("Polling messages... | Press ", style="dim")
            footer_text.append("Q", style="bold yellow")
            footer_text.append(" to quit", style="dim")
        
        footer = Panel(
            Align.center(footer_text),
            border_style="dim",
            height=3
        )
        
        # Build layout
        layout.split_column(
            Layout(header, size=3),
            Layout(name="sessions"),
            Layout(footer, size=3)
        )
        
        # Split sessions horizontally
        layout["sessions"].split_row(*[Layout(panel) for panel in session_panels])
        
        return layout
    
    def __rich__(self) -> RenderableType:
        """Render the UI for Rich"""
        # Get console size
        try:
            size = console.size
            console_width = size.width
            console_height = size.height
        except:
            console_width = 120
            console_height = 40
        
        return self.create_layout(console_width, console_height)
    
    def render(self, console_width: int = 120, console_height: int = 40):
        """Render the UI (legacy method)"""
        return self.__rich__()
    
    def show_completion_message(self):
        """Show completion message with URLs"""
        console.print()
        console.print(Panel.fit(
            "[bold cyan]✓ Testing Complete![/bold cyan]\n\n"
            f"[cyan]Report URL:[/cyan] {self.report_url}\n"
            f"[cyan]Log URL:[/cyan] {self.log_url}\n\n"
            "[dim]Press J to view JSON logs, R to view Report, or Q to quit[/dim]",
            border_style="cyan",
            title="Completion"
        ))

