#!/usr/bin/env python3
"""
AI-powered validation with consensus from multiple providers
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Any, Set
from collections import Counter, defaultdict

from ai_providers.base import (
    AIProvider,
    FileValidationContext,
    ValidationResult,
    ValidationStatus,
    ValidationError
)
from ai_cache import AIResponseCache

logger = logging.getLogger(__name__)


class ConsensusMode(Enum):
    """How to determine consensus among providers"""
    UNANIMOUS = "unanimous"  # All providers must agree
    MAJORITY = "majority"    # More than half must agree
    ANY = "any"             # Any provider saying safe is enough
    WEIGHTED = "weighted"    # Weight by confidence scores


@dataclass
class AIValidationConfig:
    """Configuration for AI validation"""
    enabled: bool = True
    consensus_mode: ConsensusMode = ConsensusMode.MAJORITY
    confidence_threshold: float = 0.7
    max_concurrent_validations: int = 5
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour
    timeout_seconds: int = 30
    max_retries: int = 3
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AIValidationConfig':
        """Create config from dictionary"""
        if 'consensus_mode' in config_dict:
            config_dict['consensus_mode'] = ConsensusMode(config_dict['consensus_mode'])
        return cls(**config_dict)


@dataclass
class ConsensusResult:
    """Result of consensus validation"""
    file_path: str
    provider_results: List[ValidationResult]
    final_status: ValidationStatus
    consensus_reached: bool
    can_delete: bool
    average_confidence: float = 0.0
    agreement_count: int = 0
    total_providers: int = 0
    provider_errors: int = 0
    disagreement_details: Dict[str, Any] = field(default_factory=dict)
    aggregated_reasons: List[str] = field(default_factory=list)
    aggregated_warnings: List[str] = field(default_factory=list)
    validation_time_ms: int = 0
    from_cache: bool = False
    
    def __post_init__(self):
        """Calculate aggregated data after initialization"""
        if self.provider_results:
            # Calculate average confidence
            confidences = [r.confidence for r in self.provider_results]
            self.average_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Aggregate unique reasons and warnings
            all_reasons = []
            all_warnings = []
            
            for result in self.provider_results:
                all_reasons.extend(result.reasons)
                all_warnings.extend(result.warnings)
            
            # Remove duplicates while preserving order
            seen = set()
            self.aggregated_reasons = []
            for reason in all_reasons:
                if reason not in seen:
                    seen.add(reason)
                    self.aggregated_reasons.append(reason)
            
            seen = set()
            self.aggregated_warnings = []
            for warning in all_warnings:
                if warning not in seen:
                    seen.add(warning)
                    self.aggregated_warnings.append(warning)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'file_path': self.file_path,
            'final_status': self.final_status.value,
            'consensus_reached': self.consensus_reached,
            'can_delete': self.can_delete,
            'average_confidence': self.average_confidence,
            'agreement_count': self.agreement_count,
            'total_providers': self.total_providers,
            'provider_errors': self.provider_errors,
            'disagreement_details': self.disagreement_details,
            'aggregated_reasons': self.aggregated_reasons,
            'aggregated_warnings': self.aggregated_warnings,
            'validation_time_ms': self.validation_time_ms,
            'from_cache': self.from_cache,
            'provider_results': [r.to_dict() for r in self.provider_results]
        }


@dataclass
class BatchValidationResult:
    """Result of validating multiple files"""
    results: List[ConsensusResult]
    total_files: int = 0
    safe_count: int = 0
    unsafe_count: int = 0
    uncertain_count: int = 0
    error_count: int = 0
    total_time_ms: int = 0
    from_cache_count: int = 0
    
    def __post_init__(self):
        """Calculate summary statistics"""
        if self.results:
            self.total_files = len(self.results)
            
            status_counts = Counter(r.final_status for r in self.results)
            self.safe_count = status_counts.get(ValidationStatus.SAFE, 0)
            self.unsafe_count = status_counts.get(ValidationStatus.UNSAFE, 0)
            self.uncertain_count = status_counts.get(ValidationStatus.UNCERTAIN, 0)
            self.error_count = status_counts.get(ValidationStatus.ERROR, 0)
            
            self.total_time_ms = sum(r.validation_time_ms for r in self.results)
            self.from_cache_count = sum(1 for r in self.results if r.from_cache)


class ConsensusValidator:
    """Validates files using consensus from multiple AI providers"""
    
    def __init__(self, providers: List[AIProvider], config: AIValidationConfig):
        self.providers = [p for p in providers if p.enabled]
        self.config = config
        self.cache = AIResponseCache() if config.cache_enabled else None
        self._semaphore = asyncio.Semaphore(config.max_concurrent_validations)
    
    async def validate_file(self, context: FileValidationContext) -> ConsensusResult:
        """Validate a single file using all providers"""
        start_time = datetime.now()
        
        # Check cache first
        if self.cache:
            cached_result = self.cache.get(context.content_hash)
            if cached_result:
                logger.info(f"Cache hit for {context.file_path}")
                cached_result.from_cache = True
                return cached_result
        
        # Get enabled providers
        enabled_providers = [p for p in self.providers if p.enabled]
        if not enabled_providers:
            return ConsensusResult(
                file_path=context.file_path,
                provider_results=[],
                final_status=ValidationStatus.ERROR,
                consensus_reached=False,
                can_delete=False,
                provider_errors=len(self.providers),
                aggregated_warnings=["No enabled providers"]
            )
        
        # Validate with all providers concurrently
        tasks = []
        for provider in enabled_providers:
            task = self._validate_with_provider(provider, context)
            tasks.append(task)
        
        # Wait for all validations
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        valid_results = []
        provider_errors = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Provider {enabled_providers[i].name} failed: {result}")
                provider_errors += 1
            elif isinstance(result, ValidationResult):
                valid_results.append(result)
            else:
                logger.warning(f"Unexpected result type from {enabled_providers[i].name}: {type(result)}")
                provider_errors += 1
        
        # Determine consensus
        consensus_result = self._determine_consensus(
            context.file_path,
            valid_results,
            len(enabled_providers),
            provider_errors
        )
        
        # Add timing
        consensus_result.validation_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Cache result
        if self.cache and consensus_result.consensus_reached:
            self.cache.set(
                context.content_hash,
                consensus_result,
                ttl_seconds=self.config.cache_ttl_seconds
            )
        
        return consensus_result
    
    async def validate_batch(self, contexts: List[FileValidationContext]) -> BatchValidationResult:
        """Validate multiple files"""
        start_time = datetime.now()
        
        # Create validation tasks with semaphore limiting
        tasks = []
        for context in contexts:
            task = self._validate_with_semaphore(context)
            tasks.append(task)
        
        # Wait for all validations
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch validation failed for {contexts[i].file_path}: {result}")
                # Create error result
                error_result = ConsensusResult(
                    file_path=contexts[i].file_path,
                    provider_results=[],
                    final_status=ValidationStatus.ERROR,
                    consensus_reached=False,
                    can_delete=False,
                    aggregated_warnings=[str(result)]
                )
                valid_results.append(error_result)
            else:
                valid_results.append(result)
        
        batch_result = BatchValidationResult(results=valid_results)
        batch_result.total_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return batch_result
    
    async def _validate_with_semaphore(self, context: FileValidationContext) -> ConsensusResult:
        """Validate with semaphore limiting concurrent operations"""
        async with self._semaphore:
            return await self.validate_file(context)
    
    async def _validate_with_provider(self, provider: AIProvider, context: FileValidationContext) -> ValidationResult:
        """Validate with a single provider"""
        try:
            # Add timeout
            result = await asyncio.wait_for(
                provider.validate_file_deletion(context),
                timeout=self.config.timeout_seconds
            )
            return result
        except asyncio.TimeoutError:
            raise ValidationError(f"Provider {provider.name} timed out")
        except Exception as e:
            raise ValidationError(f"Provider {provider.name} error: {str(e)}")
    
    def _determine_consensus(
        self,
        file_path: str,
        results: List[ValidationResult],
        total_providers: int,
        provider_errors: int
    ) -> ConsensusResult:
        """Determine consensus from provider results"""
        if not results:
            # All providers failed
            return ConsensusResult(
                file_path=file_path,
                provider_results=[],
                final_status=ValidationStatus.ERROR,
                consensus_reached=False,
                can_delete=False,
                provider_errors=provider_errors,
                total_providers=total_providers,
                aggregated_warnings=["All providers failed"]
            )
        
        # Count status votes
        status_counts = Counter(r.status for r in results)
        status_by_provider = defaultdict(list)
        
        for result in results:
            status_by_provider[result.status].append(result.provider_name)
        
        # Check confidence threshold
        avg_confidence = sum(r.confidence for r in results) / len(results)
        if avg_confidence < self.config.confidence_threshold:
            # Low confidence overrides status
            return ConsensusResult(
                file_path=file_path,
                provider_results=results,
                final_status=ValidationStatus.UNCERTAIN,
                consensus_reached=False,
                can_delete=False,
                average_confidence=avg_confidence,
                total_providers=total_providers,
                provider_errors=provider_errors,
                aggregated_warnings=[f"Average confidence {avg_confidence:.2f} below threshold {self.config.confidence_threshold}"]
            )
        
        # Determine final status based on consensus mode
        final_status, consensus_reached, can_delete = self._apply_consensus_rules(
            status_counts,
            len(results),
            total_providers
        )
        
        # Build disagreement details
        disagreement_details = {
            "safe_count": status_counts.get(ValidationStatus.SAFE, 0),
            "unsafe_count": status_counts.get(ValidationStatus.UNSAFE, 0),
            "uncertain_count": status_counts.get(ValidationStatus.UNCERTAIN, 0),
            "providers_by_status": {
                status.value: providers
                for status, providers in status_by_provider.items()
            }
        }
        
        # Count agreements (providers with same status as final)
        agreement_count = status_counts.get(final_status, 0)
        
        return ConsensusResult(
            file_path=file_path,
            provider_results=results,
            final_status=final_status,
            consensus_reached=consensus_reached,
            can_delete=can_delete,
            average_confidence=avg_confidence,
            agreement_count=agreement_count,
            total_providers=total_providers,
            provider_errors=provider_errors,
            disagreement_details=disagreement_details
        )
    
    def _apply_consensus_rules(
        self,
        status_counts: Counter,
        valid_providers: int,
        total_providers: int
    ) -> tuple[ValidationStatus, bool, bool]:
        """Apply consensus rules to determine final status"""
        
        # Safety first - if any provider says unsafe in unanimous mode
        if self.config.consensus_mode == ConsensusMode.UNANIMOUS:
            if status_counts.get(ValidationStatus.UNSAFE, 0) > 0:
                return ValidationStatus.UNSAFE, True, False
            elif status_counts.get(ValidationStatus.UNCERTAIN, 0) > 0:
                return ValidationStatus.UNCERTAIN, True, False
            elif status_counts.get(ValidationStatus.SAFE, 0) == valid_providers:
                return ValidationStatus.SAFE, True, True
            else:
                return ValidationStatus.UNCERTAIN, False, False
        
        elif self.config.consensus_mode == ConsensusMode.MAJORITY:
            # Need more than half
            threshold = valid_providers / 2
            
            if status_counts.get(ValidationStatus.UNSAFE, 0) > threshold:
                return ValidationStatus.UNSAFE, True, False
            elif status_counts.get(ValidationStatus.SAFE, 0) > threshold:
                return ValidationStatus.SAFE, True, True
            else:
                # No clear majority
                return ValidationStatus.UNCERTAIN, False, False
        
        elif self.config.consensus_mode == ConsensusMode.ANY:
            # Any safe vote is enough (but unsafe takes precedence)
            if status_counts.get(ValidationStatus.UNSAFE, 0) > 0:
                return ValidationStatus.UNSAFE, True, False
            elif status_counts.get(ValidationStatus.SAFE, 0) > 0:
                return ValidationStatus.SAFE, True, True
            else:
                return ValidationStatus.UNCERTAIN, True, False
        
        else:
            # Default to uncertain if mode not recognized
            return ValidationStatus.UNCERTAIN, False, False