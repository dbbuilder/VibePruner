#!/usr/bin/env python3
"""
Tests for Claude (Anthropic) provider implementation
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
from ai_providers.claude_provider import ClaudeProvider


class TestClaudeProvider:
    """Test the Claude provider implementation"""
    
    @pytest.fixture
    def provider_config(self):
        """Create test configuration"""
        return ProviderConfig(
            name="claude",
            api_key="test-key",
            model="claude-3-opus-20240229",
            max_tokens=4000,
            temperature=0.2,
            timeout=30
        )
    
    @pytest.fixture
    def test_context(self):
        """Create test file context"""
        return FileValidationContext(
            file_path="/test/utils.py",
            file_content="def format_date(date):\n    return date.strftime('%Y-%m-%d')",
            file_type="python",
            file_size=60,
            dependencies=["datetime"],
            dependents=[]
        )
    
    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock Anthropic client"""
        with patch('ai_providers.claude_provider.AsyncAnthropic') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_provider_initialization(self, provider_config):
        """Test provider initialization"""
        with patch('ai_providers.claude_provider.AsyncAnthropic'):
            provider = ClaudeProvider(provider_config)
            
            assert provider.name == "claude"
            assert provider.config.model == "claude-3-opus-20240229"
            assert provider.config.temperature == 0.2
    
    @pytest.mark.asyncio
    async def test_successful_validation_safe_file(self, provider_config, test_context, mock_anthropic_client):
        """Test successful validation of a safe file"""
        # Mock Claude response
        mock_response = Mock()
        mock_response.content = [
            Mock(text=json.dumps({
                "status": "SAFE",
                "confidence": 0.92,
                "reasons": ["Utility function with no dependencies", "Not referenced by other files"],
                "warnings": []
            }))
        ]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        
        mock_client = mock_anthropic_client.return_value
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        
        provider = ClaudeProvider(provider_config)
        result = await provider.validate_file_deletion(test_context)
        
        assert result.status == ValidationStatus.SAFE
        assert result.confidence == 0.92
        assert len(result.reasons) == 2
        assert "Utility function" in result.reasons[0]
        assert result.tokens_used == 150
        assert result.provider_name == "claude"
        assert result.model_name == "claude-3-opus-20240229"
    
    @pytest.mark.asyncio
    async def test_successful_validation_unsafe_file(self, provider_config, test_context, mock_anthropic_client):
        """Test successful validation of an unsafe file"""
        # Update context to be a critical file
        test_context.file_path = "/test/database.py"
        test_context.file_content = "class DatabaseConnection:\n    def __init__(self):\n        self.connection = None"
        test_context.dependents = ["models.py", "api.py", "services.py"]
        
        # Mock Claude response
        mock_response = Mock()
        mock_response.content = [
            Mock(text=json.dumps({
                "status": "UNSAFE",
                "confidence": 0.96,
                "reasons": ["Core database infrastructure", "Multiple critical files depend on this"],
                "warnings": ["Removing would break data access layer"]
            }))
        ]
        mock_response.usage = Mock(input_tokens=150, output_tokens=60)
        
        mock_client = mock_anthropic_client.return_value
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        
        provider = ClaudeProvider(provider_config)
        result = await provider.validate_file_deletion(test_context)
        
        assert result.status == ValidationStatus.UNSAFE
        assert result.confidence == 0.96
        assert "Core database infrastructure" in result.reasons
        assert len(result.warnings) == 1
        assert result.tokens_used == 210
    
    @pytest.mark.asyncio
    async def test_claude_specific_prompt_format(self, provider_config, test_context, mock_anthropic_client):
        """Test Claude-specific prompt formatting"""
        mock_response = Mock()
        mock_response.content = [
            Mock(text=json.dumps({
                "status": "SAFE",
                "confidence": 0.9,
                "reasons": ["Test"],
                "warnings": []
            }))
        ]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        
        mock_client = mock_anthropic_client.return_value
        create_mock = AsyncMock(return_value=mock_response)
        mock_client.messages.create = create_mock
        
        provider = ClaudeProvider(provider_config)
        await provider.validate_file_deletion(test_context)
        
        # Check the call arguments
        call_args = create_mock.call_args
        
        # Claude uses different parameter names
        assert 'model' in call_args.kwargs
        assert 'messages' in call_args.kwargs
        assert 'max_tokens' in call_args.kwargs
        
        # Check message format
        messages = call_args.kwargs['messages']
        assert len(messages) >= 1
        assert messages[0]['role'] == 'user'
        assert test_context.file_path in messages[0]['content']
    
    @pytest.mark.asyncio
    async def test_handle_claude_api_error(self, provider_config, test_context, mock_anthropic_client):
        """Test handling of Claude API errors"""
        mock_client = mock_anthropic_client.return_value
        mock_client.messages.create = AsyncMock(
            side_effect=Exception("Rate limit exceeded")
        )
        
        provider = ClaudeProvider(provider_config)
        
        with pytest.raises(ValidationError) as exc_info:
            await provider.validate_file_deletion(test_context)
        
        assert "Rate limit exceeded" in str(exc_info.value)
        assert exc_info.value.retryable is True
    
    @pytest.mark.asyncio
    async def test_malformed_response_handling(self, provider_config, test_context, mock_anthropic_client):
        """Test handling of malformed responses"""
        mock_response = Mock()
        mock_response.content = [
            Mock(text="Not valid JSON")
        ]
        mock_response.usage = Mock(input_tokens=50, output_tokens=10)
        
        mock_client = mock_anthropic_client.return_value
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        
        provider = ClaudeProvider(provider_config)
        
        with pytest.raises(ValidationError) as exc_info:
            await provider.validate_file_deletion(test_context)
        
        assert "Invalid response format" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_empty_response_handling(self, provider_config, test_context, mock_anthropic_client):
        """Test handling of empty responses"""
        mock_response = Mock()
        mock_response.content = []
        mock_response.usage = Mock(input_tokens=50, output_tokens=0)
        
        mock_client = mock_anthropic_client.return_value
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        
        provider = ClaudeProvider(provider_config)
        
        with pytest.raises(ValidationError) as exc_info:
            await provider.validate_file_deletion(test_context)
        
        assert "Empty response" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, provider_config, test_context, mock_anthropic_client):
        """Test timeout handling"""
        async def slow_response():
            await asyncio.sleep(5)
            return Mock()
        
        mock_client = mock_anthropic_client.return_value
        mock_client.messages.create = slow_response
        
        provider_config.timeout = 0.1
        provider = ClaudeProvider(provider_config)
        
        with pytest.raises(ValidationError) as exc_info:
            await provider.validate_file_deletion(test_context)
        
        assert "timeout" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_model_selection(self, test_context, mock_anthropic_client):
        """Test different Claude model selection"""
        # Test with Claude Instant (faster, cheaper)
        config = ProviderConfig(
            name="claude",
            api_key="test-key",
            model="claude-instant-1.2",
            max_tokens=2000,
            temperature=0.0
        )
        
        mock_response = Mock()
        mock_response.content = [
            Mock(text=json.dumps({
                "status": "SAFE",
                "confidence": 0.88,
                "reasons": ["Simple utility"],
                "warnings": []
            }))
        ]
        mock_response.usage = Mock(input_tokens=80, output_tokens=30)
        
        mock_client = mock_anthropic_client.return_value
        create_mock = AsyncMock(return_value=mock_response)
        mock_client.messages.create = create_mock
        
        provider = ClaudeProvider(config)
        result = await provider.validate_file_deletion(test_context)
        
        # Verify model was used
        call_args = create_mock.call_args
        assert call_args.kwargs['model'] == "claude-instant-1.2"
        assert result.model_name == "claude-instant-1.2"
    
    @pytest.mark.asyncio
    async def test_cost_tracking(self, provider_config, test_context, mock_anthropic_client):
        """Test token usage and cost tracking for Claude"""
        mock_response = Mock()
        mock_response.content = [
            Mock(text=json.dumps({
                "status": "SAFE",
                "confidence": 0.9,
                "reasons": ["Test"],
                "warnings": []
            }))
        ]
        mock_response.usage = Mock(input_tokens=1000, output_tokens=200)
        
        mock_client = mock_anthropic_client.return_value
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        
        provider = ClaudeProvider(provider_config)
        result = await provider.validate_file_deletion(test_context)
        
        assert result.tokens_used == 1200
        
        # Check internal usage stats
        stats = provider.get_usage_stats()
        assert stats['total_tokens'] == 1200
        assert stats['total_requests'] == 1
        # Claude Opus pricing is different from GPT-4
        assert stats['total_cost'] > 0
    
    @pytest.mark.asyncio
    async def test_health_check(self, provider_config, mock_anthropic_client):
        """Test health check functionality"""
        # Mock successful message creation (simple test)
        mock_response = Mock()
        mock_response.content = [Mock(text="Claude is operational")]
        mock_response.usage = Mock(input_tokens=10, output_tokens=5)
        
        mock_client = mock_anthropic_client.return_value
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        
        provider = ClaudeProvider(provider_config)
        is_healthy = await provider.check_health()
        
        assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, provider_config, mock_anthropic_client):
        """Test health check when API is down"""
        mock_client = mock_anthropic_client.return_value
        mock_client.messages.create = AsyncMock(side_effect=Exception("Connection error"))
        
        provider = ClaudeProvider(provider_config)
        is_healthy = await provider.check_health()
        
        assert is_healthy is False
    
    def test_resolve_api_key_from_env(self, mock_anthropic_client):
        """Test resolving API key from environment variable"""
        import os
        os.environ["TEST_CLAUDE_KEY"] = "actual-claude-key"
        
        config = ProviderConfig(
            name="claude",
            api_key="${TEST_CLAUDE_KEY}",
            model="claude-3-opus-20240229"
        )
        
        with patch('ai_providers.claude_provider.AsyncAnthropic') as mock_class:
            provider = ClaudeProvider(config)
            
            # Check that client was initialized with resolved key
            mock_class.assert_called_once()
            call_args = mock_class.call_args
            assert call_args.kwargs['api_key'] == "actual-claude-key"
        
        del os.environ["TEST_CLAUDE_KEY"]
    
    @pytest.mark.asyncio
    async def test_system_prompt_in_user_message(self, provider_config, test_context, mock_anthropic_client):
        """Test that system prompt is included in user message for Claude"""
        mock_response = Mock()
        mock_response.content = [
            Mock(text=json.dumps({
                "status": "SAFE",
                "confidence": 0.9,
                "reasons": ["Test"],
                "warnings": []
            }))
        ]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        
        mock_client = mock_anthropic_client.return_value
        create_mock = AsyncMock(return_value=mock_response)
        mock_client.messages.create = create_mock
        
        provider = ClaudeProvider(provider_config)
        await provider.validate_file_deletion(test_context)
        
        # Check that system instructions are in the user message
        call_args = create_mock.call_args
        messages = call_args.kwargs['messages']
        
        user_message = messages[0]['content']
        assert "expert code analyst" in user_message
        assert "SAFE" in user_message
        assert "UNSAFE" in user_message
        assert "UNCERTAIN" in user_message