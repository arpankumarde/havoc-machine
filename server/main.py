#!/usr/bin/env python3

import os
import asyncio
import sys
import threading
from dotenv import load_dotenv

from sync_kb import sync_kb_loop
from agent_server import app
import uvicorn

load_dotenv()

WATCH_FOLDER_ID = os.getenv("WATCH_FOLDER_ID")
AGENT_HOST = os.getenv("AGENT_HOST", "0.0.0.0")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8000"))


def run_agent_server():
    uvicorn.run(app, host=AGENT_HOST, port=AGENT_PORT, log_level="info")


async def run_all():
    if not WATCH_FOLDER_ID:
        print("Error: WATCH_FOLDER_ID not set in environment")
        print("Please set WATCH_FOLDER_ID in your .env file")
        sys.exit(1)
    
    print("Starting Havoc Machine Server...")
    print("=" * 60)
    print(f"SyncKB: Running every 5 seconds")
    print(f"Agent Server: http://{AGENT_HOST}:{AGENT_PORT}")
    print(f"WebSocket: ws://{AGENT_HOST}:{AGENT_PORT}/ws/{{session_id}}")
    print("=" * 60)
    
    server_thread = threading.Thread(target=run_agent_server, daemon=True)
    server_thread.start()
    
    await asyncio.sleep(1)
    
    try:
        await sync_kb_loop()
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(run_all())
    except KeyboardInterrupt:
        print("\nServer stopped")
