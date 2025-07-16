#!/usr/bin/env python3
"""
Anthropic Claude provider implementation for AI-powered file validation
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    AsyncAnthropic = None

from .base import (
    AIProvider,
    FileValidationContext,
    ValidationResult,
    ValidationStatus,
    ProviderConfig,
    ValidationError
)

logger = logging.getLogger(__name__)


class ClaudeProvider(AIProvider):
    """Anthropic Claude provider for file validation"""
    
    # Approximate pricing per 1K tokens (Claude 3 Opus)
    PRICE_PER_1K_INPUT_TOKENS = 0.015
    PRICE_PER_1K_OUTPUT_TOKENS = 0.075
    
    # Model pricing tiers
    MODEL_PRICING = {
        "claude-3-opus-20240229": {
            "input": 0.015,
            "output": 0.075
        },
        "claude-3-sonnet-20240229": {
            "input": 0.003,
            "output": 0.015
        },
        "claude-instant-1.2": {
            "input": 0.00163,
            "output": 0.00551
        }
    }
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")
        
        # Initialize Anthropic client
        api_key = config.resolve_api_key()
        if not api_key:
            raise ValueError("Claude API key not provided")
        
        self.client = AsyncAnthropic(
            api_key=api_key,
            timeout=config.timeout,
            max_retries=config.max_retries
        )
        
        # Set default model if not specified
        if not self.config.model:
            self.config.model = "claude-3-opus-20240229"
        
        # Get pricing for the model
        self.pricing = self.MODEL_PRICING.get(
            self.config.model,
            {"input": self.PRICE_PER_1K_INPUT_TOKENS, "output": self.PRICE_PER_1K_OUTPUT_TOKENS}
        )
        
        logger.info(f"Initialized Claude provider with model: {self.config.model}")
    
    async def validate_file_deletion(self, context: FileValidationContext) -> ValidationResult:
        """
        Validate if a file is safe to delete using Claude
        
        Args:
            context: File validation context
            
        Returns:
            ValidationResult with status and reasoning
        """
        start_time = datetime.now()
        
        try:
            # Build the prompt
            prompt = self._build_validation_prompt(context)
            
            # Make API call
            response = await self._call_claude_api(prompt)
            
            # Parse response
            result = self._parse_response(response, context)
            
            # Add timing
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            result.response_time_ms = response_time_ms
            
            # Track usage
            if hasattr(response, 'usage'):
                total_tokens = response.usage.input_tokens + response.usage.output_tokens
                # Calculate cost
                cost = (response.usage.input_tokens * self.pricing['input'] / 1000 + 
                       response.usage.output_tokens * self.pricing['output'] / 1000)
                self.track_usage(total_tokens, cost)
            
            logger.info(f"Claude validation completed for {context.file_path}: {result.status.value}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}")
            raise ValidationError(
                "Invalid response format from Claude",
                retryable=True,
                provider=self.name
            )
        except asyncio.TimeoutError:
            logger.error(f"Claude request timed out after {self.config.timeout}s")
            raise ValidationError(
                f"Claude request timeout after {self.config.timeout}s",
                retryable=True,
                provider=self.name
            )
        except Exception as e:
            logger.error(f"Claude validation error: {e}")
            self.track_error()
            # Check if it's a rate limit or temporary error
            error_str = str(e).lower()
            retryable = any(term in error_str for term in ['rate limit', 'timeout', 'temporary', 'overloaded'])
            raise ValidationError(
                str(e),
                retryable=retryable,
                provider=self.name
            )
    
    async def check_health(self) -> bool:
        """
        Check if Claude API is accessible
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try a simple message
            response = await self.client.messages.create(
                model=self.config.model,
                max_tokens=10,
                messages=[
                    {"role": "user", "content": "Respond with 'OK' if operational"}
                ]
            )
            return len(response.content) > 0
        except Exception as e:
            logger.error(f"Claude health check failed: {e}")
            return False
    
    def _build_validation_prompt(self, context: FileValidationContext) -> str:
        """Build prompt for Claude"""
        # Claude doesn't have a separate system prompt, so we include instructions in the user message
        system_instructions = """You are an expert code analyst tasked with determining if files can be safely deleted from a codebase without causing issues.

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
            system_instructions += f"\n\nFile type specific considerations:\n{file_type_hints}"
        
        # Build the full prompt
        prompt = f"""{system_instructions}

Now analyze this file for safe deletion:

{context.to_prompt_context()}

Is this file safe to delete without breaking the codebase? Respond with the JSON format specified above."""
        
        return prompt
    
    def _get_file_type_hints(self, file_type: str) -> str:
        """Get file type specific analysis hints"""
        hints = {
            "test": "Check if this test file contains shared fixtures, utilities, or base classes that other tests depend on.",
            "config": "Configuration files often have environment-specific settings. Check if removing this would break deployments.",
            "migration": "Database migrations should almost never be deleted as they maintain schema history.",
            "interface": "Interface/contract files have high impact. Verify all implementations before considering deletion.",
            "build": "Build configuration files (Makefile, CMakeLists.txt, etc.) are critical for compilation.",
            "ci": "CI/CD configuration files (.github/workflows, .gitlab-ci.yml) are needed for automation.",
            "proto": "Protocol buffer files define data contracts. Check all services using these definitions.",
            "schema": "Schema files (GraphQL, OpenAPI, etc.) define API contracts that clients depend on."
        }
        
        # Check file type categories
        for category, hint in hints.items():
            if category in file_type.lower():
                return hint
        
        return ""
    
    async def _call_claude_api(self, prompt: str) -> Any:
        """Make the actual API call to Claude"""
        # Claude uses a messages format
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # Call Claude API
        response = await self.client.messages.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        
        return response
    
    def _parse_response(self, response: Any, context: FileValidationContext) -> ValidationResult:
        """Parse Claude response into ValidationResult"""
        try:
            # Extract content from response
            if not response.content:
                raise ValidationError("Empty response from Claude", retryable=True, provider=self.name)
            
            # Claude returns content as a list of content blocks
            content = response.content[0].text if response.content else ""
            
            # Parse JSON response
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
            
            # Calculate total tokens
            total_tokens = 0
            if hasattr(response, 'usage'):
                total_tokens = response.usage.input_tokens + response.usage.output_tokens
            
            return ValidationResult(
                status=status,
                confidence=confidence,
                reasons=reasons,
                warnings=warnings,
                provider_name=self.name,
                model_name=self.config.model,
                tokens_used=total_tokens,
                raw_response=content
            )
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing Claude response: {e}, Response: {response}")
            raise ValidationError(
                f"Invalid response format from Claude: {e}",
                retryable=True,
                provider=self.name
            )