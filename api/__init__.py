"""API module for the Illness Prediction System."""

from src.api.app import app, rate_limiter, verify_api_key

__all__ = ['app', 'rate_limiter', 'verify_api_key']
