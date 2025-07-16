#!/usr/bin/env python3
"""
Google Gemini provider implementation for AI-powered file validation
"""

import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

from .base import (
    AIProvider,
    FileValidationContext,
    ValidationResult,
    ValidationStatus,
    ProviderConfig,
    ValidationError
)

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    """Google Gemini provider for file validation"""
    
    # Gemini is currently free for basic usage
    # Pricing may change in the future
    PRICE_PER_1K_TOKENS = 0.0  # Free tier
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        
        if not GEMINI_AVAILABLE:
            raise ImportError("Google GenerativeAI package not installed. Run: pip install google-generativeai")
        
        # Initialize Gemini with API key
        api_key = config.resolve_api_key()
        if not api_key:
            raise ValueError("Gemini API key not provided")
        
        genai.configure(api_key=api_key)
        
        # Set default model if not specified
        if not self.config.model:
            self.config.model = "gemini-pro"
        
        # Create generation config
        self.generation_config = genai.GenerationConfig(
            temperature=self.config.temperature,
            max_output_tokens=self.config.max_tokens
        )
        
        # Create model instance
        self.model = genai.GenerativeModel(
            model_name=self.config.model,
            generation_config=self.generation_config
        )
        
        # Safety settings for code analysis (allow all content)
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }
        ]
        
        logger.info(f"Initialized Gemini provider with model: {self.config.model}")
    
    async def validate_file_deletion(self, context: FileValidationContext) -> ValidationResult:
        """
        Validate if a file is safe to delete using Gemini
        
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
            response = await self._call_gemini_api(prompt)
            
            # Parse response
            result = self._parse_response(response, context)
            
            # Add timing
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            result.response_time_ms = response_time_ms
            
            # Track usage (Gemini doesn't provide token counts, so we estimate)
            estimated_tokens = self.estimate_tokens(prompt + response.text)
            self.track_usage(estimated_tokens, 0)  # Free tier
            
            logger.info(f"Gemini validation completed for {context.file_path}: {result.status.value}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            raise ValidationError(
                "Invalid response format from Gemini",
                retryable=True,
                provider=self.name
            )
        except asyncio.TimeoutError:
            logger.error(f"Gemini request timed out after {self.config.timeout}s")
            raise ValidationError(
                f"Gemini request timeout after {self.config.timeout}s",
                retryable=True,
                provider=self.name
            )
        except Exception as e:
            logger.error(f"Gemini validation error: {e}")
            self.track_error()
            # Check if it's a rate limit or temporary error
            error_str = str(e).lower()
            retryable = any(term in error_str for term in ['quota', 'rate', 'timeout', 'temporary', '429', '503'])
            raise ValidationError(
                str(e),
                retryable=retryable,
                provider=self.name
            )
    
    async def check_health(self) -> bool:
        """
        Check if Gemini API is accessible
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try a simple generation
            response = await self.model.generate_content_async(
                "Respond with 'OK' if operational",
                safety_settings=self.safety_settings
            )
            return bool(response.text)
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False
    
    def _build_validation_prompt(self, context: FileValidationContext) -> str:
        """Build prompt for Gemini"""
        # Gemini works best with clear, structured prompts
        prompt = f"""You are an expert code analyst. Analyze the following file to determine if it can be safely deleted from a codebase without causing issues.

File Information:
- Path: {context.file_path}
- Type: {context.file_type}
- Size: {context.file_size} bytes
- Dependencies (imports): {', '.join(context.dependencies) if context.dependencies else 'None'}
- Dependents (files that import this): {', '.join(context.dependents) if context.dependents else 'None'}

File Content:
```
{context.file_content}
```

Consider these factors:
1. Hidden dependencies (reflection, dynamic imports, string references)
2. Build system references (makefiles, project files, scripts)
3. Documentation value
4. Test coverage implications
5. Configuration or deployment references
6. Comments indicating future use or temporary status

{self._get_file_type_hints(context.file_type)}

Respond ONLY with a JSON object in this exact format:
{{
  "status": "SAFE" | "UNSAFE" | "UNCERTAIN",
  "confidence": 0.0-1.0,
  "reasons": ["reason1", "reason2"],
  "warnings": ["warning1", "warning2"]
}}

Where:
- SAFE: File can be deleted without breaking anything
- UNSAFE: File is critical and should not be deleted
- UNCERTAIN: Not enough information to make a determination
- confidence: Your confidence level (0.0 to 1.0)
- reasons: List of reasons for your decision
- warnings: Any warnings or caveats

Analyze the file and respond with ONLY the JSON object."""
        
        return prompt
    
    def _get_file_type_hints(self, file_type: str) -> str:
        """Get file type specific analysis hints"""
        hints = {
            "test": "Pay special attention: Test files often contain shared fixtures, utilities, or base classes that other tests depend on.",
            "config": "Configuration files require extra care: Check if removing this would break environment-specific deployments.",
            "migration": "Database migrations are critical: They should almost never be deleted as they maintain schema history.",
            "interface": "Interface/contract files have high impact: Verify all implementations before considering deletion.",
            "build": "Build files are essential: Files like Makefile, CMakeLists.txt are critical for compilation.",
            "ci": "CI/CD files are important: .github/workflows, .gitlab-ci.yml are needed for automation.",
            "proto": "Protocol buffers define contracts: Check all services using these definitions.",
            "schema": "Schema files define APIs: GraphQL, OpenAPI schemas that clients depend on.",
            "fixture": "Test fixtures are often shared: Other tests may depend on this test data.",
            "mock": "Mock files are test infrastructure: Often used across multiple test files."
        }
        
        # Check file type categories
        for category, hint in hints.items():
            if category in file_type.lower():
                return f"\nSpecial consideration for {category} files:\n{hint}\n"
        
        return ""
    
    async def _call_gemini_api(self, prompt: str) -> Any:
        """Make the actual API call to Gemini"""
        # Use timeout wrapper
        try:
            response = await asyncio.wait_for(
                self.model.generate_content_async(
                    prompt,
                    safety_settings=self.safety_settings
                ),
                timeout=self.config.timeout
            )
            return response
        except asyncio.TimeoutError:
            raise  # Re-raise to be caught by the main handler
    
    def _parse_response(self, response: Any, context: FileValidationContext) -> ValidationResult:
        """Parse Gemini response into ValidationResult"""
        try:
            # Extract text from response
            if not response.text:
                raise ValidationError("Empty response from Gemini", retryable=True, provider=self.name)
            
            # Clean the response text (Gemini sometimes adds markdown formatting)
            text = response.text.strip()
            
            # Remove markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]  # Remove ```json
            if text.startswith("```"):
                text = text[3:]  # Remove ```
            if text.endswith("```"):
                text = text[:-3]  # Remove trailing ```
            
            text = text.strip()
            
            # Parse JSON response
            parsed = json.loads(text)
            
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
            
            # Estimate tokens (Gemini doesn't provide token counts)
            estimated_tokens = self.estimate_tokens(text)
            
            return ValidationResult(
                status=status,
                confidence=confidence,
                reasons=reasons,
                warnings=warnings,
                provider_name=self.name,
                model_name=self.config.model,
                tokens_used=estimated_tokens,
                raw_response=text
            )
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing Gemini response: {e}, Response: {response.text}")
            raise ValidationError(
                f"Invalid response format from Gemini: {e}",
                retryable=True,
                provider=self.name
            )