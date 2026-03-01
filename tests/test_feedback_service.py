"""
Unit tests for FeedbackService.

Tests specific scenarios, edge cases, and error handling for feedback collection.
"""

import pytest
from datetime import datetime, timedelta
from src.feedback.feedback_service import FeedbackService, FeedbackPrompt, AccuracyMetrics
from src.models.data_models import UserFeedback, SymptomVector, SymptomInfo


class TestFeedbackPromptGeneration:
    """Test feedback prompt generation."""
    
    def test_generate_feedback_prompt_english(self):
        """Test generating feedback prompt in English."""
        service = FeedbackService()
        prompt = service.generate_feedback_prompt('en')
        
        assert isinstance(prompt, FeedbackPrompt)
        assert len(prompt.message) > 0
        assert len(prompt.options) == 3
        assert "prediction" in prompt.message.lower()
    
    def test_generate_feedback_prompt_spanish(self):
        """Test generating feedback prompt in Spanish."""
        service = FeedbackService()
        prompt = service.generate_feedback_prompt('es')
        
        assert isinstance(prompt, FeedbackPrompt)
        assert len(prompt.message) > 0
        assert len(prompt.options) == 3
        assert "predicción" in prompt.message.lower()
    
    def test_generate_feedback_prompt_french(self):
        """Test generating feedback prompt in French."""
        service = FeedbackService()
        prompt = service.generate_feedback_prompt('fr')
        
        assert isinstance(prompt, FeedbackPrompt)
        assert len(prompt.message) > 0
        assert len(prompt.options) == 3
        assert "prédiction" in prompt.message.lower()
    
    def test_generate_feedback_prompt_unsupported_language_defaults_to_english(self):
        """Test that unsupported language defaults to English."""
        service = FeedbackService()
        prompt = service.generate_feedback_prompt('unsupported')
        
        assert isinstance(prompt, FeedbackPrompt)
        assert "prediction" in prompt.message.lower()


class TestFeedbackCollection:
    """Test feedback collection functionality."""
    
    def test_collect_correct_feedback(self):
        """Test collecting feedback for correct prediction."""
        service = FeedbackService()
        
        feedback = service.collect_feedback(
            session_id="session-123",
            prediction_id="pred-456",
            was_correct=True,
            correct_illness="influenza"
        )
        
        assert feedback.session_id == "session-123"
        assert feedback.prediction_id == "pred-456"
        assert feedback.was_correct is True
        assert feedback.correct_illness == "influenza"
        assert isinstance(feedback.timestamp, datetime)
    
    def test_collect_incorrect_feedback(self):
        """Test collecting feedback for incorrect prediction."""
        service = FeedbackService()
        
        feedback = service.collect_feedback(
            session_id="session-123",
            prediction_id="pred-456",
            was_correct=False,
            correct_illness="pneumonia"
        )
        
        assert feedback.was_correct is False
        assert feedback.correct_illness == "pneumonia"
    
    def test_collect_feedback_with_symptom_vector(self):
        """Test collecting feedback with symptom vector context."""
        service = FeedbackService()
        
        symptom_vector = SymptomVector(
            symptoms={
                "fever": SymptomInfo(present=True, severity=8, duration="1-3d"),
                "cough": SymptomInfo(present=True, severity=6, duration="3-7d")
            }
        )
        
        feedback = service.collect_feedback(
            session_id="session-123",
            prediction_id="pred-456",
            was_correct=True,
            correct_illness="influenza",
            symptom_vector=symptom_vector
        )
        
        assert feedback is not None
        assert feedback.was_correct is True
    
    def test_collect_feedback_with_comments(self):
        """Test collecting feedback with additional comments."""
        service = FeedbackService()
        
        feedback = service.collect_feedback(
            session_id="session-123",
            prediction_id="pred-456",
            was_correct=True,
            correct_illness="influenza",
            additional_comments="The prediction was very accurate!"
        )
        
        assert feedback.additional_comments == "The prediction was very accurate!"
    
    def test_collect_feedback_missing_session_id(self):
        """Test that missing session ID raises error."""
        service = FeedbackService()
        
        with pytest.raises(ValueError, match="Session ID is required"):
            service.collect_feedback(
                session_id="",
                prediction_id="pred-456",
                was_correct=True
            )
    
    def test_collect_feedback_missing_prediction_id(self):
        """Test that missing prediction ID raises error."""
        service = FeedbackService()
        
        with pytest.raises(ValueError, match="Prediction ID is required"):
            service.collect_feedback(
                session_id="session-123",
                prediction_id="",
                was_correct=True
            )
    
    def test_collect_incorrect_feedback_without_correct_illness(self):
        """Test that incorrect feedback without correct illness raises error."""
        service = FeedbackService()
        
        with pytest.raises(ValueError, match="Correct illness must be provided"):
            service.collect_feedback(
                session_id="session-123",
                prediction_id="pred-456",
                was_correct=False,
                correct_illness=None
            )


class TestIncorrectPredictionFlagging:
    """Test flagging of incorrect predictions for expert review."""
    
    def test_incorrect_prediction_is_flagged(self):
        """Test that incorrect predictions are flagged for review."""
        service = FeedbackService()
        
        service.collect_feedback(
            session_id="session-123",
            prediction_id="pred-456",
            was_correct=False,
            correct_illness="pneumonia"
        )
        
        flagged = service.get_flagged_cases()
        assert "pred-456" in flagged
    
    def test_correct_prediction_is_not_flagged(self):
        """Test that correct predictions are not flagged."""
        service = FeedbackService()
        
        service.collect_feedback(
            session_id="session-123",
            prediction_id="pred-789",
            was_correct=True,
            correct_illness="influenza"
        )
        
        flagged = service.get_flagged_cases()
        assert "pred-789" not in flagged
    
    def test_multiple_incorrect_predictions_flagged(self):
        """Test that multiple incorrect predictions are all flagged."""
        service = FeedbackService()
        
        service.collect_feedback(
            session_id="session-1",
            prediction_id="pred-1",
            was_correct=False,
            correct_illness="illness-a"
        )
        
        service.collect_feedback(
            session_id="session-2",
            prediction_id="pred-2",
            was_correct=False,
            correct_illness="illness-b"
        )
        
        flagged = service.get_flagged_cases()
        assert len(flagged) == 2
        assert "pred-1" in flagged
        assert "pred-2" in flagged
    
    def test_duplicate_flagging_prevented(self):
        """Test that same prediction is not flagged multiple times."""
        service = FeedbackService()
        
        # Collect feedback twice for same prediction
        service.collect_feedback(
            session_id="session-123",
            prediction_id="pred-456",
            was_correct=False,
            correct_illness="pneumonia"
        )
        
        service.collect_feedback(
            session_id="session-123",
            prediction_id="pred-456",
            was_correct=False,
            correct_illness="pneumonia"
        )
        
        flagged = service.get_flagged_cases()
        # Should only appear once
        assert flagged.count("pred-456") == 1


class TestAccuracyMetricsComputation:
    """Test computation of real-world accuracy metrics."""
    
    def test_compute_accuracy_with_no_feedback(self):
        """Test accuracy computation with no feedback."""
        service = FeedbackService()
        
        metrics = service.compute_accuracy_metrics()
        
        assert metrics.total_feedback_count == 0
        assert metrics.correct_predictions == 0
        assert metrics.incorrect_predictions == 0
        assert metrics.accuracy == 0.0
        assert len(metrics.per_illness_accuracy) == 0
    
    def test_compute_accuracy_with_all_correct(self):
        """Test accuracy computation with all correct predictions."""
        service = FeedbackService()
        
        for i in range(5):
            service.collect_feedback(
                session_id=f"session-{i}",
                prediction_id=f"pred-{i}",
                was_correct=True,
                correct_illness="influenza"
            )
        
        metrics = service.compute_accuracy_metrics()
        
        assert metrics.total_feedback_count == 5
        assert metrics.correct_predictions == 5
        assert metrics.incorrect_predictions == 0
        assert metrics.accuracy == 1.0
    
    def test_compute_accuracy_with_mixed_results(self):
        """Test accuracy computation with mixed correct/incorrect."""
        service = FeedbackService()
        
        # 3 correct
        for i in range(3):
            service.collect_feedback(
                session_id=f"session-{i}",
                prediction_id=f"pred-{i}",
                was_correct=True,
                correct_illness="influenza"
            )
        
        # 2 incorrect
        for i in range(3, 5):
            service.collect_feedback(
                session_id=f"session-{i}",
                prediction_id=f"pred-{i}",
                was_correct=False,
                correct_illness="pneumonia"
            )
        
        metrics = service.compute_accuracy_metrics()
        
        assert metrics.total_feedback_count == 5
        assert metrics.correct_predictions == 3
        assert metrics.incorrect_predictions == 2
        assert metrics.accuracy == 0.6
    
    def test_compute_per_illness_accuracy(self):
        """Test per-illness accuracy computation."""
        service = FeedbackService()
        
        # Influenza: 2 correct, 1 incorrect
        service.collect_feedback(
            session_id="s1", prediction_id="p1",
            was_correct=True, correct_illness="influenza"
        )
        service.collect_feedback(
            session_id="s2", prediction_id="p2",
            was_correct=True, correct_illness="influenza"
        )
        service.collect_feedback(
            session_id="s3", prediction_id="p3",
            was_correct=False, correct_illness="influenza"
        )
        
        # Pneumonia: 1 correct, 0 incorrect
        service.collect_feedback(
            session_id="s4", prediction_id="p4",
            was_correct=True, correct_illness="pneumonia"
        )
        
        metrics = service.compute_accuracy_metrics()
        
        assert "influenza" in metrics.per_illness_accuracy
        assert "pneumonia" in metrics.per_illness_accuracy
        assert metrics.per_illness_accuracy["influenza"] == pytest.approx(2/3, 0.01)
        assert metrics.per_illness_accuracy["pneumonia"] == 1.0
    
    def test_compute_accuracy_with_time_window(self):
        """Test accuracy computation with time window filter."""
        service = FeedbackService()
        
        # Add old feedback (manually set timestamp)
        old_feedback = UserFeedback(
            session_id="old-session",
            prediction_id="old-pred",
            was_correct=True,
            correct_illness="influenza",
            timestamp=datetime.utcnow() - timedelta(days=10)
        )
        service._feedback_storage.append(old_feedback)
        
        # Add recent feedback
        service.collect_feedback(
            session_id="recent-session",
            prediction_id="recent-pred",
            was_correct=True,
            correct_illness="influenza"
        )
        
        # Compute metrics for last 7 days
        metrics = service.compute_accuracy_metrics(time_window='7d')
        
        # Should only include recent feedback
        assert metrics.total_feedback_count == 1
    
    def test_flagged_count_in_metrics(self):
        """Test that flagged count is included in metrics."""
        service = FeedbackService()
        
        service.collect_feedback(
            session_id="s1", prediction_id="p1",
            was_correct=False, correct_illness="pneumonia"
        )
        
        service.collect_feedback(
            session_id="s2", prediction_id="p2",
            was_correct=False, correct_illness="bronchitis"
        )
        
        metrics = service.compute_accuracy_metrics()
        
        assert metrics.flagged_for_review == 2


class TestFeedbackRetrieval:
    """Test feedback retrieval functionality."""
    
    def test_get_feedback_by_session(self):
        """Test retrieving feedback by session ID."""
        service = FeedbackService()
        
        service.collect_feedback(
            session_id="session-123",
            prediction_id="pred-1",
            was_correct=True,
            correct_illness="influenza"
        )
        
        service.collect_feedback(
            session_id="session-123",
            prediction_id="pred-2",
            was_correct=False,
            correct_illness="pneumonia"
        )
        
        service.collect_feedback(
            session_id="session-456",
            prediction_id="pred-3",
            was_correct=True,
            correct_illness="bronchitis"
        )
        
        feedback_list = service.get_feedback_by_session("session-123")
        
        assert len(feedback_list) == 2
        assert all(f.session_id == "session-123" for f in feedback_list)
    
    def test_get_feedback_by_prediction(self):
        """Test retrieving feedback by prediction ID."""
        service = FeedbackService()
        
        service.collect_feedback(
            session_id="session-123",
            prediction_id="pred-456",
            was_correct=True,
            correct_illness="influenza"
        )
        
        feedback = service.get_feedback_by_prediction("pred-456")
        
        assert feedback is not None
        assert feedback.prediction_id == "pred-456"
        assert feedback.correct_illness == "influenza"
    
    def test_get_feedback_by_prediction_not_found(self):
        """Test retrieving non-existent feedback returns None."""
        service = FeedbackService()
        
        feedback = service.get_feedback_by_prediction("non-existent")
        
        assert feedback is None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_session_id_rejected(self):
        """Test that empty session ID is rejected."""
        service = FeedbackService()
        
        with pytest.raises(ValueError):
            service.collect_feedback(
                session_id="",
                prediction_id="pred-123",
                was_correct=True
            )
    
    def test_empty_prediction_id_rejected(self):
        """Test that empty prediction ID is rejected."""
        service = FeedbackService()
        
        with pytest.raises(ValueError):
            service.collect_feedback(
                session_id="session-123",
                prediction_id="",
                was_correct=True
            )
    
    def test_time_window_hours_format(self):
        """Test time window with hours format."""
        service = FeedbackService()
        
        # Add feedback from 2 hours ago
        old_feedback = UserFeedback(
            session_id="old",
            prediction_id="old-pred",
            was_correct=True,
            correct_illness="influenza",
            timestamp=datetime.utcnow() - timedelta(hours=2)
        )
        service._feedback_storage.append(old_feedback)
        
        # Add recent feedback
        service.collect_feedback(
            session_id="recent",
            prediction_id="recent-pred",
            was_correct=True,
            correct_illness="influenza"
        )
        
        # Get metrics for last 1 hour
        metrics = service.compute_accuracy_metrics(time_window='1h')
        
        # Should only include recent feedback
        assert metrics.total_feedback_count == 1
    
    def test_invalid_time_window_format(self):
        """Test that invalid time window format is handled gracefully."""
        service = FeedbackService()
        
        service.collect_feedback(
            session_id="s1",
            prediction_id="p1",
            was_correct=True,
            correct_illness="influenza"
        )
        
        # Invalid format should return all feedback
        metrics = service.compute_accuracy_metrics(time_window='invalid')
        
        assert metrics.total_feedback_count == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
