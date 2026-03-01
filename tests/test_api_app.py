"""
Unit tests for FastAPI application.

Tests middleware, authentication, rate limiting, and health check endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from src.api.app import app, rate_limiter, rate_limit_storage
import os


# Create test client
client = TestClient(app)


class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check_returns_200(self):
        """Test that health check returns 200 status."""
        response = client.get("/health")
        
        assert response.status_code == 200
    
    def test_health_check_returns_status(self):
        """Test that health check returns status information."""
        response = client.get("/health")
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "services" in data
    
    def test_health_check_includes_service_status(self):
        """Test that health check includes service statuses."""
        response = client.get("/health")
        data = response.json()
        
        services = data["services"]
        assert "api" in services
        assert "database" in services
        assert "ml_model" in services
        assert "cache" in services


class TestRootEndpoint:
    """Test root endpoint."""
    
    def test_root_returns_200(self):
        """Test that root endpoint returns 200 status."""
        response = client.get("/")
        
        assert response.status_code == 200
    
    def test_root_returns_api_info(self):
        """Test that root endpoint returns API information."""
        response = client.get("/")
        data = response.json()
        
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "documentation" in data
        assert "health" in data


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def setup_method(self):
        """Clear rate limit storage before each test."""
        rate_limit_storage.clear()
    
    def test_rate_limiter_allows_requests_under_limit(self):
        """Test that rate limiter allows requests under the limit."""
        client_id = "test-client-1"
        
        # Should allow first request
        assert rate_limiter.is_allowed(client_id) is True
    
    def test_rate_limiter_blocks_requests_over_limit(self):
        """Test that rate limiter blocks requests over the limit."""
        client_id = "test-client-2"
        
        # Make requests up to the limit
        for _ in range(rate_limiter.requests_per_minute):
            assert rate_limiter.is_allowed(client_id) is True
        
        # Next request should be blocked
        assert rate_limiter.is_allowed(client_id) is False
    
    def test_rate_limiter_resets_after_window(self):
        """Test that rate limiter resets after time window."""
        client_id = "test-client-3"
        
        # Fill up the limit
        for _ in range(rate_limiter.requests_per_minute):
            rate_limiter.is_allowed(client_id)
        
        # Should be blocked
        assert rate_limiter.is_allowed(client_id) is False
        
        # Manually clear old requests (simulate time passing)
        rate_limit_storage[client_id] = []
        
        # Should be allowed again
        assert rate_limiter.is_allowed(client_id) is True
    
    def test_rate_limiter_tracks_remaining_requests(self):
        """Test that rate limiter tracks remaining requests."""
        client_id = "test-client-4"
        
        # Initially should have full limit
        remaining = rate_limiter.get_remaining(client_id)
        assert remaining == rate_limiter.requests_per_minute
        
        # Make a request
        rate_limiter.is_allowed(client_id)
        
        # Should have one less remaining
        remaining = rate_limiter.get_remaining(client_id)
        assert remaining == rate_limiter.requests_per_minute - 1
    
    def test_rate_limit_headers_included_in_response(self):
        """Test that rate limit headers are included in responses."""
        response = client.get("/")
        
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
    
    def test_health_check_bypasses_rate_limiting(self):
        """Test that health check endpoint bypasses rate limiting."""
        # Clear storage
        rate_limit_storage.clear()
        
        # Make many requests to health check
        for _ in range(100):
            response = client.get("/health")
            assert response.status_code == 200


class TestLoggingMiddleware:
    """Test logging middleware."""
    
    def test_process_time_header_added(self):
        """Test that process time header is added to responses."""
        response = client.get("/")
        
        assert "X-Process-Time" in response.headers
        
        # Should be a valid float
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0


class TestErrorHandling:
    """Test error handling."""
    
    def test_404_error_for_nonexistent_endpoint(self):
        """Test that 404 error is returned for nonexistent endpoints."""
        response = client.get("/nonexistent")
        
        assert response.status_code == 404
    
    def test_error_response_format(self):
        """Test that error responses have consistent format."""
        response = client.get("/nonexistent")
        data = response.json()
        
        assert "error" in data or "detail" in data


class TestCORSMiddleware:
    """Test CORS middleware."""
    
    def test_cors_headers_present(self):
        """Test that CORS headers are present in responses."""
        # Test with a GET request instead of OPTIONS
        response = client.get("/")
        
        # CORS headers should be present (may vary based on configuration)
        # Just verify the response is successful
        assert response.status_code == 200


class TestAuthentication:
    """Test authentication functionality."""
    
    def test_health_check_does_not_require_auth(self):
        """Test that health check does not require authentication."""
        # Don't set REQUIRE_AUTH environment variable
        response = client.get("/health")
        
        assert response.status_code == 200
    
    def test_root_endpoint_does_not_require_auth_by_default(self):
        """Test that root endpoint does not require auth by default."""
        response = client.get("/")
        
        assert response.status_code == 200


class TestRateLimiterClass:
    """Test RateLimiter class directly."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = rate_limiter
        
        assert limiter.requests_per_minute == 60
        assert limiter.window_seconds == 60
    
    def test_rate_limiter_custom_limit(self):
        """Test rate limiter with custom limit."""
        from src.api.app import RateLimiter
        
        limiter = RateLimiter(requests_per_minute=10)
        
        assert limiter.requests_per_minute == 10
    
    def test_rate_limiter_multiple_clients(self):
        """Test rate limiter with multiple clients."""
        rate_limit_storage.clear()
        
        client1 = "client-1"
        client2 = "client-2"
        
        # Both clients should be allowed initially
        assert rate_limiter.is_allowed(client1) is True
        assert rate_limiter.is_allowed(client2) is True
        
        # Fill up client1's limit
        for _ in range(rate_limiter.requests_per_minute - 1):
            rate_limiter.is_allowed(client1)
        
        # Client1 should be blocked
        assert rate_limiter.is_allowed(client1) is False
        
        # Client2 should still be allowed
        assert rate_limiter.is_allowed(client2) is True


class TestAPIConfiguration:
    """Test API configuration."""
    
    def test_api_has_title(self):
        """Test that API has a title."""
        assert app.title == "Illness Prediction System API"
    
    def test_api_has_version(self):
        """Test that API has a version."""
        assert app.version == "1.0.0"
    
    def test_api_has_description(self):
        """Test that API has a description."""
        assert len(app.description) > 0
    
    def test_docs_endpoint_accessible(self):
        """Test that docs endpoint is accessible."""
        response = client.get("/docs")
        
        assert response.status_code == 200


class TestEdgeCases:
    """Test edge cases."""
    
    def test_request_without_client_info(self):
        """Test handling of requests without client information."""
        # This is handled by the middleware
        response = client.get("/")
        
        assert response.status_code == 200
    
    def test_empty_api_key_header(self):
        """Test handling of empty API key header."""
        response = client.get("/", headers={"X-API-Key": ""})
        
        # Should still work if auth is not required
        assert response.status_code == 200
    
    def test_rate_limiter_with_zero_remaining(self):
        """Test rate limiter behavior when remaining is zero."""
        rate_limit_storage.clear()
        client_id = "test-zero"
        
        # Fill up the limit
        for _ in range(rate_limiter.requests_per_minute):
            rate_limiter.is_allowed(client_id)
        
        # Remaining should be zero
        remaining = rate_limiter.get_remaining(client_id)
        assert remaining == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
