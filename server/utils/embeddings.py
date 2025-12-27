#!/usr/bin/env python3
"""Utility for processing documents with docling, creating embeddings via OpenRouter,
and storing chunks with embeddings in MongoDB.
Can be used as a step in a linear pipeline."""

import os
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Any
from functools import wraps
import hashlib

from dotenv import load_dotenv
from docling.document_converter import DocumentConverter
from pymongo import MongoClient
from pymongo.collection import Collection
from openai import OpenAI

load_dotenv()

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENAI_API_KEY")  # OpenRouter key stored as OPENAI_API_KEY
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536  # text-embedding-3-small dimensions
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "havoc_machine")
MONGODB_COLLECTION_NAME = os.getenv("MONGODB_COLLECTION_NAME", "document_chunks")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))  # Characters per chunk
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))  # Overlap between chunks
MAX_RETRIES = 3
RETRY_DELAY = 1


def retry_async(max_retries=MAX_RETRIES, delay=RETRY_DELAY):
    """Async retry decorator with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)
                        print(f"⚠️  Retry {attempt + 1}/{max_retries} for {func.__name__} after {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                    else:
                        print(f"✗ Failed after {max_retries} retries: {func.__name__} - {e}")
            raise last_exception
        return wrapper
    return decorator


class EmbeddingProcessor:
    """Processes documents, creates embeddings, and stores them in MongoDB."""
    
    def __init__(
        self,
        mongodb_uri: str = MONGODB_URI,
        db_name: str = MONGODB_DB_NAME,
        collection_name: str = MONGODB_COLLECTION_NAME,
        openrouter_api_key: Optional[str] = None,
        openrouter_base_url: str = OPENROUTER_BASE_URL,
        embedding_model: str = EMBEDDING_MODEL,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP
    ):
        self.mongodb_uri = mongodb_uri
        self.db_name = db_name
        self.collection_name = collection_name
        self.openrouter_api_key = openrouter_api_key or OPENROUTER_API_KEY
        self.openrouter_base_url = openrouter_base_url
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize clients - MongoDB is required
        try:
            self.mongo_client = MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=5000)
            # Test connection
            self.mongo_client.admin.command('ping')
            self.db = self.mongo_client[self.db_name]
            self.collection: Collection = self.db[self.collection_name]
            # Create indexes for efficient queries
            self._create_indexes()
            print("✓ Connected to MongoDB")
        except Exception as e:
            error_msg = (
                f"\n❌ MongoDB connection failed!\n"
                f"   URI: {self.mongodb_uri}\n"
                f"   Error: {e}\n\n"
                f"   Please ensure MongoDB is running and accessible.\n"
                f"   You can start MongoDB with: mongod\n"
                f"   Or update MONGODB_URI in your .env file if using a remote instance.\n"
            )
            raise ConnectionError(error_msg) from e
        
        # Initialize OpenAI client for OpenRouter
        self.openai_client = OpenAI(
            api_key=self.openrouter_api_key,
            base_url=self.openrouter_base_url
        )
        
        # Initialize docling converter
        self.converter = DocumentConverter()
    
    def _create_indexes(self):
        """Create MongoDB indexes for efficient queries."""
        try:
            # Index on file_path for quick lookups
            self.collection.create_index("file_path")
            # Index on file_hash to check if file was already processed
            self.collection.create_index("file_hash", unique=False)
            # Index on embedding for vector search (if using vector search later)
            # Note: MongoDB Atlas supports vector search, but for now we'll store as array
            print("✓ Created MongoDB indexes")
        except Exception as e:
            print(f"⚠️  Index creation warning: {e}")
    
    def _get_file_hash(self, file_path: str) -> str:
        """Generate hash of file for change detection."""
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        return file_hash
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary if not at end
            if end < len(text):
                # Look for sentence endings
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > self.chunk_size // 2:  # Only break if reasonable
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append(chunk.strip())
            start = end - self.chunk_overlap  # Overlap for context
        
        return chunks
    
    async def _create_embedding(self, text: str) -> List[float]:
        """Create embedding for text using OpenRouter."""
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=text
                )
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"✗ Embedding error: {e}")
            raise
    
    async def _process_file(self, file_path: str) -> Dict[str, Any]:
        """Process a single file and return chunks with metadata."""
        file_path_obj = Path(file_path).resolve()
        file_path = str(file_path_obj)
        file_ext = file_path_obj.suffix.lower()
        file_name = file_path_obj.name
        
        print(f"📄 Processing: {file_name}")
        
        # Get file hash and size BEFORE processing (in case file changes during processing)
        file_hash = self._get_file_hash(file_path)
        file_size = os.path.getsize(file_path)
        
        # Extract text based on file type
        if file_ext == '.pdf':
            result = self.converter.convert(file_path)
            try:
                text = result.document.export_to_markdown()
            except AttributeError:
                try:
                    text = result.document.export_to_text()
                except AttributeError:
                    text = str(result.document)
        elif file_ext == '.md':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        # Chunk the text
        chunks = self._chunk_text(text)
        print(f"  → Created {len(chunks)} chunks")
        
        # Create embeddings for each chunk
        chunk_embeddings = []
        for i, chunk in enumerate(chunks, 1):
            print(f"  → Creating embedding for chunk {i}/{len(chunks)}")
            embedding = await self._create_embedding(chunk)
            chunk_embeddings.append({
                'chunk_index': i - 1,
                'text': chunk,
                'embedding': embedding,
                'chunk_size': len(chunk)
            })
        
        return {
            'file_path': file_path,
            'file_name': file_name,
            'file_hash': file_hash,
            'file_size': file_size,
            'total_chunks': len(chunks),
            'chunks': chunk_embeddings
        }
    
    async def _store_chunks(self, processed_file: Dict[str, Any], replace_existing: bool = True):
        """Store chunks in MongoDB."""
        file_path = processed_file['file_path']
        file_name = processed_file['file_name']
        
        # Check if file already exists
        if not replace_existing and self.collection.find_one({"file_path": file_path}):
            print(f"  ⏭️  Skipping {file_name} (already exists)")
            return
        
        # Delete existing chunks for this file if replacing
        if replace_existing:
            deleted = self.collection.delete_many({"file_path": file_path}).deleted_count
            if deleted > 0:
                print(f"  🔄 Replacing existing chunks for {file_name}")
        
        # Build documents to insert
        documents_to_insert = [{
            'file_path': file_path,
            'file_name': file_name,
            'file_hash': processed_file['file_hash'],
            'file_size': processed_file['file_size'],
            'chunk_index': chunk['chunk_index'],
            'text': chunk['text'],
            'embedding': chunk['embedding'],
            'chunk_size': chunk['chunk_size'],
            'total_chunks': processed_file['total_chunks'],
            'metadata': {
                'model': self.embedding_model,
                'dimensions': EMBEDDING_DIMENSIONS
            }
        } for chunk in processed_file['chunks']]
        
        # Bulk insert
        if documents_to_insert:
            self.collection.insert_many(documents_to_insert)
            print(f"  ✓ Stored {len(documents_to_insert)} chunks for {file_name}")
    
    @retry_async()
    async def process_file(self, file_path: str, replace_existing: bool = True) -> Dict[str, Any]:
        """Process a single file: extract text, chunk, embed, and store.
        
        Args:
            file_path: Path to the file to process
            replace_existing: Whether to replace existing chunks if file was already processed
        
        Returns:
            Dict with processing results
        """
        processed = await self._process_file(file_path)
        await self._store_chunks(processed, replace_existing=replace_existing)
        return processed
    
    async def process_directory(
        self,
        directory: str,
        file_extensions: Optional[List[str]] = None,
        replace_existing: bool = True
    ) -> List[Dict[str, Any]]:
        """Process all supported files in a directory.
        
        Args:
            directory: Directory path to process
            file_extensions: List of file extensions to process (default: ['.pdf', '.md'])
            replace_existing: Whether to replace existing chunks
        
        Returns:
            List of processing results for each file
        """
        if file_extensions is None:
            file_extensions = ['.pdf', '.md']
        
        directory_path = Path(directory)
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        # Find all files with supported extensions
        files = [
            str(f) for f in directory_path.iterdir()
            if f.is_file() and f.suffix.lower() in file_extensions
        ]
        
        if not files:
            print(f"⚠️  No supported files found in {directory}")
            return []
        
        print(f"📁 Processing {len(files)} files from {directory}")
        
        # Process files sequentially (to avoid rate limits)
        results = []
        for file_path in files:
            try:
                results.append(await self.process_file(file_path, replace_existing=replace_existing))
            except Exception as e:
                print(f"✗ Failed to process {file_path}: {e}")
                results.append({'file_path': file_path, 'error': str(e)})
        
        return results
    
    def get_chunks_for_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Retrieve all chunks for a specific file from MongoDB."""
        # Normalize path to match how it's stored
        normalized_path = str(Path(file_path).resolve())
        chunks = list(self.collection.find({"file_path": normalized_path}).sort("chunk_index", 1))
        # Convert ObjectId to string for JSON serialization
        for chunk in chunks:
            chunk['_id'] = str(chunk['_id'])
        return chunks
    
    def delete_embeddings_for_file(self, file_path: str) -> int:
        """Delete all embeddings/chunks for a specific file.
        
        Args:
            file_path: Path to the file whose embeddings should be deleted
        
        Returns:
            Number of chunks deleted
        """
        # Normalize path to match how it's stored
        normalized_path = str(Path(file_path).resolve())
        result = self.collection.delete_many({"file_path": normalized_path})
        deleted_count = result.deleted_count
        if deleted_count > 0:
            print(f"  🗑️  Deleted {deleted_count} chunks for {Path(file_path).name}")
        return deleted_count
    
    def get_processed_files(self) -> Dict[str, Dict[str, Any]]:
        """Get all processed files from MongoDB with their hashes.
        
        Returns:
            Dict mapping file_path to file metadata (file_hash, file_name, etc.)
        """
        pipeline = [{"$group": {
            "_id": "$file_path",
            "file_hash": {"$first": "$file_hash"},
            "file_name": {"$first": "$file_name"},
            "file_size": {"$first": "$file_size"},
            "total_chunks": {"$first": "$total_chunks"}
        }}]
        
        return {
            doc['_id']: {
                'file_hash': doc.get('file_hash'),
                'file_name': doc.get('file_name'),
                'file_size': doc.get('file_size'),
                'total_chunks': doc.get('total_chunks')
            }
            for doc in self.collection.aggregate(pipeline)
        }
    
    async def sync_embeddings(
        self,
        directory: str,
        file_extensions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Sync embeddings with files in directory: insert new, update changed, delete removed.
        
        This method keeps embeddings in sync with the directory, treating the directory
        as the single source of truth.
        
        Args:
            directory: Directory path to sync
            file_extensions: List of file extensions to process (default: ['.pdf', '.md'])
        
        Returns:
            Dict with sync results: {'inserted': [], 'updated': [], 'deleted': [], 'errors': []}
        """
        if file_extensions is None:
            file_extensions = ['.pdf', '.md']
        
        directory_path = Path(directory)
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        # Get all processed files from MongoDB
        processed_files = self.get_processed_files()
        print(f"📊 Found {len(processed_files)} processed files in database")
        
        # Get all files in directory (normalize to absolute paths)
        directory_abs = directory_path.resolve()
        local_files = {
            str(file_path.resolve()): {'file_name': file_path.name}
            for file_path in directory_abs.iterdir()
            if file_path.is_file() and file_path.suffix.lower() in file_extensions
        }
        
        print(f"📁 Found {len(local_files)} files in directory")
        
        # Determine what needs to be done
        to_insert = []
        to_update = []
        to_delete = []
        
        # Check local files (compute hashes once)
        file_hashes = {}
        for file_path in local_files:
            if file_path not in processed_files:
                to_insert.append(file_path)
            else:
                # Compute hash once and store for later use
                file_hash = self._get_file_hash(file_path)
                file_hashes[file_path] = file_hash
                if file_hash != processed_files[file_path].get('file_hash'):
                    to_update.append(file_path)
        
        # Check for deleted files (in DB but not in directory)
        to_delete = [fp for fp in processed_files if fp not in local_files]
        
        print(f"\n🔄 Sync plan:")
        print(f"  • New files: {len(to_insert)}")
        print(f"  • Updated files: {len(to_update)}")
        print(f"  • Deleted files: {len(to_delete)}")
        
        results = {'inserted': [], 'updated': [], 'deleted': [], 'errors': []}
        
        async def _process_with_error_handling(file_path: str, action: str):
            """Helper to process file with error handling."""
            try:
                return await self.process_file(file_path, replace_existing=True)
            except Exception as e:
                results['errors'].append({'file_path': file_path, 'error': str(e)})
                print(f"✗ Failed to {action} {file_path}: {e}")
                return None
        
        # Process inserts (new files)
        if to_insert:
            print(f"\n✨ Processing {len(to_insert)} new files...")
            for file_path in to_insert:
                processed = await _process_with_error_handling(file_path, 'process')
                if processed:
                    results['inserted'].append(processed)
        
        # Process updates (changed files)
        if to_update:
            print(f"\n📝 Processing {len(to_update)} updated files...")
            for file_path in to_update:
                processed = await _process_with_error_handling(file_path, 'update')
                if processed:
                    results['updated'].append(processed)
        
        # Process deletes (removed files)
        if to_delete:
            print(f"\n🗑️  Processing {len(to_delete)} deleted files...")
            for file_path in to_delete:
                try:
                    deleted_count = self.delete_embeddings_for_file(file_path)
                    results['deleted'].append({
                        'file_path': file_path,
                        'file_name': processed_files[file_path].get('file_name', Path(file_path).name),
                        'chunks_deleted': deleted_count
                    })
                except Exception as e:
                    results['errors'].append({'file_path': file_path, 'error': str(e)})
                    print(f"✗ Failed to delete embeddings for {file_path}: {e}")
        
        # Summary
        print(f"\n✓ Sync completed!")
        print(f"  • Inserted: {len(results['inserted'])} files")
        print(f"  • Updated: {len(results['updated'])} files")
        print(f"  • Deleted: {len(results['deleted'])} files")
        if results['errors']:
            print(f"  • Errors: {len(results['errors'])} files")
        
        return results
    
    def close(self):
        """Close MongoDB connection."""
        self.mongo_client.close()


def _create_processor(
    mongodb_uri: Optional[str] = None,
    db_name: Optional[str] = None,
    collection_name: Optional[str] = None,
    openrouter_api_key: Optional[str] = None,
    openrouter_base_url: Optional[str] = None,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP
) -> EmbeddingProcessor:
    """Helper to create EmbeddingProcessor with defaults."""
    return EmbeddingProcessor(
        mongodb_uri=mongodb_uri or MONGODB_URI,
        db_name=db_name or MONGODB_DB_NAME,
        collection_name=collection_name or MONGODB_COLLECTION_NAME,
        openrouter_api_key=openrouter_api_key,
        openrouter_base_url=openrouter_base_url or OPENROUTER_BASE_URL,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )


async def process_embeddings_step(
    directory: str,
    mongodb_uri: Optional[str] = None,
    db_name: Optional[str] = None,
    collection_name: Optional[str] = None,
    openrouter_api_key: Optional[str] = None,
    openrouter_base_url: Optional[str] = None,
    file_extensions: Optional[List[str]] = None,
    replace_existing: bool = True,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP
) -> List[Dict[str, Any]]:
    """Pipeline step function to process files and create embeddings.
    
    Args:
        directory: Directory containing files to process
        mongodb_uri: MongoDB connection URI
        db_name: MongoDB database name
        collection_name: MongoDB collection name
        openrouter_api_key: OpenRouter API key (uses env var if not provided)
        openrouter_base_url: OpenRouter base URL
        file_extensions: List of file extensions to process (default: ['.pdf', '.md'])
        replace_existing: Whether to replace existing chunks
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
    
    Returns:
        List of processing results for each file
    """
    processor = _create_processor(
        mongodb_uri, db_name, collection_name, openrouter_api_key,
        openrouter_base_url, chunk_size, chunk_overlap
    )
    
    try:
        return await processor.process_directory(
            directory=directory,
            file_extensions=file_extensions,
            replace_existing=replace_existing
        )
    finally:
        processor.close()


async def sync_embeddings_step(
    directory: str,
    mongodb_uri: Optional[str] = None,
    db_name: Optional[str] = None,
    collection_name: Optional[str] = None,
    openrouter_api_key: Optional[str] = None,
    openrouter_base_url: Optional[str] = None,
    file_extensions: Optional[List[str]] = None,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP
) -> Dict[str, Any]:
    """Pipeline step function to sync embeddings with directory (insert, update, delete).
    
    This keeps embeddings in sync with the directory, treating the directory as the
    single source of truth. It will:
    - Insert embeddings for new files
    - Update embeddings for changed files (detected by hash)
    - Delete embeddings for removed files
    
    Args:
        directory: Directory containing files to sync
        mongodb_uri: MongoDB connection URI
        db_name: MongoDB database name
        collection_name: MongoDB collection name
        openrouter_api_key: OpenRouter API key (uses env var if not provided)
        openrouter_base_url: OpenRouter base URL
        file_extensions: List of file extensions to process (default: ['.pdf', '.md'])
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
    
    Returns:
        Dict with sync results: {'inserted': [], 'updated': [], 'deleted': [], 'errors': []}
    """
    processor = _create_processor(
        mongodb_uri, db_name, collection_name, openrouter_api_key,
        openrouter_base_url, chunk_size, chunk_overlap
    )
    
    try:
        return await processor.sync_embeddings(
            directory=directory,
            file_extensions=file_extensions
        )
    finally:
        processor.close()

