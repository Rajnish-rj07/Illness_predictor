"""
Property-based tests for MonitoringService.

Tests universal correctness properties for monitoring using hypothesis.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from datetime import datetime
from src.mlops.monitoring_service import (
    MonitoringService,
    AlertType,
    ALERT_THRESHOLDS
)


# Custom strategies
@st.composite
def prediction_data(draw):
    """Generate valid prediction data."""
    pred_id = f"pred_{draw(st.integers(min_value=0, max_value=10000)):05d}"
    illness = draw(st.sampled_from(["flu", "cold", "covid", "pneumonia", "bronchitis"]))
    confidence = draw(st.floats(min_value=0.3, max_value=1.0))
    latency = draw(st.floats(min_value=50.0, max_value=1000.0))
    features = {"fever": draw(st.floats(min_value=0.0, max_value=1.0))}
    
    return pred_id, illness, confidence, latency, features


class TestProperty48PredictionLoggingCompleteness:
    """
    Property 48: Prediction logging completeness
    
    For any prediction made by the system, all required data should be logged:
    prediction ID, timestamp, features, confidence, and latency.
    
    Validates: Requirements 7.3, 8.2
    """
    
    @given(pred_data=prediction_data())
    @settings(max_examples=20, deadline=None)
    def test_all_predictions_logged_with_required_data(self, pred_data):
        """Test that all predictions are logged with complete data."""
        service = MonitoringService()
        pred_id, illness, confidence, latency, features = pred_data
        
        service.log_prediction(pred_id, illness, confidence, features, latency)
        
        logs = service.get_prediction_logs()
        assert len(logs) == 1
        
        log = logs[0]
        assert log.prediction_id == pred_id
        assert log.predicted_illness == illness
        assert log.confidence == confidence
        assert log.latency_ms == latency
        assert log.features == features
        assert log.timestamp is not None
    
    @given(predictions=st.lists(prediction_data(), min_size=1, max_size=50))
    @settings(max_examples=10, deadline=None)
    def test_all_predictions_are_logged(self, predictions):
        """Test that every prediction is logged."""
        service = MonitoringService()
        
        for pred_id, illness, confidence, latency, features in predictions:
            service.log_prediction(pred_id, illness, confidence, features, latency)
        
        logs = service.get_prediction_logs()
        assert len(logs) == len(predictions)
    
    @given(pred_data=prediction_data())
    @settings(max_examples=20, deadline=None)
    def test_logged_predictions_have_timestamps(self, pred_data):
        """Test that all logged predictions have timestamps."""
        service = MonitoringService()
        pred_id, illness, confidence, latency, features = pred_data
        
        before = datetime.utcnow()
        service.log_prediction(pred_id, illness, confidence, features, latency)
        after = datetime.utcnow()
        
        log = service.get_prediction_logs()[0]
        assert before <= log.timestamp <= after


class TestProperty49MetricDegradationAlerting:
    """
    Property 49: Metric degradation alerting
    
    For any significant drop in accuracy (>5%), the system should generate
    an alert.
    
    Validates: Requirements 7.2
    """
    
    @given(
        baseline=st.floats(min_value=0.80, max_value=0.95),
        drop=st.floats(min_value=0.06, max_value=0.20)
    )
    @settings(max_examples=10, deadline=None)
    def test_accuracy_drop_triggers_alert(self, baseline, drop):
        """Test that accuracy drops trigger alerts."""
        service = MonitoringService()
        service.set_baseline_accuracy(baseline)
        
        # Calculate target accuracy (baseline - drop)
        target_accuracy = baseline - drop
        
        # Log predictions to achieve target accuracy
        total = 20
        correct = int(total * target_accuracy)
        
        for i in range(total):
            pred_id = f"pred_{i:03d}"
            service.log_prediction(
                pred_id, "flu", 0.85, {"fever": 1.0}, 150.0
            )
            actual = "flu" if i < correct else "cold"
            service.update_prediction_feedback(pred_id, actual)
        
        alerts = service.check_thresholds()
        
        # Should have accuracy drop alert
        accuracy_alerts = [a for a in alerts if a.alert_type == AlertType.ACCURACY_DROP]
        assert len(accuracy_alerts) > 0
    
    @given(baseline=st.floats(min_value=0.80, max_value=0.95))
    @settings(max_examples=10, deadline=None)
    def test_no_alert_when_accuracy_stable(self, baseline):
        """Test that stable accuracy doesn't trigger alerts."""
        service = MonitoringService()
        service.set_baseline_accuracy(baseline)
        
        # Log predictions with accuracy close to baseline
        total = 20
        correct = int(total * baseline)
        
        for i in range(total):
            pred_id = f"pred_{i:03d}"
            service.log_prediction(
                pred_id, "flu", 0.85, {"fever": 1.0}, 150.0
            )
            actual = "flu" if i < correct else "cold"
            service.update_prediction_feedback(pred_id, actual)
        
        alerts = service.check_thresholds()
        
        # Should not have accuracy drop alert
        accuracy_alerts = [a for a in alerts if a.alert_type == AlertType.ACCURACY_DROP]
        assert len(accuracy_alerts) == 0
    
    @given(latency=st.floats(min_value=501.0, max_value=1000.0))
    @settings(max_examples=10, deadline=None)
    def test_high_latency_triggers_alert(self, latency):
        """Test that high latency triggers alerts."""
        service = MonitoringService()
        
        # Log predictions with high latency
        for i in range(10):
            service.log_prediction(
                f"pred_{i:03d}", "flu", 0.85, {"fever": 1.0}, latency
            )
        
        alerts = service.check_thresholds()
        
        # Should have latency alert
        latency_alerts = [a for a in alerts if a.alert_type == AlertType.LATENCY_HIGH]
        assert len(latency_alerts) > 0


class TestProperty50PerIllnessMetricsTracking:
    """
    Property 50: Per-illness metrics tracking
    
    For any set of predictions, the system should track separate metrics
    for each illness.
    
    Validates: Requirements 8.4
    """
    
    @given(
        illnesses=st.lists(
            st.sampled_from(["flu", "cold", "covid", "pneumonia"]),
            min_size=1,
            max_size=4,
            unique=True
        )
    )
    @settings(max_examples=10, deadline=None)
    def test_separate_metrics_for_each_illness(self, illnesses):
        """Test that separate metrics exist for each illness."""
        service = MonitoringService()
        
        # Log predictions for each illness
        for illness in illnesses:
            for i in range(5):
                pred_id = f"pred_{illness}_{i:03d}"
                service.log_prediction(
                    pred_id, illness, 0.85, {"fever": 1.0}, 150.0
                )
                service.update_prediction_feedback(pred_id, illness)
        
        per_illness = service.calculate_per_illness_metrics("1h")
        
        # Should have metrics for each illness
        assert len(per_illness) == len(illnesses)
        for illness in illnesses:
            assert illness in per_illness
            assert per_illness[illness].total_predictions > 0
    
    @given(
        illness=st.sampled_from(["flu", "cold", "covid"]),
        n_predictions=st.integers(min_value=5, max_value=20)
    )
    @settings(max_examples=10, deadline=None)
    def test_per_illness_counts_are_accurate(self, illness, n_predictions):
        """Test that per-illness prediction counts are accurate."""
        service = MonitoringService()
        
        # Log predictions for one illness
        for i in range(n_predictions):
            pred_id = f"pred_{i:03d}"
            service.log_prediction(
                pred_id, illness, 0.85, {"fever": 1.0}, 150.0
            )
            service.update_prediction_feedback(pred_id, illness)
        
        per_illness = service.calculate_per_illness_metrics("1h")
        
        assert illness in per_illness
        assert per_illness[illness].total_predictions == n_predictions
    
    @given(
        illness=st.sampled_from(["flu", "cold", "covid"]),
        n_correct=st.integers(min_value=0, max_value=10),
        n_incorrect=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=10, deadline=None)
    def test_per_illness_accuracy_calculation(self, illness, n_correct, n_incorrect):
        """Test that per-illness accuracy is calculated correctly."""
        assume(n_correct + n_incorrect > 0)
        
        service = MonitoringService()
        
        # Log correct predictions (predicted = actual = illness)
        for i in range(n_correct):
            pred_id = f"pred_correct_{i:03d}"
            service.log_prediction(
                pred_id, illness, 0.85, {"fever": 1.0}, 150.0
            )
            service.update_prediction_feedback(pred_id, illness)
        
        # Log incorrect predictions (predicted = illness, actual = other)
        for i in range(n_incorrect):
            pred_id = f"pred_incorrect_{i:03d}"
            service.log_prediction(
                pred_id, "other_illness", 0.85, {"fever": 1.0}, 150.0
            )
            # Actual illness is the one we're testing
            service.update_prediction_feedback(pred_id, illness)
        
        per_illness = service.calculate_per_illness_metrics("1h")
        
        # Metrics are grouped by actual illness
        assert illness in per_illness
        expected_accuracy = n_correct / (n_correct + n_incorrect)
        assert abs(per_illness[illness].accuracy - expected_accuracy) < 0.01


class TestProperty51FeedbackBasedAccuracyComputation:
    """
    Property 51: Feedback-based accuracy computation
    
    For any set of predictions with feedback, the system should compute
    accuracy based on actual outcomes.
    
    Validates: Requirements 8.3, 13.4
    """
    
    @given(
        n_correct=st.integers(min_value=0, max_value=20),
        n_incorrect=st.integers(min_value=0, max_value=20)
    )
    @settings(max_examples=10, deadline=None)
    def test_accuracy_computed_from_feedback(self, n_correct, n_incorrect):
        """Test that accuracy is computed from feedback."""
        assume(n_correct + n_incorrect > 0)
        
        service = MonitoringService()
        
        # Log correct predictions
        for i in range(n_correct):
            pred_id = f"pred_correct_{i:03d}"
            service.log_prediction(
                pred_id, "flu", 0.85, {"fever": 1.0}, 150.0
            )
            service.update_prediction_feedback(pred_id, "flu")
        
        # Log incorrect predictions
        for i in range(n_incorrect):
            pred_id = f"pred_incorrect_{i:03d}"
            service.log_prediction(
                pred_id, "flu", 0.85, {"fever": 1.0}, 150.0
            )
            service.update_prediction_feedback(pred_id, "cold")
        
        metrics = service.calculate_metrics("1h")
        
        expected_accuracy = n_correct / (n_correct + n_incorrect)
        assert metrics.accuracy is not None
        assert abs(metrics.accuracy - expected_accuracy) < 0.01
    
    @given(n_predictions=st.integers(min_value=1, max_value=20))
    @settings(max_examples=10, deadline=None)
    def test_accuracy_none_without_feedback(self, n_predictions):
        """Test that accuracy is None without feedback."""
        service = MonitoringService()
        
        # Log predictions without feedback
        for i in range(n_predictions):
            service.log_prediction(
                f"pred_{i:03d}", "flu", 0.85, {"fever": 1.0}, 150.0
            )
        
        metrics = service.calculate_metrics("1h")
        
        assert metrics.accuracy is None
        assert metrics.total_predictions == n_predictions
    
    @given(
        n_with_feedback=st.integers(min_value=1, max_value=10),
        n_without_feedback=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=10, deadline=None)
    def test_accuracy_only_uses_feedback_predictions(self, n_with_feedback, n_without_feedback):
        """Test that accuracy only uses predictions with feedback."""
        service = MonitoringService()
        
        # Log predictions with feedback (all correct)
        for i in range(n_with_feedback):
            pred_id = f"pred_with_{i:03d}"
            service.log_prediction(
                pred_id, "flu", 0.85, {"fever": 1.0}, 150.0
            )
            service.update_prediction_feedback(pred_id, "flu")
        
        # Log predictions without feedback
        for i in range(n_without_feedback):
            service.log_prediction(
                f"pred_without_{i:03d}", "flu", 0.85, {"fever": 1.0}, 150.0
            )
        
        metrics = service.calculate_metrics("1h")
        
        # Accuracy should be 1.0 (all with feedback are correct)
        assert metrics.accuracy == 1.0
        assert metrics.predictions_with_feedback == n_with_feedback
        assert metrics.total_predictions == n_with_feedback + n_without_feedback


class TestMonitoringServiceInvariants:
    """Test invariants that should always hold for monitoring service."""
    
    @given(predictions=st.lists(prediction_data(), min_size=1, max_size=30))
    @settings(max_examples=10, deadline=None)
    def test_log_count_equals_predictions(self, predictions):
        """Test that log count equals number of predictions."""
        service = MonitoringService()
        
        for pred_id, illness, confidence, latency, features in predictions:
            service.log_prediction(pred_id, illness, confidence, features, latency)
        
        logs = service.get_prediction_logs()
        assert len(logs) == len(predictions)
    
    @given(
        predictions=st.lists(prediction_data(), min_size=5, max_size=20),
        time_window=st.sampled_from(["1h", "24h", "7d"])
    )
    @settings(max_examples=5, deadline=None)
    def test_metrics_total_predictions_consistent(self, predictions, time_window):
        """Test that metrics total predictions is consistent."""
        service = MonitoringService()
        
        for pred_id, illness, confidence, latency, features in predictions:
            service.log_prediction(pred_id, illness, confidence, features, latency)
        
        metrics = service.calculate_metrics(time_window)
        
        # All predictions should be in the time window
        assert metrics.total_predictions == len(predictions)
    
    @given(
        n_predictions=st.integers(min_value=1, max_value=20),
        baseline=st.floats(min_value=0.70, max_value=0.95)
    )
    @settings(max_examples=10, deadline=None)
    def test_baseline_accuracy_persists(self, n_predictions, baseline):
        """Test that baseline accuracy persists across operations."""
        service = MonitoringService()
        service.set_baseline_accuracy(baseline)
        
        # Log some predictions
        for i in range(n_predictions):
            service.log_prediction(
                f"pred_{i:03d}", "flu", 0.85, {"fever": 1.0}, 150.0
            )
        
        # Baseline should still be set
        assert service.baseline_accuracy == baseline
