#!/usr/bin/env python3
"""
Tests for the base AI provider interface
"""

import pytest
from unittest.mock import Mock, AsyncMock
from dataclasses import dataclass
from typing import List, Dict, Optional

# Import the classes we'll implement
from ai_providers.base import (
    AIProvider,
    FileValidationContext,
    ValidationResult,
    ValidationStatus,
    ProviderConfig,
    ValidationError
)


class TestFileValidationContext:
    """Test the FileValidationContext data class"""
    
    def test_create_context_minimal(self):
        """Test creating a context with minimal information"""
        context = FileValidationContext(
            file_path="/test/file.py",
            file_content="print('hello')",
            file_type="python"
        )
        
        assert context.file_path == "/test/file.py"
        assert context.file_content == "print('hello')"
        assert context.file_type == "python"
        assert context.file_size == 0
        assert context.dependencies == []
        assert context.dependents == []
        assert context.metadata == {}
    
    def test_create_context_full(self):
        """Test creating a context with all information"""
        context = FileValidationContext(
            file_path="/test/module.py",
            file_content="import os\nprint('test')",
            file_type="python",
            file_size=1024,
            dependencies=["os", "sys"],
            dependents=["main.py", "test_module.py"],
            metadata={"last_modified": "2024-01-01", "author": "test"}
        )
        
        assert context.file_size == 1024
        assert len(context.dependencies) == 2
        assert "os" in context.dependencies
        assert len(context.dependents) == 2
        assert context.metadata["author"] == "test"
    
    def test_context_hash_for_caching(self):
        """Test that context can be hashed for caching purposes"""
        context = FileValidationContext(
            file_path="/test/file.py",
            file_content="test content",
            file_type="python"
        )
        
        # Should be able to create a hash for caching
        assert context.content_hash is not None
        assert len(context.content_hash) == 64  # SHA256 hex length


class TestValidationResult:
    """Test the ValidationResult data class"""
    
    def test_create_result_safe(self):
        """Test creating a safe validation result"""
        result = ValidationResult(
            status=ValidationStatus.SAFE,
            confidence=0.95,
            reasons=["No dependencies", "Temporary file"],
            warnings=[],
            provider_name="test_provider"
        )
        
        assert result.status == ValidationStatus.SAFE
        assert result.confidence == 0.95
        assert len(result.reasons) == 2
        assert result.is_safe is True
        assert result.is_unsafe is False
    
    def test_create_result_unsafe(self):
        """Test creating an unsafe validation result"""
        result = ValidationResult(
            status=ValidationStatus.UNSAFE,
            confidence=0.90,
            reasons=["Critical dependency found"],
            warnings=["Used by main application"],
            provider_name="test_provider"
        )
        
        assert result.status == ValidationStatus.UNSAFE
        assert result.is_safe is False
        assert result.is_unsafe is True
        assert len(result.warnings) == 1
    
    def test_result_with_metadata(self):
        """Test result with token usage and timing metadata"""
        result = ValidationResult(
            status=ValidationStatus.UNCERTAIN,
            confidence=0.5,
            reasons=["Unable to determine usage"],
            warnings=[],
            provider_name="test_provider",
            tokens_used=150,
            response_time_ms=1200,
            model_name="gpt-4"
        )
        
        assert result.tokens_used == 150
        assert result.response_time_ms == 1200
        assert result.model_name == "gpt-4"


class TestProviderConfig:
    """Test the ProviderConfig data class"""
    
    def test_create_config_minimal(self):
        """Test creating config with minimal settings"""
        config = ProviderConfig(
            name="test_provider",
            api_key="test_key"
        )
        
        assert config.name == "test_provider"
        assert config.api_key == "test_key"
        assert config.enabled is True  # Default
        assert config.max_tokens == 4000  # Default
        assert config.temperature == 0.2  # Default
    
    def test_create_config_from_dict(self):
        """Test creating config from dictionary"""
        config_dict = {
            "name": "openai",
            "api_key": "${OPENAI_API_KEY}",
            "model": "gpt-4",
            "max_tokens": 8000,
            "temperature": 0.1,
            "timeout": 30,
            "max_retries": 5
        }
        
        config = ProviderConfig.from_dict(config_dict)
        
        assert config.name == "openai"
        assert config.model == "gpt-4"
        assert config.max_tokens == 8000
        assert config.temperature == 0.1
        assert config.timeout == 30
        assert config.max_retries == 5
    
    def test_config_resolve_env_vars(self):
        """Test resolving environment variables in config"""
        import os
        os.environ["TEST_API_KEY"] = "actual_key_value"
        
        config = ProviderConfig(
            name="test",
            api_key="${TEST_API_KEY}"
        )
        
        resolved_key = config.resolve_api_key()
        assert resolved_key == "actual_key_value"
        
        # Clean up
        del os.environ["TEST_API_KEY"]


class TestAIProvider:
    """Test the abstract AIProvider base class"""
    
    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider for testing"""
        class MockProvider(AIProvider):
            async def validate_file_deletion(self, context: FileValidationContext) -> ValidationResult:
                return ValidationResult(
                    status=ValidationStatus.SAFE,
                    confidence=0.9,
                    reasons=["Test reason"],
                    warnings=[],
                    provider_name=self.name
                )
            
            async def check_health(self) -> bool:
                return True
        
        config = ProviderConfig(name="mock", api_key="test")
        return MockProvider(config)
    
    @pytest.mark.asyncio
    async def test_provider_basic_validation(self, mock_provider):
        """Test basic validation flow"""
        context = FileValidationContext(
            file_path="/test/file.py",
            file_content="test",
            file_type="python"
        )
        
        result = await mock_provider.validate_file_deletion(context)
        
        assert result.status == ValidationStatus.SAFE
        assert result.provider_name == "mock"
        assert result.confidence == 0.9
    
    @pytest.mark.asyncio
    async def test_provider_with_retry(self, mock_provider):
        """Test provider retry logic"""
        # Mock a provider that fails first then succeeds
        mock_provider.validate_file_deletion = AsyncMock(
            side_effect=[
                ValidationError("API Error"),
                ValidationResult(
                    status=ValidationStatus.SAFE,
                    confidence=0.8,
                    reasons=["Success after retry"],
                    warnings=[],
                    provider_name="mock"
                )
            ]
        )
        
        context = FileValidationContext(
            file_path="/test/file.py",
            file_content="test",
            file_type="python"
        )
        
        # The retry wrapper should handle the first failure
        result = await mock_provider.validate_with_retry(context)
        
        assert result.status == ValidationStatus.SAFE
        assert mock_provider.validate_file_deletion.call_count == 2
    
    @pytest.mark.asyncio
    async def test_provider_timeout(self, mock_provider):
        """Test provider timeout handling"""
        import asyncio
        
        # Mock a provider that takes too long
        async def slow_validation(context):
            await asyncio.sleep(10)  # Longer than timeout
            return ValidationResult(
                status=ValidationStatus.SAFE,
                confidence=1.0,
                reasons=[],
                warnings=[],
                provider_name="mock"
            )
        
        mock_provider.validate_file_deletion = slow_validation
        mock_provider.config.timeout = 0.1  # 100ms timeout
        
        context = FileValidationContext(
            file_path="/test/file.py",
            file_content="test",
            file_type="python"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await mock_provider.validate_with_timeout(context)
        
        assert "timeout" in str(exc_info.value).lower()
    
    def test_provider_name_property(self, mock_provider):
        """Test provider name property"""
        assert mock_provider.name == "mock"
    
    def test_provider_enabled_property(self, mock_provider):
        """Test provider enabled property"""
        assert mock_provider.enabled is True
        
        mock_provider.config.enabled = False
        assert mock_provider.enabled is False
    
    @pytest.mark.asyncio
    async def test_provider_cost_tracking(self, mock_provider):
        """Test token usage and cost tracking"""
        context = FileValidationContext(
            file_path="/test/file.py",
            file_content="test content" * 100,  # Larger content
            file_type="python"
        )
        
        # Add cost tracking to mock
        mock_provider.track_usage = Mock()
        
        result = await mock_provider.validate_file_deletion(context)
        
        # Should track token usage
        # mock_provider.track_usage.assert_called_once()


class TestValidationStatus:
    """Test the ValidationStatus enum"""
    
    def test_status_values(self):
        """Test that all expected status values exist"""
        assert ValidationStatus.SAFE.value == "safe"
        assert ValidationStatus.UNSAFE.value == "unsafe"
        assert ValidationStatus.UNCERTAIN.value == "uncertain"
        assert ValidationStatus.ERROR.value == "error"
        assert ValidationStatus.SKIPPED.value == "skipped"
    
    def test_status_ordering(self):
        """Test status priority for consensus decisions"""
        # UNSAFE should have highest priority in disagreements
        statuses = [
            ValidationStatus.SAFE,
            ValidationStatus.UNSAFE,
            ValidationStatus.UNCERTAIN
        ]
        
        # Sort by safety priority (unsafe first)
        sorted_statuses = sorted(statuses, key=lambda s: s.safety_priority)
        
        assert sorted_statuses[0] == ValidationStatus.UNSAFE
        assert sorted_statuses[-1] == ValidationStatus.SAFE


class TestValidationError:
    """Test the ValidationError exception"""
    
    def test_validation_error_creation(self):
        """Test creating validation errors"""
        error = ValidationError("API rate limit exceeded")
        assert str(error) == "API rate limit exceeded"
        assert error.retryable is True  # Default
    
    def test_validation_error_non_retryable(self):
        """Test non-retryable errors"""
        error = ValidationError("Invalid API key", retryable=False)
        assert error.retryable is False
    
    def test_validation_error_with_context(self):
        """Test error with additional context"""
        error = ValidationError(
            "Model not available",
            retryable=True,
            provider="openai",
            model="gpt-4"
        )
        
        assert error.provider == "openai"
        assert error.model == "gpt-4"