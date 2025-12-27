#!/usr/bin/env python3
"""Simple pipeline: Fetch files from Google Drive, then create and store embeddings."""

import os
import asyncio
import sys
from dotenv import load_dotenv

from utils import watch_drive_step, sync_embeddings_step

load_dotenv()

# Configuration from environment
WATCH_FOLDER_ID = os.getenv("WATCH_FOLDER_ID")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")


async def main():
    """Main pipeline: fetch files, then process embeddings."""
    
    # Validate required environment variables
    if not WATCH_FOLDER_ID:
        print("❌ Error: WATCH_FOLDER_ID not set in environment")
        print("   Please set WATCH_FOLDER_ID in your .env file")
        sys.exit(1)
    
    print("🚀 Starting pipeline...")
    print("=" * 60)
    
    # Step 1: Fetch files from Google Drive
    print("\n📥 Step 1: Fetching files from Google Drive...")
    try:
        watcher = await watch_drive_step(
            folder_id=WATCH_FOLDER_ID,
            initialize=True,  # Initialize and sync existing files
            watch=False  # Single sync, don't watch continuously
        )
        print("✓ Files fetched successfully")
    except Exception as e:
        print(f"❌ Error fetching files: {e}")
        sys.exit(1)
    
    # Step 2: Sync embeddings (insert new, update changed, delete removed)
    print(f"\n🧠 Step 2: Syncing embeddings with files...")
    try:
        results = await sync_embeddings_step(
            directory=DOWNLOAD_DIR
        )
        
        # Summary
        print(f"\n✓ Pipeline completed!")
        print(f"  • Inserted: {len(results['inserted'])} files")
        print(f"  • Updated: {len(results['updated'])} files")
        print(f"  • Deleted: {len(results['deleted'])} files")
        if results['errors']:
            print(f"  • Errors: {len(results['errors'])} files")
            for error in results['errors']:
                print(f"    - {error.get('file_path', 'unknown')}: {error.get('error')}")
    except ConnectionError as e:
        print(str(e))
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error processing embeddings: {e}")
        sys.exit(1)
    
    print("=" * 60)
    print("✅ Pipeline finished successfully!")


if __name__ == "__main__":
    asyncio.run(main())
