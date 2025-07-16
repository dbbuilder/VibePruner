#!/usr/bin/env python3
"""
Tests for consensus validation logic
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import asyncio

from ai_providers.base import (
    ValidationStatus, 
    ValidationResult,
    FileValidationContext,
    ProviderConfig
)
from ai_validation import (
    ConsensusValidator,
    ConsensusMode,
    AIValidationConfig,
    BatchValidationResult,
    ConsensusResult
)


class TestConsensusValidator:
    """Test the consensus validation logic"""
    
    @pytest.fixture
    def mock_providers(self):
        """Create mock AI providers for testing"""
        providers = []
        for i in range(3):
            provider = Mock()
            provider.name = f"provider_{i}"
            provider.enabled = True
            provider.validate_file_deletion = AsyncMock()
            providers.append(provider)
        return providers
    
    @pytest.fixture
    def validator_config(self):
        """Create test configuration"""
        return AIValidationConfig(
            enabled=True,
            consensus_mode=ConsensusMode.MAJORITY,
            confidence_threshold=0.7,
            max_concurrent_validations=3
        )
    
    @pytest.fixture
    def test_context(self):
        """Create test file context"""
        return FileValidationContext(
            file_path="/test/file.py",
            file_content="test content",
            file_type="python",
            file_size=100
        )
    
    @pytest.mark.asyncio
    async def test_unanimous_consensus_all_safe(self, mock_providers, validator_config, test_context):
        """Test unanimous consensus when all providers say safe"""
        validator_config.consensus_mode = ConsensusMode.UNANIMOUS
        
        # All providers return SAFE
        for provider in mock_providers:
            provider.validate_file_deletion.return_value = ValidationResult(
                status=ValidationStatus.SAFE,
                confidence=0.9,
                reasons=["No dependencies"],
                warnings=[],
                provider_name=provider.name
            )
        
        validator = ConsensusValidator(mock_providers, validator_config)
        result = await validator.validate_file(test_context)
        
        assert result.consensus_reached is True
        assert result.final_status == ValidationStatus.SAFE
        assert result.can_delete is True
        assert result.average_confidence == 0.9
        assert len(result.provider_results) == 3
    
    @pytest.mark.asyncio
    async def test_unanimous_consensus_one_unsafe(self, mock_providers, validator_config, test_context):
        """Test unanimous consensus when one provider says unsafe"""
        validator_config.consensus_mode = ConsensusMode.UNANIMOUS
        
        # Two SAFE, one UNSAFE
        mock_providers[0].validate_file_deletion.return_value = ValidationResult(
            status=ValidationStatus.SAFE,
            confidence=0.9,
            reasons=["No dependencies"],
            warnings=[],
            provider_name=mock_providers[0].name
        )
        mock_providers[1].validate_file_deletion.return_value = ValidationResult(
            status=ValidationStatus.SAFE,
            confidence=0.85,
            reasons=["Looks unused"],
            warnings=[],
            provider_name=mock_providers[1].name
        )
        mock_providers[2].validate_file_deletion.return_value = ValidationResult(
            status=ValidationStatus.UNSAFE,
            confidence=0.95,
            reasons=["Critical dependency found"],
            warnings=["Used by main.py"],
            provider_name=mock_providers[2].name
        )
        
        validator = ConsensusValidator(mock_providers, validator_config)
        result = await validator.validate_file(test_context)
        
        assert result.consensus_reached is True
        assert result.final_status == ValidationStatus.UNSAFE
        assert result.can_delete is False
        assert "Critical dependency found" in result.aggregated_reasons
    
    @pytest.mark.asyncio
    async def test_majority_consensus_two_safe(self, mock_providers, validator_config, test_context):
        """Test majority consensus when 2/3 providers say safe"""
        validator_config.consensus_mode = ConsensusMode.MAJORITY
        
        # Two SAFE, one UNSAFE
        mock_providers[0].validate_file_deletion.return_value = ValidationResult(
            status=ValidationStatus.SAFE,
            confidence=0.8,
            reasons=["No dependencies"],
            warnings=[],
            provider_name=mock_providers[0].name
        )
        mock_providers[1].validate_file_deletion.return_value = ValidationResult(
            status=ValidationStatus.SAFE,
            confidence=0.85,
            reasons=["Temporary file"],
            warnings=[],
            provider_name=mock_providers[1].name
        )
        mock_providers[2].validate_file_deletion.return_value = ValidationResult(
            status=ValidationStatus.UNSAFE,
            confidence=0.7,
            reasons=["Might be used"],
            warnings=[],
            provider_name=mock_providers[2].name
        )
        
        validator = ConsensusValidator(mock_providers, validator_config)
        result = await validator.validate_file(test_context)
        
        assert result.consensus_reached is True
        assert result.final_status == ValidationStatus.SAFE
        assert result.can_delete is True
        assert result.agreement_count == 2
        assert result.disagreement_details["unsafe_count"] == 1
    
    @pytest.mark.asyncio
    async def test_any_consensus_mode(self, mock_providers, validator_config, test_context):
        """Test 'any' consensus mode - one safe is enough"""
        validator_config.consensus_mode = ConsensusMode.ANY
        
        # One SAFE, two UNSAFE
        mock_providers[0].validate_file_deletion.return_value = ValidationResult(
            status=ValidationStatus.SAFE,
            confidence=0.9,
            reasons=["Clearly unused"],
            warnings=[],
            provider_name=mock_providers[0].name
        )
        mock_providers[1].validate_file_deletion.return_value = ValidationResult(
            status=ValidationStatus.UNSAFE,
            confidence=0.8,
            reasons=["Dependency"],
            warnings=[],
            provider_name=mock_providers[1].name
        )
        mock_providers[2].validate_file_deletion.return_value = ValidationResult(
            status=ValidationStatus.UNCERTAIN,
            confidence=0.5,
            reasons=["Not sure"],
            warnings=[],
            provider_name=mock_providers[2].name
        )
        
        validator = ConsensusValidator(mock_providers, validator_config)
        result = await validator.validate_file(test_context)
        
        assert result.consensus_reached is True
        assert result.final_status == ValidationStatus.SAFE
        assert result.can_delete is True
    
    @pytest.mark.asyncio
    async def test_provider_failure_handling(self, mock_providers, validator_config, test_context):
        """Test handling when a provider fails"""
        # One provider fails
        mock_providers[0].validate_file_deletion.side_effect = Exception("API Error")
        
        # Others return results
        mock_providers[1].validate_file_deletion.return_value = ValidationResult(
            status=ValidationStatus.SAFE,
            confidence=0.8,
            reasons=["No issues"],
            warnings=[],
            provider_name=mock_providers[1].name
        )
        mock_providers[2].validate_file_deletion.return_value = ValidationResult(
            status=ValidationStatus.SAFE,
            confidence=0.85,
            reasons=["Unused"],
            warnings=[],
            provider_name=mock_providers[2].name
        )
        
        validator = ConsensusValidator(mock_providers, validator_config)
        result = await validator.validate_file(test_context)
        
        # Should still work with 2/3 providers
        assert result.final_status == ValidationStatus.SAFE
        assert result.can_delete is True
        assert result.provider_errors == 1
        assert len(result.provider_results) == 2  # Only successful ones
    
    @pytest.mark.asyncio
    async def test_all_providers_fail(self, mock_providers, validator_config, test_context):
        """Test when all providers fail"""
        for provider in mock_providers:
            provider.validate_file_deletion.side_effect = Exception("API Error")
        
        validator = ConsensusValidator(mock_providers, validator_config)
        result = await validator.validate_file(test_context)
        
        assert result.final_status == ValidationStatus.ERROR
        assert result.can_delete is False
        assert result.provider_errors == 3
        assert result.consensus_reached is False
    
    @pytest.mark.asyncio
    async def test_confidence_threshold(self, mock_providers, validator_config, test_context):
        """Test confidence threshold enforcement"""
        validator_config.confidence_threshold = 0.8
        
        # All safe but low confidence
        for provider in mock_providers:
            provider.validate_file_deletion.return_value = ValidationResult(
                status=ValidationStatus.SAFE,
                confidence=0.6,  # Below threshold
                reasons=["Maybe unused"],
                warnings=[],
                provider_name=provider.name
            )
        
        validator = ConsensusValidator(mock_providers, validator_config)
        result = await validator.validate_file(test_context)
        
        # Should not delete due to low confidence
        assert result.final_status == ValidationStatus.UNCERTAIN
        assert result.can_delete is False
        assert result.average_confidence == 0.6
        assert "confidence below threshold" in str(result.aggregated_warnings).lower()
    
    @pytest.mark.asyncio
    async def test_batch_validation(self, mock_providers, validator_config):
        """Test batch validation of multiple files"""
        contexts = [
            FileValidationContext(
                file_path=f"/test/file{i}.py",
                file_content=f"content {i}",
                file_type="python"
            )
            for i in range(5)
        ]
        
        # Mix of results
        results = [
            ValidationStatus.SAFE,
            ValidationStatus.SAFE,
            ValidationStatus.UNSAFE,
            ValidationStatus.UNCERTAIN,
            ValidationStatus.SAFE
        ]
        
        for provider in mock_providers:
            provider.validate_file_deletion.side_effect = [
                ValidationResult(
                    status=status,
                    confidence=0.8,
                    reasons=[f"{status.value} file"],
                    warnings=[],
                    provider_name=provider.name
                )
                for status in results
            ]
        
        validator = ConsensusValidator(mock_providers, validator_config)
        batch_result = await validator.validate_batch(contexts)
        
        assert batch_result.total_files == 5
        assert batch_result.safe_count == 3
        assert batch_result.unsafe_count == 1
        assert batch_result.uncertain_count == 1
        assert len(batch_result.results) == 5
    
    @pytest.mark.asyncio
    async def test_concurrent_validation_limit(self, mock_providers, validator_config):
        """Test that concurrent validations are limited"""
        validator_config.max_concurrent_validations = 2
        
        # Track concurrent calls
        concurrent_calls = []
        call_times = []
        
        async def slow_validate(context):
            call_times.append(datetime.now())
            concurrent_calls.append(1)
            current_concurrent = len(concurrent_calls)
            await asyncio.sleep(0.1)  # Simulate API call
            concurrent_calls.pop()
            return ValidationResult(
                status=ValidationStatus.SAFE,
                confidence=0.9,
                reasons=[],
                warnings=[],
                provider_name="test"
            )
        
        for provider in mock_providers:
            provider.validate_file_deletion = slow_validate
        
        contexts = [
            FileValidationContext(
                file_path=f"/test/file{i}.py",
                file_content="content",
                file_type="python"
            )
            for i in range(6)
        ]
        
        validator = ConsensusValidator(mock_providers, validator_config)
        await validator.validate_batch(contexts)
        
        # Check that no more than 2 were concurrent
        # With 3 providers and 6 files, we have 18 total validations
        # But with max_concurrent=2, only 2 should run at once
        max_concurrent = max(len(concurrent_calls) for _ in range(len(call_times)))
        assert max_concurrent <= validator_config.max_concurrent_validations
    
    @pytest.mark.asyncio
    async def test_disabled_providers_skipped(self, mock_providers, validator_config, test_context):
        """Test that disabled providers are skipped"""
        # Disable one provider
        mock_providers[1].enabled = False
        
        # Set expectations for enabled providers only
        mock_providers[0].validate_file_deletion.return_value = ValidationResult(
            status=ValidationStatus.SAFE,
            confidence=0.9,
            reasons=["Safe"],
            warnings=[],
            provider_name=mock_providers[0].name
        )
        mock_providers[2].validate_file_deletion.return_value = ValidationResult(
            status=ValidationStatus.SAFE,
            confidence=0.85,
            reasons=["Also safe"],
            warnings=[],
            provider_name=mock_providers[2].name
        )
        
        validator = ConsensusValidator(mock_providers, validator_config)
        result = await validator.validate_file(test_context)
        
        # Should only use 2 providers
        assert len(result.provider_results) == 2
        assert result.final_status == ValidationStatus.SAFE
        # Disabled provider should not be called
        mock_providers[1].validate_file_deletion.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_caching_integration(self, mock_providers, validator_config, test_context):
        """Test that caching works with consensus validation"""
        # Enable caching in config
        validator_config.cache_enabled = True
        validator_config.cache_ttl_seconds = 3600
        
        # Mock cache
        with patch('ai_validation.AIResponseCache') as MockCache:
            cache_instance = MockCache.return_value
            cache_instance.get.return_value = None  # First call - cache miss
            cache_instance.set = Mock()
            
            for provider in mock_providers:
                provider.validate_file_deletion.return_value = ValidationResult(
                    status=ValidationStatus.SAFE,
                    confidence=0.9,
                    reasons=["Cached result"],
                    warnings=[],
                    provider_name=provider.name
                )
            
            validator = ConsensusValidator(mock_providers, validator_config)
            
            # First call
            result1 = await validator.validate_file(test_context)
            assert result1.final_status == ValidationStatus.SAFE
            
            # Cache should be set
            assert cache_instance.set.called
            
            # Second call with cache hit
            cache_instance.get.return_value = result1
            result2 = await validator.validate_file(test_context)
            
            # Should return cached result
            assert result2.final_status == result1.final_status
            assert result2.from_cache is True


class TestConsensusResult:
    """Test the ConsensusResult data class"""
    
    def test_consensus_result_creation(self):
        """Test creating a consensus result"""
        provider_results = [
            ValidationResult(
                status=ValidationStatus.SAFE,
                confidence=0.9,
                reasons=["No deps"],
                warnings=[],
                provider_name="provider1"
            ),
            ValidationResult(
                status=ValidationStatus.SAFE,
                confidence=0.85,
                reasons=["Unused"],
                warnings=["Old file"],
                provider_name="provider2"
            )
        ]
        
        result = ConsensusResult(
            file_path="/test/file.py",
            provider_results=provider_results,
            final_status=ValidationStatus.SAFE,
            consensus_reached=True,
            can_delete=True,
            average_confidence=0.875
        )
        
        assert result.file_path == "/test/file.py"
        assert result.final_status == ValidationStatus.SAFE
        assert result.can_delete is True
        assert len(result.provider_results) == 2
        assert result.average_confidence == 0.875
    
    def test_aggregated_reasons(self):
        """Test aggregating reasons from multiple providers"""
        provider_results = [
            ValidationResult(
                status=ValidationStatus.SAFE,
                confidence=0.9,
                reasons=["No dependencies", "Temporary file"],
                warnings=[],
                provider_name="provider1"
            ),
            ValidationResult(
                status=ValidationStatus.SAFE,
                confidence=0.85,
                reasons=["No dependencies", "Not in project files"],
                warnings=[],
                provider_name="provider2"
            )
        ]
        
        result = ConsensusResult(
            file_path="/test/file.py",
            provider_results=provider_results,
            final_status=ValidationStatus.SAFE,
            consensus_reached=True,
            can_delete=True
        )
        
        # Should deduplicate reasons
        assert "No dependencies" in result.aggregated_reasons
        assert "Temporary file" in result.aggregated_reasons
        assert "Not in project files" in result.aggregated_reasons
        assert len(result.aggregated_reasons) == 3  # No duplicates
    
    def test_disagreement_details(self):
        """Test tracking disagreement details"""
        provider_results = [
            ValidationResult(
                status=ValidationStatus.SAFE,
                confidence=0.9,
                reasons=["Safe"],
                warnings=[],
                provider_name="provider1"
            ),
            ValidationResult(
                status=ValidationStatus.UNSAFE,
                confidence=0.95,
                reasons=["Has dependencies"],
                warnings=[],
                provider_name="provider2"
            ),
            ValidationResult(
                status=ValidationStatus.UNCERTAIN,
                confidence=0.5,
                reasons=["Not sure"],
                warnings=[],
                provider_name="provider3"
            )
        ]
        
        result = ConsensusResult(
            file_path="/test/file.py",
            provider_results=provider_results,
            final_status=ValidationStatus.UNCERTAIN,
            consensus_reached=False,
            can_delete=False,
            disagreement_details={
                "safe_count": 1,
                "unsafe_count": 1,
                "uncertain_count": 1,
                "providers_by_status": {
                    "safe": ["provider1"],
                    "unsafe": ["provider2"],
                    "uncertain": ["provider3"]
                }
            }
        )
        
        assert result.disagreement_details["safe_count"] == 1
        assert result.disagreement_details["unsafe_count"] == 1
        assert result.disagreement_details["uncertain_count"] == 1
        assert "provider2" in result.disagreement_details["providers_by_status"]["unsafe"]