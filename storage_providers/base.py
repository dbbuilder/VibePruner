#!/usr/bin/env python3
"""
Base storage provider interface for cloud-agnostic storage
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import os


@dataclass
class StorageConfig:
    """Configuration for storage providers"""
    storage_type: str  # 's3', 'azure', 'gcs', 'local'
    endpoint: Optional[str] = None
    bucket: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    region: Optional[str] = None
    path_prefix: str = "vibepruner"
    
    @classmethod
    def from_env(cls) -> 'StorageConfig':
        """Create config from environment variables"""
        return cls(
            storage_type=os.getenv('STORAGE_TYPE', 'local'),
            endpoint=os.getenv('STORAGE_ENDPOINT'),
            bucket=os.getenv('STORAGE_BUCKET', 'vibepruner'),
            access_key=os.getenv('STORAGE_ACCESS_KEY'),
            secret_key=os.getenv('STORAGE_SECRET_KEY'),
            region=os.getenv('STORAGE_REGION', 'us-east-1'),
            path_prefix=os.getenv('STORAGE_PATH_PREFIX', 'vibepruner')
        )


class StorageProvider(ABC):
    """Abstract base class for storage providers"""
    
    def __init__(self, config: StorageConfig):
        self.config = config
    
    @abstractmethod
    async def upload_file(self, key: str, content: bytes, metadata: Optional[Dict[str, str]] = None) -> str:
        """
        Upload a file to storage
        
        Args:
            key: Storage key/path for the file
            content: File content as bytes
            metadata: Optional metadata to store with file
            
        Returns:
            URL or identifier for the uploaded file
        """
        pass
    
    @abstractmethod
    async def download_file(self, key: str) -> bytes:
        """
        Download a file from storage
        
        Args:
            key: Storage key/path for the file
            
        Returns:
            File content as bytes
        """
        pass
    
    @abstractmethod
    async def delete_file(self, key: str) -> bool:
        """
        Delete a file from storage
        
        Args:
            key: Storage key/path for the file
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def list_files(self, prefix: str = "", limit: int = 1000) -> List[str]:
        """
        List files in storage
        
        Args:
            prefix: Filter files by prefix
            limit: Maximum number of files to return
            
        Returns:
            List of file keys
        """
        pass
    
    @abstractmethod
    async def file_exists(self, key: str) -> bool:
        """
        Check if a file exists
        
        Args:
            key: Storage key/path for the file
            
        Returns:
            True if exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_file_metadata(self, key: str) -> Dict[str, Any]:
        """
        Get metadata for a file
        
        Args:
            key: Storage key/path for the file
            
        Returns:
            Metadata dictionary
        """
        pass
    
    def get_full_key(self, key: str) -> str:
        """Get full key with prefix"""
        if self.config.path_prefix:
            return f"{self.config.path_prefix}/{key}"
        return key
    
    @abstractmethod
    async def create_bucket_if_needed(self) -> bool:
        """
        Create storage bucket/container if it doesn't exist
        
        Returns:
            True if created, False if already existed
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if storage is accessible
        
        Returns:
            True if healthy, False otherwise
        """
        pass