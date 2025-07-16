#!/usr/bin/env python3
"""
Tests for Google Gemini provider implementation
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio

from ai_providers.base import (
    FileValidationContext,
    ValidationResult,
    ValidationStatus,
    ProviderConfig,
    ValidationError
)
from ai_providers.gemini_provider import GeminiProvider


class TestGeminiProvider:
    """Test the Gemini provider implementation"""
    
    @pytest.fixture
    def provider_config(self):
        """Create test configuration"""
        return ProviderConfig(
            name="gemini",
            api_key="test-key",
            model="gemini-pro",
            max_tokens=4000,
            temperature=0.2,
            timeout=30
        )
    
    @pytest.fixture
    def test_context(self):
        """Create test file context"""
        return FileValidationContext(
            file_path="/test/logger.py",
            file_content="import logging\n\ndef setup_logger():\n    pass",
            file_type="python",
            file_size=50,
            dependencies=["logging"],
            dependents=[]
        )
    
    @pytest.fixture
    def mock_genai(self):
        """Mock Google GenerativeAI"""
        with patch('ai_providers.gemini_provider.genai') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_provider_initialization(self, provider_config, mock_genai):
        """Test provider initialization"""
        provider = GeminiProvider(provider_config)
        
        assert provider.name == "gemini"
        assert provider.config.model == "gemini-pro"
        assert provider.config.temperature == 0.2
        
        # Check that API key was configured
        mock_genai.configure.assert_called_once_with(api_key="test-key")
    
    @pytest.mark.asyncio
    async def test_successful_validation_safe_file(self, provider_config, test_context, mock_genai):
        """Test successful validation of a safe file"""
        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = json.dumps({
            "status": "SAFE",
            "confidence": 0.89,
            "reasons": ["Unused logging setup", "No external dependencies"],
            "warnings": []
        })
        
        mock_model = Mock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        
        provider = GeminiProvider(provider_config)
        result = await provider.validate_file_deletion(test_context)
        
        assert result.status == ValidationStatus.SAFE
        assert result.confidence == 0.89
        assert len(result.reasons) == 2
        assert "Unused logging setup" in result.reasons
        assert result.provider_name == "gemini"
        assert result.model_name == "gemini-pro"
    
    @pytest.mark.asyncio
    async def test_successful_validation_unsafe_file(self, provider_config, test_context, mock_genai):
        """Test successful validation of an unsafe file"""
        # Update context to be a critical file
        test_context.file_path = "/test/security.py"
        test_context.file_content = "class SecurityManager:\n    def check_auth(self, token):\n        # Core security"
        test_context.dependents = ["api.py", "middleware.py", "routes.py"]
        
        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = json.dumps({
            "status": "UNSAFE",
            "confidence": 0.97,
            "reasons": ["Core security component", "Multiple critical dependencies"],
            "warnings": ["Essential for authentication"]
        })
        
        mock_model = Mock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        
        provider = GeminiProvider(provider_config)
        result = await provider.validate_file_deletion(test_context)
        
        assert result.status == ValidationStatus.UNSAFE
        assert result.confidence == 0.97
        assert "Core security component" in result.reasons
        assert len(result.warnings) == 1
    
    @pytest.mark.asyncio
    async def test_gemini_prompt_format(self, provider_config, test_context, mock_genai):
        """Test Gemini-specific prompt formatting"""
        mock_response = Mock()
        mock_response.text = json.dumps({
            "status": "SAFE",
            "confidence": 0.9,
            "reasons": ["Test"],
            "warnings": []
        })
        
        mock_model = Mock()
        generate_mock = AsyncMock(return_value=mock_response)
        mock_model.generate_content_async = generate_mock
        mock_genai.GenerativeModel.return_value = mock_model
        
        provider = GeminiProvider(provider_config)
        await provider.validate_file_deletion(test_context)
        
        # Check the prompt content
        call_args = generate_mock.call_args
        prompt = call_args[0][0]  # First positional argument
        
        assert test_context.file_path in prompt
        assert test_context.file_content in prompt
        assert "SAFE" in prompt
        assert "UNSAFE" in prompt
        assert "JSON" in prompt
    
    @pytest.mark.asyncio
    async def test_handle_gemini_api_error(self, provider_config, test_context, mock_genai):
        """Test handling of Gemini API errors"""
        mock_model = Mock()
        mock_model.generate_content_async = AsyncMock(
            side_effect=Exception("Quota exceeded")
        )
        mock_genai.GenerativeModel.return_value = mock_model
        
        provider = GeminiProvider(provider_config)
        
        with pytest.raises(ValidationError) as exc_info:
            await provider.validate_file_deletion(test_context)
        
        assert "Quota exceeded" in str(exc_info.value)
        assert exc_info.value.retryable is True
    
    @pytest.mark.asyncio
    async def test_malformed_response_handling(self, provider_config, test_context, mock_genai):
        """Test handling of malformed responses"""
        mock_response = Mock()
        mock_response.text = "This is not JSON"
        
        mock_model = Mock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        
        provider = GeminiProvider(provider_config)
        
        with pytest.raises(ValidationError) as exc_info:
            await provider.validate_file_deletion(test_context)
        
        assert "Invalid response format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_empty_response_handling(self, provider_config, test_context, mock_genai):
        """Test handling of empty responses"""
        mock_response = Mock()
        mock_response.text = ""
        
        mock_model = Mock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        
        provider = GeminiProvider(provider_config)
        
        with pytest.raises(ValidationError) as exc_info:
            await provider.validate_file_deletion(test_context)
        
        assert "Empty response" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, provider_config, test_context, mock_genai):
        """Test timeout handling"""
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(5)
            return Mock()
        
        mock_model = Mock()
        mock_model.generate_content_async = slow_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        provider_config.timeout = 0.1
        provider = GeminiProvider(provider_config)
        
        with pytest.raises(ValidationError) as exc_info:
            await provider.validate_file_deletion(test_context)
        
        assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_generation_config(self, test_context, mock_genai):
        """Test custom generation configuration"""
        config = ProviderConfig(
            name="gemini",
            api_key="test-key",
            model="gemini-pro",
            max_tokens=2000,
            temperature=0.0
        )
        
        mock_response = Mock()
        mock_response.text = json.dumps({
            "status": "SAFE",
            "confidence": 0.9,
            "reasons": ["Test"],
            "warnings": []
        })
        
        mock_model = Mock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        
        # Capture the GenerativeModel initialization
        mock_genai.GenerativeModel.return_value = mock_model
        
        provider = GeminiProvider(config)
        
        # Check generation config was created properly
        mock_genai.GenerationConfig.assert_called_once_with(
            temperature=0.0,
            max_output_tokens=2000
        )
    
    @pytest.mark.asyncio
    async def test_safety_settings(self, provider_config, test_context, mock_genai):
        """Test that safety settings are configured for code analysis"""
        mock_response = Mock()
        mock_response.text = json.dumps({
            "status": "SAFE",
            "confidence": 0.9,
            "reasons": ["Test"],
            "warnings": []
        })
        
        mock_model = Mock()
        generate_mock = AsyncMock(return_value=mock_response)
        mock_model.generate_content_async = generate_mock
        mock_genai.GenerativeModel.return_value = mock_model
        
        provider = GeminiProvider(provider_config)
        await provider.validate_file_deletion(test_context)
        
        # Check that safety settings were passed
        call_args = generate_mock.call_args
        assert 'safety_settings' in call_args.kwargs
    
    @pytest.mark.asyncio
    async def test_cost_tracking(self, provider_config, test_context, mock_genai):
        """Test token estimation and cost tracking for Gemini"""
        mock_response = Mock()
        mock_response.text = json.dumps({
            "status": "SAFE",
            "confidence": 0.9,
            "reasons": ["Test"],
            "warnings": []
        })
        
        mock_model = Mock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        
        provider = GeminiProvider(provider_config)
        result = await provider.validate_file_deletion(test_context)
        
        # Gemini doesn't provide token counts, so we estimate
        assert result.tokens_used > 0  # Should have estimated tokens
        
        # Check internal usage stats
        stats = provider.get_usage_stats()
        assert stats['total_tokens'] > 0
        assert stats['total_requests'] == 1
    
    @pytest.mark.asyncio
    async def test_health_check(self, provider_config, mock_genai):
        """Test health check functionality"""
        # Mock successful generation
        mock_response = Mock()
        mock_response.text = "OK"
        
        mock_model = Mock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        
        provider = GeminiProvider(provider_config)
        is_healthy = await provider.check_health()
        
        assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, provider_config, mock_genai):
        """Test health check when API is down"""
        mock_model = Mock()
        mock_model.generate_content_async = AsyncMock(side_effect=Exception("Service unavailable"))
        mock_genai.GenerativeModel.return_value = mock_model
        
        provider = GeminiProvider(provider_config)
        is_healthy = await provider.check_health()
        
        assert is_healthy is False
    
    def test_resolve_api_key_from_env(self, mock_genai):
        """Test resolving API key from environment variable"""
        import os
        os.environ["TEST_GEMINI_KEY"] = "actual-gemini-key"
        
        config = ProviderConfig(
            name="gemini",
            api_key="${TEST_GEMINI_KEY}",
            model="gemini-pro"
        )
        
        provider = GeminiProvider(config)
        
        # Check that genai was configured with resolved key
        mock_genai.configure.assert_called_with(api_key="actual-gemini-key")
        
        del os.environ["TEST_GEMINI_KEY"]
    
    @pytest.mark.asyncio
    async def test_batch_processing_optimization(self, provider_config, mock_genai):
        """Test that Gemini provider can handle batch requests efficiently"""
        contexts = [
            FileValidationContext(
                file_path=f"/test/file{i}.py",
                file_content=f"content {i}",
                file_type="python"
            )
            for i in range(3)
        ]
        
        mock_response = Mock()
        mock_response.text = json.dumps({
            "status": "SAFE",
            "confidence": 0.9,
            "reasons": ["Test"],
            "warnings": []
        })
        
        mock_model = Mock()
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        
        provider = GeminiProvider(provider_config)
        
        # Process multiple files
        results = []
        for context in contexts:
            result = await provider.validate_file_deletion(context)
            results.append(result)
        
        assert len(results) == 3
        assert all(r.status == ValidationStatus.SAFE for r in results)