"""
AI Provider service — manages LLM instantiation and API key encryption.

Supports: OpenAI, Anthropic, Groq, Mistral, OpenRouter, Ollama.
"""

import time
from typing import Any

from cryptography.fernet import Fernet
from langchain_core.language_models import BaseChatModel

from app.core.config import settings
from app.core.exceptions import AIProviderError
from app.core.logging import get_logger
from app.schemas.user import AIProviderTestResponse

logger = get_logger(__name__)

# Derive a valid 32-byte Fernet key from SECRET_KEY using SHA-256.
# Fernet expects exactly 32 url-safe base64-encoded bytes (44 chars with padding).
import base64
import hashlib
_raw_key = hashlib.sha256(settings.secret_key.encode()).digest()  # always 32 bytes
_FERNET_KEY = base64.urlsafe_b64encode(_raw_key)                 # always 44 chars
_fernet = Fernet(_FERNET_KEY)


class ProviderService:
    """
    Factory for LangChain-compatible LLM instances.

    Handles:
    - Provider-specific LLM instantiation
    - API key encryption/decryption
    - Connection testing
    """

    @staticmethod
    def encrypt_api_key(plain_key: str) -> str:
        """Encrypts a plain-text API key using Fernet symmetric encryption."""
        return _fernet.encrypt(plain_key.encode()).decode()

    @staticmethod
    def decrypt_api_key(encrypted_key: str) -> str:
        """Decrypts a Fernet-encrypted API key."""
        return _fernet.decrypt(encrypted_key.encode()).decode()

    @staticmethod
    def get_llm(
        provider: str,
        model: str,
        api_key: str,
        base_url: str = "",
        temperature: float = settings.llm_temperature,
    ) -> BaseChatModel:
        """
        Instantiates a LangChain LLM for the given provider.

        Args:
            provider:    Provider name (openai, anthropic, groq, mistral, openrouter, ollama).
            model:       Model identifier (e.g. gpt-4o, claude-3-5-sonnet-20241022).
            api_key:     Plain-text API key (pre-decrypted).
            temperature: LLM temperature (default 0.1 for consistent outputs).

        Returns:
            LangChain BaseChatModel instance.

        Raises:
            AIProviderError: Provider not supported or initialization failed.
        """
        try:
            match provider:
                case "openai":
                    from langchain_openai import ChatOpenAI
                    return ChatOpenAI(
                        model=model,
                        api_key=api_key,
                        temperature=temperature,
                    )

                case "anthropic":
                    from langchain_anthropic import ChatAnthropic
                    return ChatAnthropic(
                        model=model,
                        api_key=api_key,
                        temperature=temperature,
                    )

                case "groq":
                    from langchain_groq import ChatGroq
                    return ChatGroq(
                        model=model,
                        api_key=api_key,
                        temperature=temperature,
                    )

                case "mistral":
                    from langchain_mistralai import ChatMistralAI
                    return ChatMistralAI(
                        model=model,
                        api_key=api_key,
                        temperature=temperature,
                    )

                case "openrouter":
                    from langchain_openai import ChatOpenAI
                    return ChatOpenAI(
                        model=model,
                        api_key=api_key,
                        base_url="https://openrouter.ai/api/v1",
                        temperature=temperature,
                    )

                case "ollama":
                    from langchain_ollama import ChatOllama
                    return ChatOllama(
                        model=model,
                        temperature=temperature,
                        base_url=base_url or "http://localhost:11434",
                    )

                case _:
                    raise AIProviderError(
                        provider=provider,
                        detail=f"Unsupported provider '{provider}'",
                    )

        except AIProviderError:
            raise
        except Exception as exc:
            raise AIProviderError(
                provider=provider,
                detail=f"Failed to initialize {provider} LLM: {exc}",
            ) from exc

    @staticmethod
    async def test_provider(user: Any) -> AIProviderTestResponse:
        """
        Tests the connection to the user's configured AI provider.

        Sends a minimal request to verify the API key and model are valid.

        Args:
            user: User ORM instance with ai_provider, ai_model, ai_api_key_encrypted.

        Returns:
            AIProviderTestResponse with success status and latency.
        """
        provider: str = user.ai_provider
        model: str = user.ai_model

        try:
            api_key = ""
            if user.ai_api_key_encrypted:
                api_key = ProviderService.decrypt_api_key(user.ai_api_key_encrypted)

            llm = ProviderService.get_llm(provider, model, api_key)

            start = time.monotonic()
            await llm.ainvoke("Say 'OK' in one word.")
            latency_ms = int((time.monotonic() - start) * 1000)

            logger.info(
                "Provider test successful",
                extra={"provider": provider, "model": model, "latency_ms": latency_ms},
            )

            return AIProviderTestResponse(
                success=True,
                provider=provider,
                model=model,
                message=f"Connection successful ({latency_ms}ms)",
                latency_ms=latency_ms,
            )

        except Exception as exc:
            logger.warning(
                "Provider test failed",
                exc_info=exc,
                extra={"provider": provider, "model": model},
            )
            return AIProviderTestResponse(
                success=False,
                provider=provider,
                model=model,
                message=str(exc),
            )
