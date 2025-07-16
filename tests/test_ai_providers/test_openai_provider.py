#!/usr/bin/env python3
"""
Tests for OpenAI provider implementation
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from ai_providers.base import (
    FileValidationContext,
    ValidationResult,
    ValidationStatus,
    ProviderConfig,
    ValidationError
)
from ai_providers.openai_provider import OpenAIProvider


class TestOpenAIProvider:
    """Test the OpenAI provider implementation"""
    
    @pytest.fixture
    def provider_config(self):
        """Create test configuration"""
        return ProviderConfig(
            name="openai",
            api_key="test-key",
            model="gpt-4-turbo-preview",
            max_tokens=4000,
            temperature=0.2,
            timeout=30
        )
    
    @pytest.fixture
    def test_context(self):
        """Create test file context"""
        return FileValidationContext(
            file_path="/test/helper.py",
            file_content="def unused_helper():\n    pass",
            file_type="python",
            file_size=30,
            dependencies=[],
            dependents=[]
        )
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client"""
        with patch('ai_providers.openai_provider.AsyncOpenAI') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_provider_initialization(self, provider_config):
        """Test provider initialization"""
        with patch('ai_providers.openai_provider.AsyncOpenAI'):
            provider = OpenAIProvider(provider_config)
            
            assert provider.name == "openai"
            assert provider.config.model == "gpt-4-turbo-preview"
            assert provider.config.temperature == 0.2
    
    @pytest.mark.asyncio
    async def test_successful_validation_safe_file(self, provider_config, test_context, mock_openai_client):
        """Test successful validation of a safe file"""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps({
                "status": "SAFE",
                "confidence": 0.95,
                "reasons": ["No dependencies found", "Appears to be unused helper"],
                "warnings": []
            })))
        ]
        mock_response.usage = Mock(total_tokens=150)
        
        mock_client = mock_openai_client.return_value
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        provider = OpenAIProvider(provider_config)
        result = await provider.validate_file_deletion(test_context)
        
        assert result.status == ValidationStatus.SAFE
        assert result.confidence == 0.95
        assert len(result.reasons) == 2
        assert "No dependencies found" in result.reasons
        assert result.tokens_used == 150
        assert result.provider_name == "openai"
        assert result.model_name == "gpt-4-turbo-preview"
    
    @pytest.mark.asyncio
    async def test_successful_validation_unsafe_file(self, provider_config, test_context, mock_openai_client):
        """Test successful validation of an unsafe file"""
        # Update context to be a critical file
        test_context.file_path = "/test/auth.py"
        test_context.file_content = "class AuthManager:\n    def authenticate(self, user):\n        # Critical auth logic"
        test_context.dependents = ["main.py", "api.py", "admin.py"]
        
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps({
                "status": "UNSAFE",
                "confidence": 0.98,
                "reasons": ["Critical authentication module", "Multiple files depend on this"],
                "warnings": ["Removing this would break authentication"]
            })))
        ]
        mock_response.usage = Mock(total_tokens=200)
        
        mock_client = mock_openai_client.return_value
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        provider = OpenAIProvider(provider_config)
        result = await provider.validate_file_deletion(test_context)
        
        assert result.status == ValidationStatus.UNSAFE
        assert result.confidence == 0.98
        assert "Critical authentication module" in result.reasons
        assert len(result.warnings) == 1
        assert result.tokens_used == 200
    
    @pytest.mark.asyncio
    async def test_validation_with_uncertain_result(self, provider_config, test_context, mock_openai_client):
        """Test validation returning uncertain status"""
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps({
                "status": "UNCERTAIN",
                "confidence": 0.5,
                "reasons": ["Unable to determine usage", "May have dynamic imports"],
                "warnings": ["Requires manual review"]
            })))
        ]
        mock_response.usage = Mock(total_tokens=100)
        
        mock_client = mock_openai_client.return_value
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        provider = OpenAIProvider(provider_config)
        result = await provider.validate_file_deletion(test_context)
        
        assert result.status == ValidationStatus.UNCERTAIN
        assert result.confidence == 0.5
        assert "Unable to determine usage" in result.reasons
    
    @pytest.mark.asyncio
    async def test_malformed_response_handling(self, provider_config, test_context, mock_openai_client):
        """Test handling of malformed JSON response"""
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="This is not JSON"))
        ]
        mock_response.usage = Mock(total_tokens=50)
        
        mock_client = mock_openai_client.return_value
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        provider = OpenAIProvider(provider_config)
        
        with pytest.raises(ValidationError) as exc_info:
            await provider.validate_file_deletion(test_context)
        
        assert "Invalid response format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, provider_config, test_context, mock_openai_client):
        """Test handling of API errors"""
        mock_client = mock_openai_client.return_value
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API rate limit exceeded")
        )
        
        provider = OpenAIProvider(provider_config)
        
        with pytest.raises(ValidationError) as exc_info:
            await provider.validate_file_deletion(test_context)
        
        assert "API rate limit exceeded" in str(exc_info.value)
        assert exc_info.value.retryable is True
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, provider_config, test_context, mock_openai_client):
        """Test timeout handling"""
        async def slow_response():
            await asyncio.sleep(5)  # Longer than timeout
            return Mock()
        
        mock_client = mock_openai_client.return_value
        mock_client.chat.completions.create = slow_response
        
        provider_config.timeout = 0.1  # 100ms timeout
        provider = OpenAIProvider(provider_config)
        
        with pytest.raises(ValidationError) as exc_info:
            await provider.validate_file_deletion(test_context)
        
        assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_prompt_construction(self, provider_config, test_context, mock_openai_client):
        """Test that prompts are constructed correctly"""
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps({
                "status": "SAFE",
                "confidence": 0.9,
                "reasons": ["Test"],
                "warnings": []
            })))
        ]
        mock_response.usage = Mock(total_tokens=100)
        
        mock_client = mock_openai_client.return_value
        create_mock = AsyncMock(return_value=mock_response)
        mock_client.chat.completions.create = create_mock
        
        provider = OpenAIProvider(provider_config)
        await provider.validate_file_deletion(test_context)
        
        # Check the call arguments
        call_args = create_mock.call_args
        messages = call_args.kwargs['messages']
        
        assert len(messages) == 2  # System and user messages
        assert messages[0]['role'] == 'system'
        assert 'expert code analyst' in messages[0]['content']
        assert messages[1]['role'] == 'user'
        assert test_context.file_path in messages[1]['content']
        assert test_context.file_content in messages[1]['content']
    
    @pytest.mark.asyncio
    async def test_cost_tracking(self, provider_config, test_context, mock_openai_client):
        """Test token usage and cost tracking"""
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps({
                "status": "SAFE",
                "confidence": 0.9,
                "reasons": ["Test"],
                "warnings": []
            })))
        ]
        mock_response.usage = Mock(
            prompt_tokens=1000,
            completion_tokens=200,
            total_tokens=1200
        )
        
        mock_client = mock_openai_client.return_value
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        provider = OpenAIProvider(provider_config)
        result = await provider.validate_file_deletion(test_context)
        
        assert result.tokens_used == 1200
        
        # Check internal usage stats
        stats = provider.get_usage_stats()
        assert stats['total_tokens'] == 1200
        assert stats['total_requests'] == 1
    
    @pytest.mark.asyncio
    async def test_health_check(self, provider_config, mock_openai_client):
        """Test health check functionality"""
        # Mock successful models list response
        mock_models = Mock()
        mock_models.data = [Mock(id="gpt-4"), Mock(id="gpt-3.5-turbo")]
        
        mock_client = mock_openai_client.return_value
        mock_client.models.list = AsyncMock(return_value=mock_models)
        
        provider = OpenAIProvider(provider_config)
        is_healthy = await provider.check_health()
        
        assert is_healthy is True
        mock_client.models.list.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, provider_config, mock_openai_client):
        """Test health check when API is down"""
        mock_client = mock_openai_client.return_value
        mock_client.models.list = AsyncMock(side_effect=Exception("Connection error"))
        
        provider = OpenAIProvider(provider_config)
        is_healthy = await provider.check_health()
        
        assert is_healthy is False
    
    def test_resolve_api_key_from_env(self, mock_openai_client):
        """Test resolving API key from environment variable"""
        import os
        os.environ["TEST_OPENAI_KEY"] = "actual-api-key"
        
        config = ProviderConfig(
            name="openai",
            api_key="${TEST_OPENAI_KEY}",
            model="gpt-4"
        )
        
        with patch('ai_providers.openai_provider.AsyncOpenAI') as mock_class:
            provider = OpenAIProvider(config)
            
            # Check that client was initialized with resolved key
            mock_class.assert_called_once()
            call_args = mock_class.call_args
            assert call_args.kwargs['api_key'] == "actual-api-key"
        
        del os.environ["TEST_OPENAI_KEY"]
    
    @pytest.mark.asyncio
    async def test_custom_model_configuration(self, test_context, mock_openai_client):
        """Test using different model configurations"""
        config = ProviderConfig(
            name="openai",
            api_key="test-key",
            model="gpt-3.5-turbo",  # Cheaper model
            max_tokens=2000,
            temperature=0.0  # More deterministic
        )
        
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps({
                "status": "SAFE",
                "confidence": 0.9,
                "reasons": ["Test"],
                "warnings": []
            })))
        ]
        mock_response.usage = Mock(total_tokens=100)
        
        mock_client = mock_openai_client.return_value
        create_mock = AsyncMock(return_value=mock_response)
        mock_client.chat.completions.create = create_mock
        
        provider = OpenAIProvider(config)
        result = await provider.validate_file_deletion(test_context)
        
        # Verify model configuration was used
        call_args = create_mock.call_args
        assert call_args.kwargs['model'] == "gpt-3.5-turbo"
        assert call_args.kwargs['temperature'] == 0.0
        assert call_args.kwargs['max_tokens'] == 2000