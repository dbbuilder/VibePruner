#!/usr/bin/env python3
"""
OpenAI provider implementation for AI-powered file validation
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    AsyncOpenAI = None

from .base import (
    AIProvider,
    FileValidationContext,
    ValidationResult,
    ValidationStatus,
    ProviderConfig,
    ValidationError
)

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    """OpenAI GPT-4 provider for file validation"""
    
    # Approximate pricing per 1K tokens (GPT-4 Turbo)
    PRICE_PER_1K_INPUT_TOKENS = 0.01
    PRICE_PER_1K_OUTPUT_TOKENS = 0.03
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package not installed. Run: pip install openai")
        
        # Initialize OpenAI client
        api_key = config.resolve_api_key()
        if not api_key:
            raise ValueError("OpenAI API key not provided")
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=config.timeout,
            max_retries=config.max_retries
        )
        
        # Set default model if not specified
        if not self.config.model:
            self.config.model = "gpt-4-turbo-preview"
        
        logger.info(f"Initialized OpenAI provider with model: {self.config.model}")
    
    async def validate_file_deletion(self, context: FileValidationContext) -> ValidationResult:
        """
        Validate if a file is safe to delete using OpenAI
        
        Args:
            context: File validation context
            
        Returns:
            ValidationResult with status and reasoning
        """
        start_time = datetime.now()
        
        try:
            # Build the prompt
            system_prompt, user_prompt = self._build_validation_prompt(context)
            
            # Make API call
            response = await self._call_openai_api(system_prompt, user_prompt)
            
            # Parse response
            result = self._parse_response(response, context)
            
            # Add timing
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            result.response_time_ms = response_time_ms
            
            # Track usage
            if hasattr(response.usage, 'total_tokens'):
                tokens = response.usage.total_tokens
                # Estimate cost
                input_tokens = getattr(response.usage, 'prompt_tokens', 0)
                output_tokens = getattr(response.usage, 'completion_tokens', 0)
                cost = (input_tokens * self.PRICE_PER_1K_INPUT_TOKENS / 1000 + 
                       output_tokens * self.PRICE_PER_1K_OUTPUT_TOKENS / 1000)
                self.track_usage(tokens, cost)
            
            logger.info(f"OpenAI validation completed for {context.file_path}: {result.status.value}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
            raise ValidationError(
                "Invalid response format from OpenAI",
                retryable=True,
                provider=self.name
            )
        except asyncio.TimeoutError:
            logger.error(f"OpenAI request timed out after {self.config.timeout}s")
            raise ValidationError(
                f"OpenAI request timeout after {self.config.timeout}s",
                retryable=True,
                provider=self.name
            )
        except Exception as e:
            logger.error(f"OpenAI validation error: {e}")
            self.track_error()
            # Check if it's a rate limit or temporary error
            error_str = str(e).lower()
            retryable = any(term in error_str for term in ['rate limit', 'timeout', 'temporary'])
            raise ValidationError(
                str(e),
                retryable=retryable,
                provider=self.name
            )
    
    async def check_health(self) -> bool:
        """
        Check if OpenAI API is accessible
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to list available models
            models = await self.client.models.list()
            return len(models.data) > 0
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False
    
    def _build_validation_prompt(self, context: FileValidationContext) -> tuple[str, str]:
        """Build prompts for OpenAI"""
        system_prompt = """You are an expert code analyst tasked with determining if files can be safely deleted from a codebase without causing issues.

Analyze the provided file and consider:
1. Hidden dependencies (reflection, dynamic imports, string references)
2. Build system references (makefiles, project files, scripts)
3. Documentation value
4. Test coverage implications
5. Configuration or deployment references
6. Comments indicating future use or temporary status

Respond with a JSON object:
{
  "status": "SAFE" | "UNSAFE" | "UNCERTAIN",
  "confidence": 0.0-1.0,
  "reasons": ["reason1", "reason2"],
  "warnings": ["warning1", "warning2"]
}

SAFE: File can be deleted without breaking anything
UNSAFE: File is critical and should not be deleted
UNCERTAIN: Not enough information to make a determination"""
        
        # Add file type specific hints
        file_type_hints = self._get_file_type_hints(context.file_type)
        if file_type_hints:
            system_prompt += f"\n\nFile type specific considerations:\n{file_type_hints}"
        
        user_prompt = f"""Analyze this file for safe deletion:

{context.to_prompt_context()}

Is this file safe to delete without breaking the codebase?"""
        
        return system_prompt, user_prompt
    
    def _get_file_type_hints(self, file_type: str) -> str:
        """Get file type specific analysis hints"""
        hints = {
            "test": "Check if this test file contains shared fixtures, utilities, or base classes that other tests depend on.",
            "config": "Configuration files often have environment-specific settings. Check if removing this would break deployments.",
            "migration": "Database migrations should almost never be deleted as they maintain schema history.",
            "interface": "Interface/contract files have high impact. Verify all implementations before considering deletion.",
            "build": "Build configuration files (Makefile, CMakeLists.txt, etc.) are critical for compilation.",
            "ci": "CI/CD configuration files (.github/workflows, .gitlab-ci.yml) are needed for automation."
        }
        
        # Check file type categories
        for category, hint in hints.items():
            if category in file_type.lower():
                return hint
        
        return ""
    
    async def _call_openai_api(self, system_prompt: str, user_prompt: str) -> Any:
        """Make the actual API call to OpenAI"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Call OpenAI API
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            response_format={"type": "json_object"}  # Ensure JSON response
        )
        
        return response
    
    def _parse_response(self, response: Any, context: FileValidationContext) -> ValidationResult:
        """Parse OpenAI response into ValidationResult"""
        try:
            # Extract content from response
            content = response.choices[0].message.content
            parsed = json.loads(content)
            
            # Map status string to enum
            status_map = {
                "SAFE": ValidationStatus.SAFE,
                "UNSAFE": ValidationStatus.UNSAFE,
                "UNCERTAIN": ValidationStatus.UNCERTAIN
            }
            
            status = status_map.get(parsed.get("status", "").upper(), ValidationStatus.UNCERTAIN)
            confidence = float(parsed.get("confidence", 0.5))
            reasons = parsed.get("reasons", [])
            warnings = parsed.get("warnings", [])
            
            # Ensure lists
            if not isinstance(reasons, list):
                reasons = [str(reasons)] if reasons else []
            if not isinstance(warnings, list):
                warnings = [str(warnings)] if warnings else []
            
            return ValidationResult(
                status=status,
                confidence=confidence,
                reasons=reasons,
                warnings=warnings,
                provider_name=self.name,
                model_name=self.config.model,
                tokens_used=getattr(response.usage, 'total_tokens', 0),
                raw_response=content
            )
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing OpenAI response: {e}, Response: {response}")
            raise ValidationError(
                f"Invalid response format from OpenAI: {e}",
                retryable=True,
                provider=self.name
            )