"""
Unit tests for MonitoringService.

Tests prediction logging, metrics calculation, alerting, and reporting functionality.
"""

import pytest
from datetime import datetime, timedelta
from src.mlops.monitoring_service import (
    MonitoringService,
    AlertType,
    ALERT_THRESHOLDS
)


class TestPredictionLogging:
    """Tests for prediction logging functionality."""
    
    def test_log_prediction(self):
        """Test logging a single prediction."""
        service = MonitoringService()
        
        service.log_prediction(
            prediction_id="pred_001",
            predicted_illness="flu",
            confidence=0.85,
            features={"fever": 1.0, "cough": 1.0},
            latency_ms=150.0
        )
        
        logs = service.get_prediction_logs()
        assert len(logs) == 1
        assert logs[0].prediction_id == "pred_001"
        assert logs[0].predicted_illness == "flu"
        assert logs[0].confidence == 0.85
        assert logs[0].latency_ms == 150.0
    
    def test_log_multiple_predictions(self):
        """Test logging multiple predictions."""
        service = MonitoringService()
        
        for i in range(10):
            service.log_prediction(
                prediction_id=f"pred_{i:03d}",
                predicted_illness="flu",
                confidence=0.8 + i * 0.01,
                features={"fever": 1.0},
                latency_ms=100.0 + i * 10
            )
        
        logs = service.get_prediction_logs()
        assert len(logs) == 10
    
    def test_get_prediction_logs_with_limit(self):
        """Test getting limited number of logs."""
        service = MonitoringService()
        
        for i in range(20):
            service.log_prediction(
                prediction_id=f"pred_{i:03d}",
                predicted_illness="flu",
                confidence=0.85,
                features={"fever": 1.0},
                latency_ms=150.0
            )
        
        logs = service.get_prediction_logs(limit=5)
        assert len(logs) == 5
        # Should get most recent
        assert logs[-1].prediction_id == "pred_019"


class TestFeedbackUpdate:
    """Tests for feedback update functionality."""
    
    def test_update_prediction_feedback(self):
        """Test updating prediction with feedback."""
        service = MonitoringService()
        
        service.log_prediction(
            prediction_id="pred_001",
            predicted_illness="flu",
            confidence=0.85,
            features={"fever": 1.0},
            latency_ms=150.0
        )
        
        service.update_prediction_feedback("pred_001", "cold")
        
        logs = service.get_prediction_logs()
        assert logs[0].actual_illness == "cold"
    
    def test_update_non_existent_prediction(self):
        """Test updating non-existent prediction logs warning."""
        service = MonitoringService()
        
        # Should not raise error, just log warning
        service.update_prediction_feedback("pred_999", "flu")


class TestMetricsCalculation:
    """Tests for metrics calculation functionality."""
    
    def test_calculate_metrics_empty(self):
        """Test calculating metrics with no data."""
        service = MonitoringService()
        
        metrics = service.calculate_metrics("1h")
        
        assert metrics.total_predictions == 0
        assert metrics.accuracy is None
    
    def test_calculate_metrics_without_feedback(self):
        """Test calculating metrics without feedback."""
        service = MonitoringService()
        
        for i in range(10):
            service.log_prediction(
                prediction_id=f"pred_{i:03d}",
                predicted_illness="flu",
                confidence=0.85,
                features={"fever": 1.0},
                latency_ms=150.0
            )
        
        metrics = service.calculate_metrics("1h")
        
        assert metrics.total_predictions == 10
        assert metrics.accuracy is None  # No feedback yet
        assert metrics.confidence_mean > 0
        assert metrics.latency_p95 > 0
    
    def test_calculate_metrics_with_feedback(self):
        """Test calculating metrics with feedback."""
        service = MonitoringService()
        
        # Log predictions
        for i in range(10):
            service.log_prediction(
                prediction_id=f"pred_{i:03d}",
                predicted_illness="flu",
                confidence=0.85,
                features={"fever": 1.0},
                latency_ms=150.0
            )
        
        # Add feedback (8 correct, 2 incorrect)
        for i in range(8):
            service.update_prediction_feedback(f"pred_{i:03d}", "flu")
        for i in range(8, 10):
            service.update_prediction_feedback(f"pred_{i:03d}", "cold")
        
        metrics = service.calculate_metrics("1h")
        
        assert metrics.total_predictions == 10
        assert metrics.predictions_with_feedback == 10
        assert metrics.accuracy == 0.8  # 8/10 correct
        assert metrics.top_3_accuracy is not None
    
    def test_calculate_latency_percentiles(self):
        """Test latency percentile calculations."""
        service = MonitoringService()
        
        # Log predictions with varying latencies
        latencies = [100, 150, 200, 250, 300, 350, 400, 450, 500, 1000]
        for i, latency in enumerate(latencies):
            service.log_prediction(
                prediction_id=f"pred_{i:03d}",
                predicted_illness="flu",
                confidence=0.85,
                features={"fever": 1.0},
                latency_ms=latency
            )
        
        metrics = service.calculate_metrics("1h")
        
        assert metrics.latency_p50 > 0
        assert metrics.latency_p95 > metrics.latency_p50
        assert metrics.latency_p99 > metrics.latency_p95


class TestPerIllnessMetrics:
    """Tests for per-illness metrics calculation."""
    
    def test_calculate_per_illness_metrics(self):
        """Test calculating metrics per illness."""
        service = MonitoringService()
        
        # Log predictions for different illnesses
        illnesses = ["flu", "cold", "covid"]
        for illness in illnesses:
            for i in range(5):
                pred_id = f"pred_{illness}_{i:03d}"
                service.log_prediction(
                    prediction_id=pred_id,
                    predicted_illness=illness,
                    confidence=0.85,
                    features={"fever": 1.0},
                    latency_ms=150.0
                )
                service.update_prediction_feedback(pred_id, illness)
        
        per_illness = service.calculate_per_illness_metrics("1h")
        
        assert len(per_illness) == 3
        for illness in illnesses:
            assert illness in per_illness
            assert per_illness[illness].total_predictions == 5
            assert per_illness[illness].accuracy == 1.0  # All correct
    
    def test_per_illness_metrics_with_errors(self):
        """Test per-illness metrics with incorrect predictions."""
        service = MonitoringService()
        
        # Log flu predictions, some incorrect
        for i in range(10):
            pred_id = f"pred_{i:03d}"
            service.log_prediction(
                prediction_id=pred_id,
                predicted_illness="flu",
                confidence=0.85,
                features={"fever": 1.0},
                latency_ms=150.0
            )
            # First 7 are correct, last 3 are actually cold
            actual = "flu" if i < 7 else "cold"
            service.update_prediction_feedback(pred_id, actual)
        
        per_illness = service.calculate_per_illness_metrics("1h")
        
        # Should have metrics for both flu and cold (actual illnesses)
        assert "flu" in per_illness
        assert "cold" in per_illness
        
        # Flu: 7 total, 7 correct
        assert per_illness["flu"].total_predictions == 7
        assert per_illness["flu"].accuracy == 1.0
        
        # Cold: 3 total, 0 correct (all predicted as flu)
        assert per_illness["cold"].total_predictions == 3
        assert per_illness["cold"].accuracy == 0.0


class TestAlerting:
    """Tests for alerting functionality."""
    
    def test_check_thresholds_no_alerts(self):
        """Test checking thresholds with no alerts."""
        service = MonitoringService()
        service.set_baseline_accuracy(0.85)
        
        # Log predictions with good metrics
        for i in range(10):
            service.log_prediction(
                prediction_id=f"pred_{i:03d}",
                predicted_illness="flu",
                confidence=0.85,
                features={"fever": 1.0},
                latency_ms=150.0
            )
            service.update_prediction_feedback(f"pred_{i:03d}", "flu")
        
        alerts = service.check_thresholds()
        
        assert len(alerts) == 0
    
    def test_accuracy_drop_alert(self):
        """Test alert for accuracy drop."""
        service = MonitoringService()
        service.set_baseline_accuracy(0.90)
        
        # Log predictions with low accuracy
        for i in range(10):
            service.log_prediction(
                prediction_id=f"pred_{i:03d}",
                predicted_illness="flu",
                confidence=0.85,
                features={"fever": 1.0},
                latency_ms=150.0
            )
            # Only 7 correct = 70% accuracy (20% drop from baseline)
            actual = "flu" if i < 7 else "cold"
            service.update_prediction_feedback(f"pred_{i:03d}", actual)
        
        alerts = service.check_thresholds()
        
        assert len(alerts) > 0
        accuracy_alerts = [a for a in alerts if a.alert_type == AlertType.ACCURACY_DROP]
        assert len(accuracy_alerts) == 1
        assert accuracy_alerts[0].severity == 'critical'  # >10% drop
    
    def test_latency_high_alert(self):
        """Test alert for high latency."""
        service = MonitoringService()
        
        # Log predictions with high latency
        for i in range(10):
            service.log_prediction(
                prediction_id=f"pred_{i:03d}",
                predicted_illness="flu",
                confidence=0.85,
                features={"fever": 1.0},
                latency_ms=600.0  # Above 500ms threshold
            )
        
        alerts = service.check_thresholds()
        
        latency_alerts = [a for a in alerts if a.alert_type == AlertType.LATENCY_HIGH]
        assert len(latency_alerts) == 1
        assert latency_alerts[0].metric_value > ALERT_THRESHOLDS['latency_p95']


class TestReporting:
    """Tests for report generation functionality."""
    
    def test_generate_report(self):
        """Test generating monitoring report."""
        service = MonitoringService()
        
        # Log some predictions
        for i in range(20):
            service.log_prediction(
                prediction_id=f"pred_{i:03d}",
                predicted_illness="flu",
                confidence=0.85,
                features={"fever": 1.0},
                latency_ms=150.0
            )
            service.update_prediction_feedback(f"pred_{i:03d}", "flu")
        
        report = service.generate_report("7d")
        
        assert report.total_predictions == 20
        assert report.overall_metrics.accuracy == 1.0
        assert len(report.per_illness_metrics) > 0
        assert report.period_start < report.period_end
    
    def test_report_includes_alerts(self):
        """Test that report includes alerts from period."""
        service = MonitoringService()
        service.set_baseline_accuracy(0.90)
        
        # Log predictions with low accuracy to trigger alert
        for i in range(10):
            service.log_prediction(
                prediction_id=f"pred_{i:03d}",
                predicted_illness="flu",
                confidence=0.85,
                features={"fever": 1.0},
                latency_ms=150.0
            )
            actual = "flu" if i < 7 else "cold"
            service.update_prediction_feedback(f"pred_{i:03d}", actual)
        
        # Trigger alerts
        service.check_thresholds()
        
        # Generate report
        report = service.generate_report("7d")
        
        assert len(report.alerts) > 0


class TestTimeWindowParsing:
    """Tests for time window parsing."""
    
    def test_parse_hours(self):
        """Test parsing hour time windows."""
        service = MonitoringService()
        
        delta = service._parse_time_window("1h")
        assert delta == timedelta(hours=1)
        
        delta = service._parse_time_window("24h")
        assert delta == timedelta(hours=24)
    
    def test_parse_days(self):
        """Test parsing day time windows."""
        service = MonitoringService()
        
        delta = service._parse_time_window("1d")
        assert delta == timedelta(days=1)
        
        delta = service._parse_time_window("7d")
        assert delta == timedelta(days=7)
    
    def test_parse_minutes(self):
        """Test parsing minute time windows."""
        service = MonitoringService()
        
        delta = service._parse_time_window("30m")
        assert delta == timedelta(minutes=30)
    
    def test_parse_invalid_unit(self):
        """Test parsing invalid time unit."""
        service = MonitoringService()
        
        with pytest.raises(ValueError, match="Invalid time window unit"):
            service._parse_time_window("1x")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
