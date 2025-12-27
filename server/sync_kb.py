#!/usr/bin/env python3

import os
import asyncio
from dotenv import load_dotenv

from utils import watch_drive_step, sync_embeddings_step

load_dotenv()

WATCH_FOLDER_ID = os.getenv("WATCH_FOLDER_ID")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
SYNC_INTERVAL = 5


async def sync_kb_once():
    try:
        watcher = await watch_drive_step(
            folder_id=WATCH_FOLDER_ID,
            initialize=False,
            watch=False
        )
        
        results = await sync_embeddings_step(directory=DOWNLOAD_DIR)
        
        return results
    except Exception as e:
        print(f"SyncKB error: {e}")
        return None


async def sync_kb_loop():
    print("Starting SyncKB background process...")
    print(f"Syncing every {SYNC_INTERVAL} seconds")
    
    print("\nInitial sync...")
    await sync_kb_once()
    
    while True:
        await asyncio.sleep(SYNC_INTERVAL)
        await sync_kb_once()


async def run_sync_kb():
    if not WATCH_FOLDER_ID:
        raise ValueError("WATCH_FOLDER_ID not set in environment")
    
    try:
        await sync_kb_loop()
    except KeyboardInterrupt:
        print("\nSyncKB stopped")
    except Exception as e:
        print(f"SyncKB fatal error: {e}")
        raise

