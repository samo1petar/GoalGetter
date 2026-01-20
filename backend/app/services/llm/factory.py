"""
LLM Service Factory.

Provides a factory pattern for creating and managing LLM service instances.
Supports multiple providers with singleton pattern for efficiency.
"""
from typing import Dict, List, Literal, Optional

from app.core.config import settings
from .base import BaseLLMService

# Type alias for supported providers
LLMProvider = Literal["claude", "openai"]


class LLMServiceFactory:
    """
    Factory for creating and managing LLM service instances.

    Uses singleton pattern to cache service instances for efficiency.
    Supports dynamic provider selection based on configuration.
    """

    _instances: Dict[str, BaseLLMService] = {}

    @classmethod
    def get_service(cls, provider: Optional[LLMProvider] = None) -> BaseLLMService:
        """
        Get or create an LLM service instance for the specified provider.

        Args:
            provider: The LLM provider to use ('claude' or 'openai').
                      If None, uses DEFAULT_LLM_PROVIDER from config.

        Returns:
            BaseLLMService: An instance of the requested provider's service

        Raises:
            ValueError: If the provider is unknown or not configured
        """
        # Use default provider if none specified
        if provider is None:
            provider = cls.get_default_provider()

        if provider not in cls._instances:
            if provider == "claude":
                from .claude_service import ClaudeService
                cls._instances[provider] = ClaudeService()
            elif provider == "openai":
                from .openai_service import OpenAIService
                cls._instances[provider] = OpenAIService()
            else:
                raise ValueError(f"Unknown LLM provider: {provider}")

        service = cls._instances[provider]

        # Verify the service is configured
        if not service.is_configured:
            raise ValueError(
                f"Provider '{provider}' is not configured. "
                f"Please ensure the API key is set in environment variables."
            )

        return service

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """
        Return list of configured providers with valid API keys.

        Returns:
            List[str]: List of provider names that have valid configuration
        """
        providers = []

        if settings.ANTHROPIC_API_KEY:
            providers.append("claude")

        if settings.OPENAI_API_KEY:
            providers.append("openai")

        return providers

    @classmethod
    def get_default_provider(cls) -> LLMProvider:
        """
        Get the default LLM provider based on configuration.

        Returns:
            LLMProvider: The default provider name

        Raises:
            ValueError: If no providers are configured
        """
        available = cls.get_available_providers()

        if not available:
            raise ValueError("No LLM providers are configured")

        # Use configured default if available
        default = getattr(settings, 'DEFAULT_LLM_PROVIDER', 'claude')
        if default in available:
            return default

        # Fall back to first available
        return available[0]

    @classmethod
    def is_provider_available(cls, provider: LLMProvider) -> bool:
        """
        Check if a specific provider is available.

        Args:
            provider: The provider to check

        Returns:
            bool: True if the provider is configured and available
        """
        return provider in cls.get_available_providers()

    @classmethod
    async def close_all(cls) -> None:
        """
        Close all cached service instances.

        Should be called during application shutdown.
        """
        for service in cls._instances.values():
            await service.close()
        cls._instances.clear()

    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear the service instance cache.

        Useful for testing or when configuration changes.
        """
        cls._instances.clear()
