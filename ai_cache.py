#!/usr/bin/env python3
"""
Caching system for AI validation responses to minimize API costs
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import asdict
import logging

logger = logging.getLogger(__name__)


class AIResponseCache:
    """Simple file-based cache for AI responses"""
    
    def __init__(self, cache_dir: str = ".vibepruner/ai_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cleanup_old_entries()
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached response if exists and not expired"""
        cache_file = self._get_cache_file(key)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Check expiration
            if time.time() > data.get('expires_at', 0):
                logger.debug(f"Cache expired for key {key}")
                cache_file.unlink()  # Delete expired entry
                return None
            
            logger.debug(f"Cache hit for key {key}")
            return data.get('result')
            
        except Exception as e:
            logger.error(f"Error reading cache for {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """Set cache entry with TTL"""
        cache_file = self._get_cache_file(key)
        
        try:
            # Convert dataclass to dict if needed
            if hasattr(value, '__dataclass_fields__'):
                value_dict = asdict(value)
            elif hasattr(value, 'to_dict'):
                value_dict = value.to_dict()
            else:
                value_dict = value
            
            data = {
                'result': value_dict,
                'expires_at': time.time() + ttl_seconds,
                'created_at': time.time()
            }
            
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Cached result for key {key}")
            
        except Exception as e:
            logger.error(f"Error caching result for {key}: {e}")
    
    def clear(self):
        """Clear all cache entries"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
        logger.info("Cache cleared")
    
    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for key"""
        # Create safe filename from key
        safe_key = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.json"
    
    def _cleanup_old_entries(self):
        """Remove expired cache entries"""
        cleaned = 0
        current_time = time.time()
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                if current_time > data.get('expires_at', 0):
                    cache_file.unlink()
                    cleaned += 1
                    
            except Exception as e:
                logger.error(f"Error cleaning cache file {cache_file}: {e}")
                # Delete corrupted cache files
                cache_file.unlink()
                cleaned += 1
        
        if cleaned > 0:
            logger.info(f"Cleaned {cleaned} expired cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_entries = 0
        total_size = 0
        expired_entries = 0
        current_time = time.time()
        
        for cache_file in self.cache_dir.glob("*.json"):
            total_entries += 1
            total_size += cache_file.stat().st_size
            
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                
                if current_time > data.get('expires_at', 0):
                    expired_entries += 1
                    
            except Exception:
                expired_entries += 1
        
        return {
            'total_entries': total_entries,
            'total_size_bytes': total_size,
            'expired_entries': expired_entries,
            'cache_directory': str(self.cache_dir)
        }