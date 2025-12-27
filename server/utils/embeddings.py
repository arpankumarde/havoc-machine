#!/usr/bin/env python3

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

OPENROUTER_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "havoc_machine")
MONGODB_COLLECTION_NAME = os.getenv("MONGODB_COLLECTION_NAME", "document_chunks")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
MAX_RETRIES = 3
RETRY_DELAY = 1


def retry_async(max_retries=MAX_RETRIES, delay=RETRY_DELAY):
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
                        print(f"Retry {attempt + 1}/{max_retries} for {func.__name__} after {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                    else:
                        print(f"Failed after {max_retries} retries: {func.__name__} - {e}")
            raise last_exception
        return wrapper
    return decorator


class EmbeddingProcessor:
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
        
        try:
            self.mongo_client = MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=5000)
            self.mongo_client.admin.command('ping')
            self.db = self.mongo_client[self.db_name]
            self.collection: Collection = self.db[self.collection_name]
            self._create_indexes()
            print("Connected to MongoDB")
        except Exception as e:
            error_msg = (
                f"\nMongoDB connection failed!\n"
                f"   URI: {self.mongodb_uri}\n"
                f"   Error: {e}\n\n"
                f"   Please ensure MongoDB is running and accessible.\n"
                f"   You can start MongoDB with: mongod\n"
                f"   Or update MONGODB_URI in your .env file if using a remote instance.\n"
            )
            raise ConnectionError(error_msg) from e
        
        self.openai_client = OpenAI(
            api_key=self.openrouter_api_key,
            base_url=self.openrouter_base_url
        )
        
        self.converter = DocumentConverter()
    
    def _create_indexes(self):
        try:
            self.collection.create_index("file_path")
            self.collection.create_index("file_hash", unique=False)
            print("Created MongoDB indexes")
        except Exception as e:
            print(f"Index creation warning: {e}")
    
    def _get_file_hash(self, file_path: str) -> str:
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        return file_hash
    
    def _chunk_text(self, text: str) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > self.chunk_size // 2:
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append(chunk.strip())
            start = end - self.chunk_overlap
        
        return chunks
    
    async def _create_embedding(self, text: str) -> List[float]:
        try:
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
            print(f"Embedding error: {e}")
            raise
    
    async def _process_file(self, file_path: str) -> Dict[str, Any]:
        file_path_obj = Path(file_path).resolve()
        file_path = str(file_path_obj)
        file_ext = file_path_obj.suffix.lower()
        file_name = file_path_obj.name
        
        print(f"Processing: {file_name}")
        
        file_hash = self._get_file_hash(file_path)
        file_size = os.path.getsize(file_path)
        
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
        
        chunks = self._chunk_text(text)
        print(f"Created {len(chunks)} chunks")
        
        chunk_embeddings = []
        for i, chunk in enumerate(chunks, 1):
            print(f"Creating embedding for chunk {i}/{len(chunks)}")
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
        file_path = processed_file['file_path']
        file_name = processed_file['file_name']
        
        if not replace_existing and self.collection.find_one({"file_path": file_path}):
            print(f"Skipping {file_name} (already exists)")
            return
        
        if replace_existing:
            deleted = self.collection.delete_many({"file_path": file_path}).deleted_count
            if deleted > 0:
                print(f"Replacing existing chunks for {file_name}")
        
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
        
        if documents_to_insert:
            self.collection.insert_many(documents_to_insert)
            print(f"Stored {len(documents_to_insert)} chunks for {file_name}")
    
    @retry_async()
    async def process_file(self, file_path: str, replace_existing: bool = True) -> Dict[str, Any]:
        processed = await self._process_file(file_path)
        await self._store_chunks(processed, replace_existing=replace_existing)
        return processed
    
    async def process_directory(
        self,
        directory: str,
        file_extensions: Optional[List[str]] = None,
        replace_existing: bool = True
    ) -> List[Dict[str, Any]]:
        if file_extensions is None:
            file_extensions = ['.pdf', '.md']
        
        directory_path = Path(directory)
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        files = [
            str(f) for f in directory_path.iterdir()
            if f.is_file() and f.suffix.lower() in file_extensions
        ]
        
        if not files:
            print(f"No supported files found in {directory}")
            return []
        
        print(f"Processing {len(files)} files from {directory}")
        
        results = []
        for file_path in files:
            try:
                results.append(await self.process_file(file_path, replace_existing=replace_existing))
            except Exception as e:
                print(f"Failed to process {file_path}: {e}")
                results.append({'file_path': file_path, 'error': str(e)})
        
        return results
    
    def get_chunks_for_file(self, file_path: str) -> List[Dict[str, Any]]:
        normalized_path = str(Path(file_path).resolve())
        chunks = list(self.collection.find({"file_path": normalized_path}).sort("chunk_index", 1))
        for chunk in chunks:
            chunk['_id'] = str(chunk['_id'])
        return chunks
    
    def delete_embeddings_for_file(self, file_path: str) -> int:
        normalized_path = str(Path(file_path).resolve())
        result = self.collection.delete_many({"file_path": normalized_path})
        deleted_count = result.deleted_count
        if deleted_count > 0:
            print(f"Deleted {deleted_count} chunks for {Path(file_path).name}")
        return deleted_count
    
    def get_processed_files(self) -> Dict[str, Dict[str, Any]]:
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
        if file_extensions is None:
            file_extensions = ['.pdf', '.md']
        
        directory_path = Path(directory)
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        processed_files = self.get_processed_files()
        print(f"Found {len(processed_files)} processed files in database")
        
        directory_abs = directory_path.resolve()
        local_files = {
            str(file_path.resolve()): {'file_name': file_path.name}
            for file_path in directory_abs.iterdir()
            if file_path.is_file() and file_path.suffix.lower() in file_extensions
        }
        
        print(f"Found {len(local_files)} files in directory")
        
        to_insert = []
        to_update = []
        to_delete = []
        
        file_hashes = {}
        for file_path in local_files:
            if file_path not in processed_files:
                to_insert.append(file_path)
            else:
                file_hash = self._get_file_hash(file_path)
                file_hashes[file_path] = file_hash
                if file_hash != processed_files[file_path].get('file_hash'):
                    to_update.append(file_path)
        
        to_delete = [fp for fp in processed_files if fp not in local_files]
        
        print(f"\nSync plan:")
        print(f"  New files: {len(to_insert)}")
        print(f"  Updated files: {len(to_update)}")
        print(f"  Deleted files: {len(to_delete)}")
        
        results = {'inserted': [], 'updated': [], 'deleted': [], 'errors': []}
        
        async def _process_with_error_handling(file_path: str, action: str):
            try:
                return await self.process_file(file_path, replace_existing=True)
            except Exception as e:
                results['errors'].append({'file_path': file_path, 'error': str(e)})
                print(f"Failed to {action} {file_path}: {e}")
                return None
        
        if to_insert:
            print(f"\nProcessing {len(to_insert)} new files...")
            for file_path in to_insert:
                processed = await _process_with_error_handling(file_path, 'process')
                if processed:
                    results['inserted'].append(processed)
        
        if to_update:
            print(f"\nProcessing {len(to_update)} updated files...")
            for file_path in to_update:
                processed = await _process_with_error_handling(file_path, 'update')
                if processed:
                    results['updated'].append(processed)
        
        if to_delete:
            print(f"\nProcessing {len(to_delete)} deleted files...")
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
                    print(f"Failed to delete embeddings for {file_path}: {e}")
        
        print(f"\nSync completed!")
        print(f"  Inserted: {len(results['inserted'])} files")
        print(f"  Updated: {len(results['updated'])} files")
        print(f"  Deleted: {len(results['deleted'])} files")
        if results['errors']:
            print(f"  Errors: {len(results['errors'])} files")
        
        return results
    
    def close(self):
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

