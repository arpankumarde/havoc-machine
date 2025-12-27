#!/usr/bin/env python3
"""Simple pipeline: Fetch files from Google Drive, then create and store embeddings."""

import os
import asyncio
import sys
from dotenv import load_dotenv

from utils import watch_drive_step, process_embeddings_step

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
    
    # Step 2: Process files and create embeddings
    print(f"\n🧠 Step 2: Processing files and creating embeddings...")
    try:
        results = await process_embeddings_step(
            directory=DOWNLOAD_DIR,
            replace_existing=True  # Upsert: replace existing embeddings
        )
        
        # Summary
        successful = [r for r in results if 'error' not in r]
        failed = [r for r in results if 'error' in r]
        
        print(f"\n✓ Pipeline completed!")
        print(f"  • Successfully processed: {len(successful)} files")
        if failed:
            print(f"  • Failed: {len(failed)} files")
            for result in failed:
                print(f"    - {result.get('file_path', 'unknown')}: {result.get('error')}")
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
