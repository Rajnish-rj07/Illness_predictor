"""
Unit tests for LLM client wrapper.
Tests circuit breaker, retry logic, and response parsing.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
import httpx

from src.llm.llm_client import (
    LLMClient,
    LLMResponse,
    CircuitBreaker,
    CircuitBreakerOpenError,
    LLMError,
    LLMTimeoutError,
    LLMValidationError,
    LLMProvider,
)


class TestCircuitBreaker:
    """Test circuit breaker pattern implementation."""
    
    def test_circuit_breaker_initial_state(self):
        """Circuit breaker should start in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=3, timeout=60)
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
    
    def test_circuit_breaker_opens_after_threshold(self):
        """Circuit breaker should open after failure threshold reached."""
        cb = CircuitBreaker(failure_threshold=3, timeout=60)
        
        def failing_func():
            raise Exception("Test failure")
        
        # Trigger failures
        for _ in range(3):
            with pytest.raises(Exception):
                cb.call(failing_func)
        
        # Circuit should be open
        assert cb.state == "OPEN"
        
        # Next call should raise CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(failing_func)
    
    def test_circuit_breaker_resets_on_success(self):
        """Circuit breaker should reset failure count on success."""
        cb = CircuitBreaker(failure_threshold=3, timeout=60)
        
        def failing_func():
            raise Exception("Test failure")
        
        def success_func():
            return "success"
        
        # Trigger some failures
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(failing_func)
        
        assert cb.failure_count == 2
        
        # Success should reset count
        result = cb.call(success_func)
        assert result == "success"
        assert cb.failure_count == 0
    
    def test_circuit_breaker_half_open_transition(self):
        """Circuit breaker should transition to HALF_OPEN after timeout."""
        import time
        
        cb = CircuitBreaker(failure_threshold=2, timeout=1)
        
        def failing_func():
            raise Exception("Test failure")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(failing_func)
        
        assert cb.state == "OPEN"
        
        # Wait for timeout
        time.sleep(1.1)
        
        # Next call should transition to HALF_OPEN
        def success_func():
            return "success"
        
        result = cb.call(success_func)
        assert result == "success"
        assert cb.state == "CLOSED"
    
    def test_circuit_breaker_manual_reset(self):
        """Circuit breaker should support manual reset."""
        cb = CircuitBreaker(failure_threshold=2, timeout=60)
        
        def failing_func():
            raise Exception("Test failure")
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                cb.call(failing_func)
        
        assert cb.state == "OPEN"
        
        # Manual reset
        cb.reset()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0


class TestLLMClient:
    """Test LLM client functionality."""
    
    def test_llm_client_initialization(self):
        """LLM client should initialize with correct defaults."""
        client = LLMClient(
            provider="openai",
            api_key="test-key",
            model="gpt-4",
        )
        
        assert client.provider == LLMProvider.OPENAI
        assert client.api_key == "test-key"
        assert client.model == "gpt-4"
        assert client.circuit_breaker is not None
    
    def test_parse_openai_response(self):
        """Should correctly parse OpenAI API response."""
        client = LLMClient(provider="openai", api_key="test-key")
        
        raw_response = {
            "choices": [
                {
                    "message": {
                        "content": "Test response"
                    },
                    "finish_reason": "stop"
                }
            ],
            "model": "gpt-4",
            "usage": {
                "total_tokens": 100
            }
        }
        
        response = client._parse_openai_response(raw_response)
        
        assert response.content == "Test response"
        assert response.provider == "openai"
        assert response.model == "gpt-4"
        assert response.tokens_used == 100
        assert response.finish_reason == "stop"
    
    def test_parse_anthropic_response(self):
        """Should correctly parse Anthropic API response."""
        client = LLMClient(provider="anthropic", api_key="test-key")
        
        raw_response = {
            "content": [
                {
                    "text": "Test response"
                }
            ],
            "model": "claude-3",
            "usage": {
                "output_tokens": 50
            },
            "stop_reason": "end_turn"
        }
        
        response = client._parse_anthropic_response(raw_response)
        
        assert response.content == "Test response"
        assert response.provider == "anthropic"
        assert response.model == "claude-3"
        assert response.tokens_used == 50
        assert response.finish_reason == "end_turn"
    
    def test_parse_response_invalid_format(self):
        """Should raise LLMValidationError for invalid response format."""
        client = LLMClient(provider="openai", api_key="test-key")
        
        # Missing required fields
        invalid_response = {"invalid": "data"}
        
        with pytest.raises(LLMValidationError):
            client._parse_response(invalid_response)
    
    @pytest.mark.asyncio
    async def test_openai_request_success(self):
        """Should successfully make OpenAI API request."""
        client = LLMClient(provider="openai", api_key="test-key")
        
        mock_response = {
            "choices": [
                {
                    "message": {"content": "Test response"},
                    "finish_reason": "stop"
                }
            ],
            "model": "gpt-4",
            "usage": {"total_tokens": 100}
        }
        
        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_resp = Mock()
            mock_resp.json = Mock(return_value=mock_response)
            mock_resp.raise_for_status = Mock()
            mock_post.return_value = mock_resp
            
            messages = [{"role": "user", "content": "Test"}]
            response = await client._openai_request(messages)
            
            assert response == mock_response
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_request_timeout(self):
        """Should raise LLMTimeoutError on timeout."""
        client = LLMClient(provider="openai", api_key="test-key", timeout=1)
        
        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Timeout")
            
            messages = [{"role": "user", "content": "Test"}]
            
            with pytest.raises(LLMTimeoutError):
                await client._make_request(messages)
    
    @pytest.mark.asyncio
    async def test_request_http_error(self):
        """Should raise LLMError on HTTP error."""
        client = LLMClient(provider="openai", api_key="test-key")
        
        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            
            error = httpx.HTTPStatusError(
                "Error", request=Mock(), response=mock_response
            )
            
            mock_resp = Mock()
            mock_resp.raise_for_status = Mock(side_effect=error)
            mock_post.return_value = mock_resp
            
            messages = [{"role": "user", "content": "Test"}]
            
            with pytest.raises(LLMError):
                await client._make_request(messages)
    
    @pytest.mark.asyncio
    async def test_generate_json_success(self):
        """Should successfully generate and parse JSON response."""
        client = LLMClient(provider="openai", api_key="test-key")
        
        json_content = {"symptom": "fever", "severity": 8}
        mock_response = {
            "choices": [
                {
                    "message": {"content": json.dumps(json_content)},
                    "finish_reason": "stop"
                }
            ],
            "model": "gpt-4",
            "usage": {"total_tokens": 50}
        }
        
        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_resp = Mock()
            mock_resp.json = Mock(return_value=mock_response)
            mock_resp.raise_for_status = Mock()
            mock_post.return_value = mock_resp
            
            result = await client.generate_json("Extract symptoms")
            
            assert result == json_content
    
    @pytest.mark.asyncio
    async def test_generate_json_invalid(self):
        """Should raise LLMValidationError for invalid JSON."""
        client = LLMClient(provider="openai", api_key="test-key")
        
        mock_response = {
            "choices": [
                {
                    "message": {"content": "Not valid JSON"},
                    "finish_reason": "stop"
                }
            ],
            "model": "gpt-4",
            "usage": {"total_tokens": 50}
        }
        
        with patch.object(client.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = Mock()
            
            with pytest.raises(LLMValidationError):
                await client.generate_json("Extract symptoms")


class TestLLMResponse:
    """Test LLMResponse dataclass."""
    
    def test_llm_response_creation(self):
        """Should create LLMResponse with all fields."""
        response = LLMResponse(
            content="Test content",
            raw_response={"test": "data"},
            provider="openai",
            model="gpt-4",
            tokens_used=100,
            finish_reason="stop"
        )
        
        assert response.content == "Test content"
        assert response.provider == "openai"
        assert response.model == "gpt-4"
        assert response.tokens_used == 100
        assert response.finish_reason == "stop"
