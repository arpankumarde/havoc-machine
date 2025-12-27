#!/usr/bin/env python3

import os
import sys
import asyncio
import pickle
from pathlib import Path
from typing import Optional, Dict, List
from functools import wraps
import time
from concurrent.futures import ThreadPoolExecutor

import json
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/drive']
GCP_AUTH = os.getenv("GCP_AUTH", "client.json")
POLL_INTERVAL = 5
STATE_FILE = ".drive_state.pkl"
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
SUPPORTED_EXTENSIONS = {'.pdf', '.md'}
MIME_TYPES = {'application/pdf': '.pdf', 'text/markdown': '.md', 'text/x-markdown': '.md'}
MAX_CONCURRENT = 5
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
                except (HttpError, Exception) as e:
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


class DriveWatcher:
    def __init__(self, folder_id: str, auth_file: str = GCP_AUTH, download_dir: str = DOWNLOAD_DIR):
        self.folder_id = folder_id
        self.auth_file = auth_file
        self.download_dir = download_dir
        self.service = None
        self.page_token: Optional[str] = None
        self.known_files: Dict[str, Dict] = {}
        self.local_files: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
        self._api_lock = asyncio.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._file_executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT)
        os.makedirs(self.download_dir, exist_ok=True)
        self._authenticate()
        self._load_state()
    
    def _authenticate(self):
        if not os.path.exists(self.auth_file):
            raise FileNotFoundError(f"Auth file not found: {self.auth_file}")
        
        with open(self.auth_file, 'r') as f:
            auth_data = json.load(f)
        
        if auth_data.get('type') == 'service_account':
            creds = service_account.Credentials.from_service_account_file(self.auth_file, scopes=SCOPES)
        else:
            raise ValueError(f"Unsupported auth type. Expected service_account, got: {auth_data.get('type')}")
        
        self.service = build('drive', 'v3', credentials=creds)
    
    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'rb') as f:
                    state = pickle.load(f)
                    self.page_token = state.get('page_token')
                    self.known_files = state.get('known_files', {})
                    self.local_files = state.get('local_files', {})
            except:
                pass
    
    async def _save_state(self):
        async with self._lock:
            try:
                await asyncio.to_thread(self._save_state_sync)
            except Exception as e:
                print(f"Save state error: {e}")
    
    def _save_state_sync(self):
        try:
            with open(STATE_FILE, 'wb') as f:
                pickle.dump({
                    'page_token': self.page_token,
                    'known_files': self.known_files,
                    'local_files': self.local_files
                }, f)
        except Exception as e:
            print(f"Save state error: {e}")
    
    def _is_supported(self, file_data: Dict) -> bool:
        mime = file_data.get('mimeType', '')
        if mime == 'application/vnd.google-apps.folder':
            return False
        name = file_data.get('name', '')
        if name and Path(name).suffix.lower() in SUPPORTED_EXTENSIONS:
            return True
        return mime in MIME_TYPES
    
    async def _run_api_call(self, func, *args):
        async with self._api_lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._executor, func, *args)
    
    async def _run_file_io(self, func, *args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._file_executor, func, *args)
    
    @retry_async()
    async def _download(self, file_id: str, file_name: str):
        file_path = os.path.join(self.download_dir, file_name)
        try:
            def _download_sync():
                request = self.service.files().get_media(fileId=file_id)
                with open(file_path, 'wb') as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()
                return os.path.getmtime(file_path)
            
            mtime = await self._run_api_call(_download_sync)
            
            async with self._lock:
                self.local_files[file_name] = {'file_id': file_id, 'mtime': mtime}
            
            print(f"Downloaded: {file_name}")
        except HttpError as e:
            print(f"Download error: {file_name} - {e}")
            raise
        except Exception as e:
            print(f"Download error: {file_name} - {e}")
            raise
    
    async def _delete_local(self, file_name: str):
        file_path = os.path.join(self.download_dir, file_name)
        if os.path.exists(file_path):
            try:
                await self._run_file_io(os.remove, file_path)
                async with self._lock:
                    if file_name in self.local_files:
                        del self.local_files[file_name]
                print(f"Deleted local: {file_name}")
            except Exception as e:
                print(f"Delete error: {file_name} - {e}")
    
    @retry_async()
    async def _upload(self, file_path: str, file_name: str):
        mime_type = 'application/pdf' if file_name.endswith('.pdf') else 'text/markdown'
        try:
            def _upload_sync():
                file_metadata = {'name': file_name, 'parents': [self.folder_id]}
                media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
                return self.service.files().create(
                    body=file_metadata, media_body=media, fields='id, name, modifiedTime'
                ).execute()
            
            file = await self._run_api_call(_upload_sync)
            mtime = await self._run_file_io(os.path.getmtime, file_path)
            
            async with self._lock:
                self.local_files[file_name] = {'file_id': file['id'], 'mtime': mtime}
                self.known_files[file['id']] = {'name': file_name, 'modifiedTime': file.get('modifiedTime')}
            
            print(f"Uploaded: {file_name}")
            return file['id']
        except HttpError as e:
            print(f"Upload error: {file_name} - {e}")
            raise
        except Exception as e:
            print(f"Upload error: {file_name} - {e}")
            raise
    
    @retry_async()
    async def _update_drive(self, file_id: str, file_path: str, file_name: str):
        mime_type = 'application/pdf' if file_name.endswith('.pdf') else 'text/markdown'
        try:
            def _update_sync():
                media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
                return self.service.files().update(
                    fileId=file_id, media_body=media, fields='id, name, modifiedTime'
                ).execute()
            
            file = await self._run_api_call(_update_sync)
            mtime = await self._run_file_io(os.path.getmtime, file_path)
            
            async with self._lock:
                self.local_files[file_name] = {'file_id': file_id, 'mtime': mtime}
                self.known_files[file_id] = {'name': file_name, 'modifiedTime': file.get('modifiedTime')}
            
            print(f"Updated Drive: {file_name}")
        except HttpError as e:
            print(f"Update error: {file_name} - {e}")
            raise
        except Exception as e:
            print(f"Update error: {file_name} - {e}")
            raise
    
    async def _check_changes(self):
        try:
            def _get_changes():
                params = {'pageSize': 1000, 'fields': 'nextPageToken, changes(fileId, removed, file(id, name, mimeType, modifiedTime, parents))'}
                if self.page_token:
                    params['pageToken'] = self.page_token
                return self.service.changes().list(**params).execute()
            
            changes = await self._run_api_call(_get_changes)
            change_list = changes.get('changes', [])
            new_token = changes.get('newStartPageToken')
            
            if not change_list and not new_token:
                return
            
            tasks = []
            for change in change_list:
                if change.get('removed'):
                    file_id = change.get('fileId')
                    async with self._lock:
                        if file_id in self.known_files:
                            file_name = self.known_files[file_id].get('name')
                            print(f"Deleted from Drive: {file_name}")
                            del self.known_files[file_id]
                            tasks.append(self._delete_local(file_name))
                    continue
                
                file_data = change.get('file')
                if not file_data or self.folder_id not in file_data.get('parents', []) or not self._is_supported(file_data):
                    continue
                
                file_id = file_data['id']
                file_name = file_data.get('name', 'Unknown')
                file_path = os.path.join(self.download_dir, file_name)
                
                async with self._lock:
                    if file_id in self.known_files:
                        old_mtime = self.known_files[file_id].get('modifiedTime')
                        new_mtime = file_data.get('modifiedTime')
                        if old_mtime != new_mtime:
                            file_exists = await self._run_file_io(os.path.exists, file_path)
                            if file_name in self.local_files and file_exists:
                                local_mtime = await self._run_file_io(os.path.getmtime, file_path)
                                local_stored_mtime = self.local_files[file_name].get('mtime', 0)
                                if local_mtime > local_stored_mtime:
                                    print(f"Conflict: {file_name} (Drive wins, overwriting local)")
                                else:
                                    print(f"Updated on Drive: {file_name}")
                            else:
                                print(f"Updated on Drive: {file_name}")
                            tasks.append(self._download(file_id, file_name))
                            self.known_files[file_id] = file_data
                    else:
                        print(f"New on Drive: {file_name}")
                        tasks.append(self._download(file_id, file_name))
                        self.known_files[file_id] = file_data
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        print(f"Task error: {result}")
            
            if new_token:
                async with self._lock:
                    self.page_token = new_token
                await self._save_state()
        except Exception as e:
            print(f"Error checking changes: {e}")
    
    async def initialize(self):
        print(f"Initializing folder: {self.folder_id}")
        page_token = None
        download_tasks = []
        
        while True:
            try:
                def _list_files():
                    return self.service.files().list(
                        q=f"'{self.folder_id}' in parents and trashed=false",
                        fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                        pageToken=page_token
                    ).execute()
                
                results = await self._run_api_call(_list_files)
                
                for item in results.get('files', []):
                    if self._is_supported(item):
                        self.known_files[item['id']] = item
                        file_name = item.get('name')
                        file_path = os.path.join(self.download_dir, file_name)
                        if os.path.exists(file_path):
                            mtime = await self._run_file_io(os.path.getmtime, file_path)
                            self.local_files[file_name] = {'file_id': item['id'], 'mtime': mtime}
                        else:
                            print(f"Downloading missing: {file_name}")
                            download_tasks.append(self._download(item['id'], file_name))
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            except HttpError as e:
                print(f"Error: {e}")
                break
        
        if download_tasks:
            await asyncio.gather(*download_tasks, return_exceptions=True)
        
        try:
            def _get_start_token():
                return self.service.changes().getStartPageToken().execute().get('startPageToken')
            
            self.page_token = await self._run_api_call(_get_start_token)
            await self._save_state()
        except:
            pass
        print(f"Found {len(self.known_files)} files on Drive, {len(self.local_files)} local files")
    
    async def _check_local_changes(self):
        try:
            file_list = await self._run_file_io(os.listdir, self.download_dir)
            tasks = []
            
            for file_name in file_list:
                if not any(file_name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                    continue
                
                file_path = os.path.join(self.download_dir, file_name)
                is_file = await self._run_file_io(os.path.isfile, file_path)
                if not is_file:
                    continue
                
                mtime = await self._run_file_io(os.path.getmtime, file_path)
                
                async with self._lock:
                    if file_name in self.local_files:
                        stored_mtime = self.local_files[file_name].get('mtime', 0)
                        file_id = self.local_files[file_name].get('file_id')
                        
                        if mtime > stored_mtime:
                            if file_id and file_id in self.known_files:
                                print(f"Uploading update: {file_name}")
                                tasks.append(self._update_drive(file_id, file_path, file_name))
                            else:
                                print(f"Uploading new: {file_name}")
                                tasks.append(self._upload(file_path, file_name))
                    else:
                        print(f"Uploading new local file: {file_name}")
                        tasks.append(self._upload(file_path, file_name))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        print(f"Upload task error: {result}")
                await self._save_state()
            
            deleted_files = []
            async with self._lock:
                for file_name in list(self.local_files.keys()):
                    file_path = os.path.join(self.download_dir, file_name)
                    file_exists = await self._run_file_io(os.path.exists, file_path)
                    if not file_exists:
                        deleted_files.append((file_name, self.local_files[file_name].get('file_id')))
            
            delete_tasks = []
            for file_name, file_id in deleted_files:
                if file_id and file_id in self.known_files:
                    print(f"Deleting from Drive: {file_name}")
                    delete_tasks.append(self._delete_from_drive(file_id, file_name))
            
            if delete_tasks:
                results = await asyncio.gather(*delete_tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        print(f"Delete task error: {result}")
                await self._save_state()
        except Exception as e:
            print(f"Error checking local changes: {e}")
    
    @retry_async()
    async def _delete_from_drive(self, file_id: str, file_name: str):
        try:
            def _delete_sync():
                self.service.files().delete(fileId=file_id).execute()
            
            await self._run_api_call(_delete_sync)
            
            async with self._lock:
                if file_id in self.known_files:
                    del self.known_files[file_id]
                if file_name in self.local_files:
                    del self.local_files[file_name]
            
            print(f"Deleted from Drive: {file_name}")
        except HttpError as e:
            print(f"Delete from Drive error: {file_name} - {e}")
            raise
    
    async def watch(self):
        print(f"Watching (every {POLL_INTERVAL}s)...")
        try:
            while True:
                await asyncio.gather(
                    self._check_changes(),
                    self._check_local_changes(),
                    return_exceptions=True
                )
                await asyncio.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\nStopped")
            await self._save_state()


async def main_async():
    folder_id = os.getenv("WATCH_FOLDER_ID") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not folder_id:
        print("Usage: python drive_watcher.py <FOLDER_ID>")
        print("   or: Set WATCH_FOLDER_ID in .env file")
        sys.exit(1)
    
    watcher = DriveWatcher(folder_id, os.getenv("GCP_AUTH", GCP_AUTH))
    await watcher.initialize()
    await watcher.watch()


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
