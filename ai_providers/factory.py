#!/usr/bin/env python3
"""
Factory for creating AI provider instances
"""

import logging
from typing import Dict, List, Optional, Type

from .base import AIProvider, ProviderConfig
from .openai_provider import OpenAIProvider
from .claude_provider import ClaudeProvider  
from .gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class ProviderFactory:
    """Factory for creating AI provider instances"""
    
    # Registry of available providers
    PROVIDERS: Dict[str, Type[AIProvider]] = {
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "anthropic": ClaudeProvider,  # Alias
        "gemini": GeminiProvider,
        "google": GeminiProvider,  # Alias
    }
    
    @classmethod
    def create_provider(cls, config: ProviderConfig) -> AIProvider:
        """
        Create a provider instance from configuration
        
        Args:
            config: Provider configuration
            
        Returns:
            Configured AI provider instance
            
        Raises:
            ValueError: If provider type is not supported
        """
        provider_type = config.name.lower()
        
        if provider_type not in cls.PROVIDERS:
            raise ValueError(
                f"Unknown provider type: {provider_type}. "
                f"Supported providers: {list(cls.PROVIDERS.keys())}"
            )
        
        provider_class = cls.PROVIDERS[provider_type]
        
        try:
            provider = provider_class(config)
            logger.info(f"Created {provider_type} provider with model {config.model}")
            return provider
        except ImportError as e:
            logger.error(f"Failed to create {provider_type} provider: {e}")
            raise ImportError(
                f"Required package for {provider_type} not installed. "
                f"Please install the required dependencies."
            )
        except Exception as e:
            logger.error(f"Error creating {provider_type} provider: {e}")
            raise
    
    @classmethod
    def create_providers_from_config(cls, config_dict: Dict[str, Dict]) -> List[AIProvider]:
        """
        Create multiple providers from configuration dictionary
        
        Args:
            config_dict: Dictionary of provider configurations
            
        Returns:
            List of configured AI provider instances
        """
        providers = []
        
        for provider_name, provider_config in config_dict.items():
            if not provider_config.get('enabled', True):
                logger.info(f"Skipping disabled provider: {provider_name}")
                continue
            
            try:
                # Add the provider name to config if not present
                if 'name' not in provider_config:
                    provider_config['name'] = provider_name
                
                config = ProviderConfig.from_dict(provider_config)
                provider = cls.create_provider(config)
                providers.append(provider)
                
            except Exception as e:
                logger.error(f"Failed to create provider {provider_name}: {e}")
                # Continue with other providers
        
        return providers
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[AIProvider]):
        """
        Register a custom provider
        
        Args:
            name: Provider name
            provider_class: Provider class that extends AIProvider
        """
        cls.PROVIDERS[name.lower()] = provider_class
        logger.info(f"Registered custom provider: {name}")
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available provider names"""
        return list(cls.PROVIDERS.keys())
    
    @classmethod
    def create_provider_with_fallback(
        cls,
        primary_config: ProviderConfig,
        fallback_configs: List[ProviderConfig]
    ) -> AIProvider:
        """
        Create a provider with fallback options
        
        Args:
            primary_config: Primary provider configuration
            fallback_configs: List of fallback configurations
            
        Returns:
            First successfully created provider
            
        Raises:
            RuntimeError: If no providers could be created
        """
        configs = [primary_config] + fallback_configs
        errors = []
        
        for config in configs:
            try:
                provider = cls.create_provider(config)
                if len(errors) > 0:
                    logger.info(f"Using fallback provider: {config.name}")
                return provider
            except Exception as e:
                errors.append(f"{config.name}: {str(e)}")
                continue
        
        # All failed
        error_msg = "Failed to create any provider:\n" + "\n".join(errors)
        raise RuntimeError(error_msg)


def create_default_providers() -> List[AIProvider]:
    """
    Create providers with default configuration
    
    This reads from environment variables:
    - OPENAI_API_KEY
    - CLAUDE_API_KEY or ANTHROPIC_API_KEY
    - GEMINI_API_KEY or GOOGLE_API_KEY
    
    Returns:
        List of available providers
    """
    import os
    
    providers = []
    
    # Try OpenAI
    openai_key = os.environ.get('OPENAI_API_KEY')
    if openai_key:
        try:
            config = ProviderConfig(
                name="openai",
                api_key=openai_key,
                model="gpt-4-turbo-preview"
            )
            providers.append(ProviderFactory.create_provider(config))
        except Exception as e:
            logger.warning(f"Failed to create OpenAI provider: {e}")
    
    # Try Claude
    claude_key = os.environ.get('CLAUDE_API_KEY') or os.environ.get('ANTHROPIC_API_KEY')
    if claude_key:
        try:
            config = ProviderConfig(
                name="claude",
                api_key=claude_key,
                model="claude-3-opus-20240229"
            )
            providers.append(ProviderFactory.create_provider(config))
        except Exception as e:
            logger.warning(f"Failed to create Claude provider: {e}")
    
    # Try Gemini
    gemini_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if gemini_key:
        try:
            config = ProviderConfig(
                name="gemini",
                api_key=gemini_key,
                model="gemini-pro"
            )
            providers.append(ProviderFactory.create_provider(config))
        except Exception as e:
            logger.warning(f"Failed to create Gemini provider: {e}")
    
    if not providers:
        logger.warning(
            "No AI providers available. Set OPENAI_API_KEY, CLAUDE_API_KEY, "
            "or GEMINI_API_KEY environment variables."
        )
    
    return providers