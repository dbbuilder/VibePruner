"""
Storage providers for cloud-agnostic file storage
"""

from .base import StorageProvider, StorageConfig
from .local import LocalFileStorage
from .s3_compatible import S3CompatibleStorage
from .factory import get_storage_provider

__all__ = [
    'StorageProvider',
    'StorageConfig',
    'LocalFileStorage',
    'S3CompatibleStorage',
    'get_storage_provider'
]