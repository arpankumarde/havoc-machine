#!/usr/bin/env python3
"""SyncKB: Continuously syncs knowledge base from Google Drive to MongoDB embeddings.
Runs every 5 seconds in the background."""

import os
import asyncio
from dotenv import load_dotenv

from utils import watch_drive_step, sync_embeddings_step

load_dotenv()

# Configuration from environment
WATCH_FOLDER_ID = os.getenv("WATCH_FOLDER_ID")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
SYNC_INTERVAL = 5  # seconds


async def sync_kb_once():
    """Perform a single sync operation."""
    try:
        # Step 1: Sync files from Google Drive
        watcher = await watch_drive_step(
            folder_id=WATCH_FOLDER_ID,
            initialize=False,  # Don't re-initialize, just sync changes
            watch=False  # Single sync
        )
        
        # Step 2: Sync embeddings with files
        results = await sync_embeddings_step(directory=DOWNLOAD_DIR)
        
        return results
    except Exception as e:
        print(f"⚠️  SyncKB error: {e}")
        return None


async def sync_kb_loop():
    """Run syncKB continuously every SYNC_INTERVAL seconds."""
    print("🔄 Starting SyncKB background process...")
    print(f"   Syncing every {SYNC_INTERVAL} seconds")
    
    # Initial sync
    print("\n📥 Initial sync...")
    await sync_kb_once()
    
    # Continuous sync loop
    while True:
        await asyncio.sleep(SYNC_INTERVAL)
        await sync_kb_once()


async def run_sync_kb():
    """Main entry point for syncKB."""
    if not WATCH_FOLDER_ID:
        raise ValueError("WATCH_FOLDER_ID not set in environment")
    
    try:
        await sync_kb_loop()
    except KeyboardInterrupt:
        print("\n🛑 SyncKB stopped")
    except Exception as e:
        print(f"❌ SyncKB fatal error: {e}")
        raise

