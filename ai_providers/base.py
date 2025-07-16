#!/usr/bin/env python3
"""
Base classes and interfaces for AI providers
Provides cloud-agnostic abstraction for multiple AI providers
"""

import os
import hashlib
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Status of file validation"""
    SAFE = "safe"
    UNSAFE = "unsafe"
    UNCERTAIN = "uncertain"
    ERROR = "error"
    SKIPPED = "skipped"
    
    @property
    def safety_priority(self) -> int:
        """Priority for consensus decisions (lower = higher priority)"""
        priorities = {
            ValidationStatus.UNSAFE: 0,    # Highest priority
            ValidationStatus.ERROR: 1,
            ValidationStatus.UNCERTAIN: 2,
            ValidationStatus.SKIPPED: 3,
            ValidationStatus.SAFE: 4       # Lowest priority
        }
        return priorities.get(self, 999)


@dataclass
class FileValidationContext:
    """Context information for file validation"""
    file_path: str
    file_content: str
    file_type: str
    file_size: int = 0
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    related_files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def content_hash(self) -> str:
        """Generate hash of file content for caching"""
        return hashlib.sha256(self.file_content.encode()).hexdigest()
    
    def to_prompt_context(self, max_content_lines: int = 500) -> str:
        """Convert to a string suitable for AI prompts"""
        content_lines = self.file_content.split('\n')
        if len(content_lines) > max_content_lines:
            content_preview = '\n'.join(content_lines[:max_content_lines])
            content_preview += f"\n... ({len(content_lines) - max_content_lines} more lines)"
        else:
            content_preview = self.file_content
        
        prompt = f"""File: {self.file_path}
Type: {self.file_type}
Size: {self.file_size} bytes
Dependencies: {', '.join(self.dependencies) if self.dependencies else 'None'}
Dependents: {', '.join(self.dependents) if self.dependents else 'None'}
Related Files: {', '.join(self.related_files) if self.related_files else 'None'}

Content:
{content_preview}
"""
        return prompt


@dataclass
class ValidationResult:
    """Result of AI validation"""
    status: ValidationStatus
    confidence: float  # 0.0 to 1.0
    reasons: List[str]
    warnings: List[str]
    provider_name: str
    tokens_used: int = 0
    response_time_ms: int = 0
    model_name: Optional[str] = None
    raw_response: Optional[str] = None
    
    @property
    def is_safe(self) -> bool:
        """Check if the file is safe to delete"""
        return self.status == ValidationStatus.SAFE
    
    @property
    def is_unsafe(self) -> bool:
        """Check if the file is unsafe to delete"""
        return self.status == ValidationStatus.UNSAFE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'status': self.status.value,
            'confidence': self.confidence,
            'reasons': self.reasons,
            'warnings': self.warnings,
            'provider_name': self.provider_name,
            'tokens_used': self.tokens_used,
            'response_time_ms': self.response_time_ms,
            'model_name': self.model_name
        }


@dataclass
class ProviderConfig:
    """Configuration for an AI provider"""
    name: str
    api_key: str
    enabled: bool = True
    model: Optional[str] = None
    endpoint: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.2
    timeout: int = 30
    max_retries: int = 3
    rate_limit_per_minute: Optional[int] = None
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ProviderConfig':
        """Create config from dictionary"""
        return cls(**config_dict)
    
    def resolve_api_key(self) -> str:
        """Resolve API key from environment variable if needed"""
        if self.api_key.startswith('${') and self.api_key.endswith('}'):
            env_var = self.api_key[2:-1]
            return os.environ.get(env_var, '')
        return self.api_key


class ValidationError(Exception):
    """Error during validation"""
    def __init__(self, message: str, retryable: bool = True, **kwargs):
        super().__init__(message)
        self.retryable = retryable
        self.context = kwargs
        
        # Add specific attributes from kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self._usage_stats = {
            'total_requests': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'errors': 0
        }
    
    @property
    def name(self) -> str:
        """Get provider name"""
        return self.config.name
    
    @property
    def enabled(self) -> bool:
        """Check if provider is enabled"""
        return self.config.enabled
    
    @abstractmethod
    async def validate_file_deletion(self, context: FileValidationContext) -> ValidationResult:
        """
        Validate if a file is safe to delete
        
        Args:
            context: File validation context
            
        Returns:
            ValidationResult with status and reasoning
        """
        pass
    
    @abstractmethod
    async def check_health(self) -> bool:
        """
        Check if the provider is healthy and accessible
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    async def validate_with_retry(self, context: FileValidationContext) -> ValidationResult:
        """Validate with retry logic"""
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                return await self.validate_file_deletion(context)
            except ValidationError as e:
                last_error = e
                if not e.retryable:
                    raise
                
                if attempt < self.config.max_retries - 1:
                    wait_time = (2 ** attempt) * 1  # Exponential backoff
                    logger.warning(f"{self.name}: Retry {attempt + 1} after {wait_time}s - {str(e)}")
                    await asyncio.sleep(wait_time)
            except Exception as e:
                last_error = ValidationError(str(e), retryable=True)
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        # All retries failed
        raise last_error or ValidationError(f"Failed after {self.config.max_retries} retries")
    
    async def validate_with_timeout(self, context: FileValidationContext) -> ValidationResult:
        """Validate with timeout"""
        try:
            return await asyncio.wait_for(
                self.validate_file_deletion(context),
                timeout=self.config.timeout
            )
        except asyncio.TimeoutError:
            raise ValidationError(
                f"Validation timeout after {self.config.timeout}s",
                retryable=True,
                provider=self.name
            )
    
    def track_usage(self, tokens: int, cost: float = 0.0):
        """Track usage statistics"""
        self._usage_stats['total_requests'] += 1
        self._usage_stats['total_tokens'] += tokens
        self._usage_stats['total_cost'] += cost
    
    def track_error(self):
        """Track error occurrence"""
        self._usage_stats['errors'] += 1
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return self._usage_stats.copy()
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)"""
        # Rough estimate: 1 token ≈ 4 characters
        return len(text) // 4
    
    def build_prompt(self, context: FileValidationContext) -> str:
        """Build prompt for file validation"""
        system_prompt = """You are an expert code analyst tasked with determining if files can be safely deleted from a codebase without causing issues.

Analyze the provided file and consider:
1. Hidden dependencies (reflection, dynamic imports, string references)
2. Build system references (makefiles, project files, scripts)
3. Documentation value
4. Test coverage implications
5. Configuration or deployment references

Respond with a JSON object:
{
  "status": "SAFE" | "UNSAFE" | "UNCERTAIN",
  "confidence": 0.0-1.0,
  "reasons": ["reason1", "reason2"],
  "warnings": ["warning1", "warning2"]
}"""
        
        user_prompt = f"""Analyze this file for safe deletion:

{context.to_prompt_context()}

Is this file safe to delete without breaking the codebase?"""
        
        return system_prompt, user_prompt