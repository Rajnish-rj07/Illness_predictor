"""
Basic tests to verify project setup and configuration.
"""

import pytest
from config.settings import settings
from src.database.models import SessionModel, PredictionModel, FeedbackModel


@pytest.mark.unit
def test_settings_loaded():
    """Test that settings are loaded correctly."""
    assert settings.app_name == "Illness Prediction System"
    assert settings.app_version == "1.0.0"
    assert settings.max_questions_per_session == 15
    assert settings.prediction_confidence_threshold == 0.30


@pytest.mark.unit
def test_database_url_construction():
    """Test that database URL is constructed correctly."""
    db_url = settings.database_url
    assert "postgresql://" in db_url
    assert settings.postgres_user in db_url
    assert settings.postgres_db in db_url


@pytest.mark.unit
def test_redis_url_construction():
    """Test that Redis URL is constructed correctly."""
    redis_url = settings.redis_url
    assert "redis://" in redis_url
    assert str(settings.redis_port) in redis_url


@pytest.mark.unit
@pytest.mark.requires_db
def test_database_models_creation(test_db_session):
    """Test that database models can be created."""
    # Create a session
    session = SessionModel(
        session_id="test-123",
        user_id="user-456",
        channel="web",
        language="en",
        status="active"
    )
    
    test_db_session.add(session)
    test_db_session.commit()
    
    # Query it back
    retrieved = test_db_session.query(SessionModel).filter_by(session_id="test-123").first()
    assert retrieved is not None
    assert retrieved.user_id == "user-456"
    assert retrieved.channel == "web"


@pytest.mark.unit
def test_supported_languages():
    """Test that supported languages are configured."""
    assert len(settings.supported_languages) == 5
    assert "en" in settings.supported_languages
    assert "es" in settings.supported_languages
    assert "fr" in settings.supported_languages
    assert "hi" in settings.supported_languages
    assert "zh" in settings.supported_languages


@pytest.mark.unit
def test_mlops_configuration():
    """Test that MLOps settings are configured."""
    assert settings.drift_psi_threshold == 0.25
    assert settings.drift_check_window_days == 7
    assert settings.canary_initial_traffic == 0.10
    assert settings.validation_split == 0.2
