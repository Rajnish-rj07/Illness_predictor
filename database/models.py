"""
SQLAlchemy database models for the Illness Prediction System.
Defines schemas for sessions, predictions, feedback, and metrics.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, 
    Text, JSON, ForeignKey, Index, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class SessionStatus(str, enum.Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"


class Severity(str, enum.Enum):
    """Illness severity enumeration."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class SessionModel(Base):
    """
    Session table for storing user conversation sessions.
    Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5
    """
    __tablename__ = "sessions"
    
    session_id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)  # Anonymized
    channel = Column(String(50), nullable=False)  # sms, whatsapp, web
    language = Column(String(10), nullable=False, default="en")
    status = Column(SQLEnum(SessionStatus), nullable=False, default=SessionStatus.ACTIVE)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_active = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # JSON fields for complex data
    conversation_context = Column(JSON, nullable=False, default=dict)
    symptom_vector = Column(JSON, nullable=False, default=dict)
    
    # Relationships
    predictions = relationship("PredictionModel", back_populates="session", cascade="all, delete-orphan")
    feedback = relationship("FeedbackModel", back_populates="session", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_session_status_last_active', 'status', 'last_active'),
        Index('idx_session_user_created', 'user_id', 'created_at'),
    )


class PredictionModel(Base):
    """
    Prediction table for storing illness predictions.
    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 7.3, 8.2
    """
    __tablename__ = "predictions"
    
    prediction_id = Column(String(36), primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.session_id"), nullable=False, index=True)
    
    # Prediction details
    illness = Column(String(255), nullable=False, index=True)
    confidence_score = Column(Float, nullable=False)
    severity = Column(SQLEnum(Severity), nullable=False)
    rank = Column(Integer, nullable=False)  # 1, 2, or 3
    
    # Model information
    model_version = Column(String(50), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    
    # Explainability
    shap_values = Column(JSON, nullable=True)
    top_contributors = Column(JSON, nullable=True)  # List of (symptom, contribution)
    explanation_text = Column(Text, nullable=True)
    
    # Treatment suggestions
    medications = Column(JSON, nullable=True)
    non_medication_treatments = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    input_features = Column(JSON, nullable=False)  # Symptom vector at prediction time
    latency_ms = Column(Float, nullable=True)  # Prediction latency
    
    # Relationships
    session = relationship("SessionModel", back_populates="predictions")
    
    # Indexes
    __table_args__ = (
        Index('idx_prediction_illness_created', 'illness', 'created_at'),
        Index('idx_prediction_model_created', 'model_version', 'created_at'),
    )


class FeedbackModel(Base):
    """
    Feedback table for storing user feedback on predictions.
    Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5
    """
    __tablename__ = "feedback"
    
    feedback_id = Column(String(36), primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.session_id"), nullable=False, index=True)
    prediction_id = Column(String(36), nullable=False, index=True)
    
    # Feedback details
    was_correct = Column(Boolean, nullable=False)
    correct_illness = Column(String(255), nullable=True, index=True)
    additional_comments = Column(Text, nullable=True)
    
    # Flagging
    flagged_for_review = Column(Boolean, nullable=False, default=False, index=True)
    reviewed = Column(Boolean, nullable=False, default=False)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    session = relationship("SessionModel", back_populates="feedback")
    
    # Indexes
    __table_args__ = (
        Index('idx_feedback_flagged', 'flagged_for_review', 'reviewed'),
    )


class ModelMetricsModel(Base):
    """
    Model metrics table for tracking ML model performance.
    Validates: Requirements 5.3, 7.1, 7.2, 8.1, 8.4
    """
    __tablename__ = "model_metrics"
    
    metric_id = Column(String(36), primary_key=True, index=True)
    model_version = Column(String(50), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    
    # Overall metrics
    accuracy = Column(Float, nullable=False)
    precision = Column(Float, nullable=False)
    recall = Column(Float, nullable=False)
    f1_score = Column(Float, nullable=False)
    top_3_accuracy = Column(Float, nullable=True)
    
    # Per-class metrics (JSON)
    per_class_metrics = Column(JSON, nullable=True)
    
    # Metadata
    metric_type = Column(String(50), nullable=False)  # validation, production, feedback
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    sample_count = Column(Integer, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_metrics_model_timestamp', 'model_version', 'timestamp'),
        Index('idx_metrics_type_timestamp', 'metric_type', 'timestamp'),
    )


class DriftReportModel(Base):
    """
    Drift report table for tracking data and concept drift.
    Validates: Requirements 7.4, 7.5, 17.1, 17.2, 17.3, 17.4, 17.5
    """
    __tablename__ = "drift_reports"
    
    report_id = Column(String(36), primary_key=True, index=True)
    model_version = Column(String(50), nullable=False, index=True)
    
    # Drift detection
    drift_type = Column(String(50), nullable=False)  # no_drift, feature_drift, concept_drift, both
    drift_detected = Column(Boolean, nullable=False, default=False, index=True)
    
    # Feature drift (PSI scores per feature)
    feature_drifts = Column(JSON, nullable=True)
    max_psi_score = Column(Float, nullable=True)
    
    # Concept drift
    concept_drift_score = Column(Float, nullable=True)
    accuracy_drop = Column(Float, nullable=True)
    
    # Recommendations
    recommendation = Column(Text, nullable=True)
    retraining_recommended = Column(Boolean, nullable=False, default=False, index=True)
    
    # Metadata
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    sample_count = Column(Integer, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_drift_model_timestamp', 'model_version', 'timestamp'),
        Index('idx_drift_detected_timestamp', 'drift_detected', 'timestamp'),
    )


class TrainingRunModel(Base):
    """
    Training run table for tracking model training executions.
    Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5
    """
    __tablename__ = "training_runs"
    
    run_id = Column(String(36), primary_key=True, index=True)
    model_version = Column(String(50), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    
    # Training status
    status = Column(String(50), nullable=False, index=True)  # running, completed, failed
    
    # Dataset information
    dataset_path = Column(String(500), nullable=False)
    dataset_size = Column(Integer, nullable=False)
    validation_size = Column(Integer, nullable=False)
    
    # Hyperparameters
    hyperparameters = Column(JSON, nullable=False)
    
    # Results
    training_metrics = Column(JSON, nullable=True)
    validation_metrics = Column(JSON, nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # Metadata
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # MLflow integration
    mlflow_run_id = Column(String(100), nullable=True, index=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_training_status_started', 'status', 'started_at'),
    )
