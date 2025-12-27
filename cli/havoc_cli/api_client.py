"""API client for interacting with the Havoc Machine server"""

import requests
from typing import Dict, List, Any, Optional
from rich.console import Console

console = Console()


class APIClient:
    """Client for making API requests to the Havoc Machine server"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the API client
        
        Args:
            base_url: Base URL of the server (default: http://localhost:8000)
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
        })
    
    def start_parallel_adversarial(
        self,
        websocket_url: str,
        parallel_executions: int,
        duration_minutes: float
    ) -> Dict[str, Any]:
        """
        Start parallel adversarial testing
        
        Args:
            websocket_url: WebSocket URL for the agent server
            parallel_executions: Number of parallel sessions
            duration_minutes: Duration in minutes
            
        Returns:
            Response containing group_id, session_ids, status, and message
        """
        url = f"{self.base_url}/api/adversarial/parallel"
        payload = {
            "websocket_url": websocket_url,
            "parallel_executions": parallel_executions,
            "duration_minutes": duration_minutes,
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error starting adversarial test: {e}[/red]")
            raise
    
    def get_session_messages(self, session_id: str) -> Dict[str, Any]:
        """
        Get messages for a specific session
        
        Args:
            session_id: The session ID to retrieve messages for
            
        Returns:
            Response containing session_id, message_count, and messages
        """
        url = f"{self.base_url}/api/session/{session_id}/messages"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error fetching messages for session {session_id}: {e}[/red]")
            return {
                "session_id": session_id,
                "message_count": 0,
                "messages": []
            }
    
    def get_group_metadata(self, group_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a group
        
        Args:
            group_id: The group ID to retrieve metadata for
            
        Returns:
            Group metadata or None if error
        """
        url = f"{self.base_url}/api/groups/{group_id}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            console.print(f"[yellow]Warning: Could not fetch group metadata: {e}[/yellow]")
            return None

