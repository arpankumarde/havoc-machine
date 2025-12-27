#!/usr/bin/env python3
"""Google Drive watcher for .pdf and .md files using page tokens."""

import os
import sys
import time
import pickle
from pathlib import Path
from typing import Optional, Dict

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


class DriveWatcher:
    def __init__(self, folder_id: str, auth_file: str = GCP_AUTH, download_dir: str = DOWNLOAD_DIR):
        self.folder_id = folder_id
        self.auth_file = auth_file
        self.download_dir = download_dir
        self.service = None
        self.page_token: Optional[str] = None
        self.known_files: Dict[str, Dict] = {}  # file_id -> file metadata
        self.local_files: Dict[str, Dict] = {}  # filename -> {file_id, mtime}
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
    
    def _save_state(self):
        try:
            with open(STATE_FILE, 'wb') as f:
                pickle.dump({
                    'page_token': self.page_token,
                    'known_files': self.known_files,
                    'local_files': self.local_files
                }, f)
        except:
            pass
    
    def _is_supported(self, file_data: Dict) -> bool:
        mime = file_data.get('mimeType', '')
        if mime == 'application/vnd.google-apps.folder':
            return False
        name = file_data.get('name', '')
        if name and Path(name).suffix.lower() in SUPPORTED_EXTENSIONS:
            return True
        return mime in MIME_TYPES
    
    def _download(self, file_id: str, file_name: str):
        file_path = os.path.join(self.download_dir, file_name)
        try:
            with open(file_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, self.service.files().get_media(fileId=file_id))
                done = False
                while not done:
                    _, done = downloader.next_chunk()
            mtime = os.path.getmtime(file_path)
            self.local_files[file_name] = {'file_id': file_id, 'mtime': mtime}
            print(f"✓ Downloaded: {file_name}")
        except HttpError as e:
            print(f"✗ Download error: {file_name} - {e}")
    
    def _delete_local(self, file_name: str):
        file_path = os.path.join(self.download_dir, file_name)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                if file_name in self.local_files:
                    del self.local_files[file_name]
                print(f"🗑️  Deleted local: {file_name}")
            except Exception as e:
                print(f"✗ Delete error: {file_name} - {e}")
    
    def _upload(self, file_path: str, file_name: str):
        mime_type = 'application/pdf' if file_name.endswith('.pdf') else 'text/markdown'
        try:
            file_metadata = {'name': file_name, 'parents': [self.folder_id]}
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id, name, modifiedTime').execute()
            mtime = os.path.getmtime(file_path)
            self.local_files[file_name] = {'file_id': file['id'], 'mtime': mtime}
            self.known_files[file['id']] = {'name': file_name, 'modifiedTime': file.get('modifiedTime')}
            print(f"✓ Uploaded: {file_name}")
            return file['id']
        except HttpError as e:
            print(f"✗ Upload error: {file_name} - {e}")
            return None
    
    def _update_drive(self, file_id: str, file_path: str, file_name: str):
        mime_type = 'application/pdf' if file_name.endswith('.pdf') else 'text/markdown'
        try:
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            file = self.service.files().update(fileId=file_id, media_body=media, fields='id, name, modifiedTime').execute()
            mtime = os.path.getmtime(file_path)
            self.local_files[file_name] = {'file_id': file_id, 'mtime': mtime}
            self.known_files[file_id] = {'name': file_name, 'modifiedTime': file.get('modifiedTime')}
            print(f"✓ Updated Drive: {file_name}")
        except HttpError as e:
            print(f"✗ Update error: {file_name} - {e}")
    
    def _check_changes(self):
        try:
            params = {'pageSize': 1000, 'fields': 'nextPageToken, changes(fileId, removed, file(id, name, mimeType, modifiedTime, parents))'}
            if self.page_token:
                params['pageToken'] = self.page_token
            
            changes = self.service.changes().list(**params).execute()
            change_list = changes.get('changes', [])
            new_token = changes.get('newStartPageToken')
            
            if not change_list and not new_token:
                return
            
            for change in change_list:
                if change.get('removed'):
                    file_id = change.get('fileId')
                    if file_id in self.known_files:
                        file_name = self.known_files[file_id].get('name')
                        print(f"🗑️  Deleted from Drive: {file_name}")
                        self._delete_local(file_name)
                        del self.known_files[file_id]
                    continue
                
                file_data = change.get('file')
                if not file_data or self.folder_id not in file_data.get('parents', []) or not self._is_supported(file_data):
                    continue
                
                file_id = file_data['id']
                file_name = file_data.get('name', 'Unknown')
                file_path = os.path.join(self.download_dir, file_name)
                
                if file_id in self.known_files:
                    old_mtime = self.known_files[file_id].get('modifiedTime')
                    new_mtime = file_data.get('modifiedTime')
                    if old_mtime != new_mtime:
                        # Check if local file was modified
                        if file_name in self.local_files and os.path.exists(file_path):
                            local_mtime = os.path.getmtime(file_path)
                            local_stored_mtime = self.local_files[file_name].get('mtime', 0)
                            if local_mtime > local_stored_mtime:
                                # Conflict: Drive always wins
                                print(f"⚠️  Conflict: {file_name} (Drive wins, overwriting local)")
                            else:
                                print(f"📝 Updated on Drive: {file_name}")
                        else:
                            print(f"📝 Updated on Drive: {file_name}")
                        # Always download from Drive (Drive wins)
                        self._download(file_id, file_name)
                        self.known_files[file_id] = file_data
                else:
                    print(f"✨ New on Drive: {file_name}")
                    self._download(file_id, file_name)
                    self.known_files[file_id] = file_data
            
            if new_token:
                self.page_token = new_token
                self._save_state()
        except HttpError as e:
            print(f"✗ Error: {e}")
    
    def initialize(self):
        print(f"🔍 Initializing folder: {self.folder_id}")
        page_token = None
        while True:
            try:
                results = self.service.files().list(
                    q=f"'{self.folder_id}' in parents and trashed=false",
                    fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                    pageToken=page_token
                ).execute()
                for item in results.get('files', []):
                    if self._is_supported(item):
                        self.known_files[item['id']] = item
                        file_name = item.get('name')
                        file_path = os.path.join(self.download_dir, file_name)
                        if os.path.exists(file_path):
                            mtime = os.path.getmtime(file_path)
                            self.local_files[file_name] = {'file_id': item['id'], 'mtime': mtime}
                        else:
                            # Download missing files
                            print(f"📥 Downloading missing: {file_name}")
                            self._download(item['id'], file_name)
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            except HttpError as e:
                print(f"✗ Error: {e}")
                break
        
        try:
            self.page_token = self.service.changes().getStartPageToken().execute().get('startPageToken')
            self._save_state()
        except:
            pass
        print(f"✓ Found {len(self.known_files)} files on Drive, {len(self.local_files)} local files")
    
    def _check_local_changes(self):
        """Check for local file changes and sync to Drive."""
        for file_name in os.listdir(self.download_dir):
            if not any(file_name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                continue
            
            file_path = os.path.join(self.download_dir, file_name)
            if not os.path.isfile(file_path):
                continue
            
            mtime = os.path.getmtime(file_path)
            
            if file_name in self.local_files:
                stored_mtime = self.local_files[file_name].get('mtime', 0)
                file_id = self.local_files[file_name].get('file_id')
                
                if mtime > stored_mtime:
                    # Local file was modified
                    if file_id and file_id in self.known_files:
                        # File exists on Drive, update it
                        print(f"📤 Uploading update: {file_name}")
                        self._update_drive(file_id, file_path, file_name)
                    else:
                        # New file, upload it
                        print(f"📤 Uploading new: {file_name}")
                        self._upload(file_path, file_name)
                    self._save_state()
            else:
                # New local file
                print(f"📤 Uploading new local file: {file_name}")
                self._upload(file_path, file_name)
                self._save_state()
        
        # Check for deleted local files (files in local_files but not on disk)
        for file_name in list(self.local_files.keys()):
            file_path = os.path.join(self.download_dir, file_name)
            if not os.path.exists(file_path):
                file_id = self.local_files[file_name].get('file_id')
                if file_id and file_id in self.known_files:
                    print(f"🗑️  Deleting from Drive: {file_name}")
                    try:
                        self.service.files().delete(fileId=file_id).execute()
                        del self.known_files[file_id]
                        del self.local_files[file_name]
                        print(f"✓ Deleted from Drive: {file_name}")
                        self._save_state()
                    except HttpError as e:
                        print(f"✗ Delete from Drive error: {file_name} - {e}")
    
    def watch(self):
        print(f"👀 Watching (every {POLL_INTERVAL}s)...")
        try:
            while True:
                self._check_changes()  # Drive -> Local
                self._check_local_changes()  # Local -> Drive
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\n🛑 Stopped")
            self._save_state()


def main():
    folder_id = os.getenv("WATCH_FOLDER_ID") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not folder_id:
        print("Usage: python drive_watcher.py <FOLDER_ID>")
        print("   or: Set WATCH_FOLDER_ID in .env file")
        sys.exit(1)
    
    watcher = DriveWatcher(folder_id, os.getenv("GCP_AUTH", GCP_AUTH))
    watcher.initialize()
    watcher.watch()


if __name__ == "__main__":
    main()
