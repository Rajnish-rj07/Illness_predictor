"""
LLM Client wrapper with retry logic and circuit breaker pattern.
Supports OpenAI and Anthropic APIs.
"""

import time
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from config.settings import settings

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""
    pass


class LLMValidationError(LLMError):
    """Raised when LLM response validation fails."""
    pass


@dataclass
class LLMResponse:
    """Structured LLM response."""
    content: str
    raw_response: Dict[str, Any]
    provider: str
    model: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for LLM API calls.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are blocked
    - HALF_OPEN: Testing if service recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        half_open_attempts: int = 1
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting recovery
            half_open_attempts: Number of successful attempts needed to close circuit
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_attempts = half_open_attempts
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        logger.info(
            f"Circuit breaker initialized: threshold={failure_threshold}, "
            f"timeout={timeout}s"
        )
    
    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                self.state = "HALF_OPEN"
                self.success_count = 0
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. "
                    f"Retry after {self.timeout - (time.time() - self.last_failure_time):.0f}s"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful call."""
        if self.state == "HALF_OPEN":
            self.success_count += 1
            if self.success_count >= self.half_open_attempts:
                logger.info("Circuit breaker CLOSED after successful recovery")
                self.state = "CLOSED"
                self.failure_count = 0
        elif self.state == "CLOSED":
            # Reset failure count on success
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == "HALF_OPEN":
            logger.warning("Circuit breaker reopening after failed recovery attempt")
            self.state = "OPEN"
        elif self.failure_count >= self.failure_threshold:
            logger.error(
                f"Circuit breaker OPENED after {self.failure_count} failures"
            )
            self.state = "OPEN"
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        logger.info("Circuit breaker manually reset")
        self.state = "CLOSED"
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None


class LLMClient:
    """
    LLM client wrapper with retry logic and circuit breaker.
    Supports OpenAI and Anthropic APIs.
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
    ):
        """
        Initialize LLM client.
        
        Args:
            provider: LLM provider (openai, anthropic). Defaults to settings.
            api_key: API key. Defaults to settings.
            model: Model name. Defaults to settings.
            temperature: Sampling temperature. Defaults to settings.
            max_tokens: Maximum tokens in response. Defaults to settings.
            timeout: Request timeout in seconds. Defaults to settings.
        """
        self.provider = LLMProvider(provider or settings.llm_provider)
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.temperature = temperature if temperature is not None else settings.llm_temperature
        self.max_tokens = max_tokens or settings.llm_max_tokens
        self.timeout = timeout or settings.llm_timeout
        
        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=60,
            half_open_attempts=1
        )
        
        # HTTP client
        self.client = httpx.AsyncClient(timeout=self.timeout)
        
        logger.info(
            f"LLM client initialized: provider={self.provider.value}, "
            f"model={self.model}"
        )
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True
    )
    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request to LLM API with retry logic.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters for the API
            
        Returns:
            Raw API response
            
        Raises:
            LLMTimeoutError: If request times out
            LLMError: If API returns error
        """
        try:
            if self.provider == LLMProvider.OPENAI:
                return await self._openai_request(messages, **kwargs)
            elif self.provider == LLMProvider.ANTHROPIC:
                return await self._anthropic_request(messages, **kwargs)
            else:
                raise LLMError(f"Unsupported provider: {self.provider}")
        except httpx.TimeoutException as e:
            logger.error(f"LLM request timeout: {e}")
            raise LLMTimeoutError(f"Request timed out after {self.timeout}s") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API error: {e.response.status_code} - {e.response.text}")
            raise LLMError(f"API error: {e.response.status_code}") from e
    
    async def _openai_request(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Make request to OpenAI API."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }
        
        # Add response format if specified
        if "response_format" in kwargs:
            payload["response_format"] = kwargs["response_format"]
        
        response = await self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    
    async def _anthropic_request(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """Make request to Anthropic API."""
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }
        
        response = await self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    
    def _parse_response(self, raw_response: Dict[str, Any]) -> LLMResponse:
        """
        Parse raw API response into structured format.
        
        Args:
            raw_response: Raw API response
            
        Returns:
            Structured LLMResponse
            
        Raises:
            LLMValidationError: If response format is invalid
        """
        try:
            if self.provider == LLMProvider.OPENAI:
                return self._parse_openai_response(raw_response)
            elif self.provider == LLMProvider.ANTHROPIC:
                return self._parse_anthropic_response(raw_response)
            else:
                raise LLMError(f"Unsupported provider: {self.provider}")
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise LLMValidationError(f"Invalid response format: {e}") from e
    
    def _parse_openai_response(self, raw_response: Dict[str, Any]) -> LLMResponse:
        """Parse OpenAI API response."""
        choice = raw_response["choices"][0]
        content = choice["message"]["content"]
        
        return LLMResponse(
            content=content,
            raw_response=raw_response,
            provider=self.provider.value,
            model=raw_response.get("model", self.model),
            tokens_used=raw_response.get("usage", {}).get("total_tokens"),
            finish_reason=choice.get("finish_reason"),
        )
    
    def _parse_anthropic_response(self, raw_response: Dict[str, Any]) -> LLMResponse:
        """Parse Anthropic API response."""
        content = raw_response["content"][0]["text"]
        
        return LLMResponse(
            content=content,
            raw_response=raw_response,
            provider=self.provider.value,
            model=raw_response.get("model", self.model),
            tokens_used=raw_response.get("usage", {}).get("output_tokens"),
            finish_reason=raw_response.get("stop_reason"),
        )
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion from prompt.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            LLMResponse with generated content
            
        Raises:
            CircuitBreakerOpenError: If circuit breaker is open
            LLMError: If generation fails
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        # Use circuit breaker to protect API calls
        raw_response = self.circuit_breaker.call(
            self._make_request_sync,
            messages,
            **kwargs
        )
        
        return self._parse_response(raw_response)
    
    def _make_request_sync(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Synchronous wrapper for async request (for circuit breaker)."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._make_request(messages, **kwargs))
    
    async def generate_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Async version of generate.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse with generated content
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        raw_response = await self._make_request(messages, **kwargs)
        return self._parse_response(raw_response)
    
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate JSON response from prompt.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional parameters
            
        Returns:
            Parsed JSON response
            
        Raises:
            LLMValidationError: If response is not valid JSON
        """
        # For OpenAI, use JSON mode
        if self.provider == LLMProvider.OPENAI:
            kwargs["response_format"] = {"type": "json_object"}
            
            # Ensure prompt mentions JSON
            if "json" not in prompt.lower():
                prompt += "\n\nRespond with valid JSON."
        
        response = await self.generate_async(prompt, system_prompt, **kwargs)
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise LLMValidationError(f"Invalid JSON response: {e}") from e
