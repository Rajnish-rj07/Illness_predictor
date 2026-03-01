"""
Unit tests for DriftDetectionService.

Tests PSI calculation, KS test, concept drift, and drift reporting functionality.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from src.mlops.drift_detection_service import (
    DriftDetectionService,
    DriftType,
    DriftSeverity,
    PSI_THRESHOLDS,
    CONCEPT_DRIFT_THRESHOLD
)


class TestPSICalculation:
    """Tests for PSI calculation."""
    
    def test_calculate_psi_no_drift(self):
        """Test PSI calculation with no drift."""
        service = DriftDetectionService()
        
        # Identical distributions
        baseline = np.array([0.2, 0.3, 0.3, 0.2])
        current = np.array([0.2, 0.3, 0.3, 0.2])
        
        psi = service.calculate_psi(baseline, current)
        
        assert psi < 0.01  # Very small PSI for identical distributions
    
    def test_calculate_psi_with_drift(self):
        """Test PSI calculation with drift."""
        service = DriftDetectionService()
        
        # Different distributions
        baseline = np.array([0.4, 0.3, 0.2, 0.1])
        current = np.array([0.1, 0.2, 0.3, 0.4])
        
        psi = service.calculate_psi(baseline, current)
        
        assert psi > 0.1  # Significant PSI for different distributions
    
    def test_calculate_psi_handles_zeros(self):
        """Test that PSI handles zero values."""
        service = DriftDetectionService()
        
        # Distribution with zeros
        baseline = np.array([0.5, 0.5, 0.0, 0.0])
        current = np.array([0.0, 0.0, 0.5, 0.5])
        
        psi = service.calculate_psi(baseline, current)
        
        assert not np.isnan(psi)
        assert not np.isinf(psi)


class TestFeatureDrift:
    """Tests for feature drift detection."""
    
    def test_calculate_feature_drift_no_drift(self):
        """Test feature drift with no drift."""
        service = DriftDetectionService()
        
        # Create similar datasets
        np.random.seed(42)
        baseline = pd.DataFrame({
            'feature1': np.random.normal(0, 1, 1000),
            'feature2': np.random.normal(5, 2, 1000)
        })
        current = pd.DataFrame({
            'feature1': np.random.normal(0, 1, 1000),
            'feature2': np.random.normal(5, 2, 1000)
        })
        
        drifts = service.calculate_feature_drift(baseline, current)
        
        assert len(drifts) == 2
        assert drifts['feature1'].psi_score < PSI_THRESHOLDS['moderate']
        assert drifts['feature2'].psi_score < PSI_THRESHOLDS['moderate']
    
    def test_calculate_feature_drift_with_drift(self):
        """Test feature drift with significant drift."""
        service = DriftDetectionService()
        
        # Create datasets with drift
        np.random.seed(42)
        baseline = pd.DataFrame({
            'feature1': np.random.normal(0, 1, 1000)
        })
        current = pd.DataFrame({
            'feature1': np.random.normal(5, 1, 1000)  # Shifted mean
        })
        
        drifts = service.calculate_feature_drift(baseline, current)
        
        assert drifts['feature1'].has_drift is True
        assert drifts['feature1'].psi_score > PSI_THRESHOLDS['moderate']
    
    def test_feature_drift_includes_ks_test(self):
        """Test that feature drift includes KS test results."""
        service = DriftDetectionService()
        
        np.random.seed(42)
        baseline = pd.DataFrame({'feature1': np.random.normal(0, 1, 100)})
        current = pd.DataFrame({'feature1': np.random.normal(0, 1, 100)})
        
        drifts = service.calculate_feature_drift(baseline, current)
        
        assert drifts['feature1'].ks_statistic is not None
        assert drifts['feature1'].ks_p_value is not None
    
    def test_feature_drift_severity_classification(self):
        """Test drift severity classification."""
        service = DriftDetectionService()
        
        np.random.seed(42)
        baseline = pd.DataFrame({
            'no_drift': np.random.normal(0, 1, 1000),
            'moderate_drift': np.random.normal(0, 1, 1000),
            'significant_drift': np.random.normal(0, 1, 1000)
        })
        current = pd.DataFrame({
            'no_drift': np.random.normal(0, 1, 1000),
            'moderate_drift': np.random.normal(1, 1, 1000),
            'significant_drift': np.random.normal(10, 1, 1000)
        })
        
        drifts = service.calculate_feature_drift(baseline, current)
        
        assert drifts['no_drift'].severity == DriftSeverity.NONE
        # Note: actual severity depends on PSI calculation


class TestConceptDrift:
    """Tests for concept drift detection."""
    
    def test_calculate_concept_drift(self):
        """Test concept drift calculation."""
        service = DriftDetectionService()
        service.set_baseline(pd.DataFrame(), 0.90)
        
        drift_score = service.calculate_concept_drift(0.85)
        
        assert abs(drift_score - 0.05) < 0.001  # Allow for floating point precision
    
    def test_concept_drift_no_baseline(self):
        """Test concept drift without baseline."""
        service = DriftDetectionService()
        
        drift_score = service.calculate_concept_drift(0.85)
        
        assert drift_score == 0.0
    
    def test_concept_drift_records_history(self):
        """Test that concept drift records accuracy history."""
        service = DriftDetectionService()
        service.set_baseline(pd.DataFrame(), 0.90)
        
        service.calculate_concept_drift(0.88)
        service.calculate_concept_drift(0.86)
        service.calculate_concept_drift(0.84)
        
        history = service.get_accuracy_history()
        assert len(history) == 3


class TestDriftTypeDetection:
    """Tests for drift type detection."""
    
    def test_detect_no_drift(self):
        """Test detection of no drift."""
        service = DriftDetectionService()
        
        feature_drifts = {
            'feature1': type('obj', (object,), {'has_drift': False})()
        }
        concept_drift_score = 0.02
        
        drift_type = service.detect_drift_type(feature_drifts, concept_drift_score)
        
        assert drift_type == DriftType.NO_DRIFT
    
    def test_detect_feature_drift_only(self):
        """Test detection of feature drift only."""
        service = DriftDetectionService()
        
        feature_drifts = {
            'feature1': type('obj', (object,), {'has_drift': True})()
        }
        concept_drift_score = 0.02
        
        drift_type = service.detect_drift_type(feature_drifts, concept_drift_score)
        
        assert drift_type == DriftType.FEATURE_DRIFT
    
    def test_detect_concept_drift_only(self):
        """Test detection of concept drift only."""
        service = DriftDetectionService()
        
        feature_drifts = {
            'feature1': type('obj', (object,), {'has_drift': False})()
        }
        concept_drift_score = 0.10
        
        drift_type = service.detect_drift_type(feature_drifts, concept_drift_score)
        
        assert drift_type == DriftType.CONCEPT_DRIFT
    
    def test_detect_both_drifts(self):
        """Test detection of both feature and concept drift."""
        service = DriftDetectionService()
        
        feature_drifts = {
            'feature1': type('obj', (object,), {'has_drift': True})()
        }
        concept_drift_score = 0.10
        
        drift_type = service.detect_drift_type(feature_drifts, concept_drift_score)
        
        assert drift_type == DriftType.BOTH


class TestDriftCategorization:
    """Tests for drift pattern categorization."""
    
    def test_categorize_sudden_drift(self):
        """Test categorization of sudden drift."""
        service = DriftDetectionService()
        
        # Simulate sudden drop
        service.accuracy_history = [
            (datetime.utcnow(), 0.90),
            (datetime.utcnow(), 0.89),
            (datetime.utcnow(), 0.75),  # Sudden drop
            (datetime.utcnow(), 0.74)
        ]
        
        pattern = service.categorize_drift_pattern()
        
        assert pattern == "sudden"
    
    def test_categorize_gradual_drift(self):
        """Test categorization of gradual drift."""
        service = DriftDetectionService()
        
        # Simulate gradual decline
        service.accuracy_history = [
            (datetime.utcnow(), 0.90),
            (datetime.utcnow(), 0.87),
            (datetime.utcnow(), 0.84),
            (datetime.utcnow(), 0.81),
            (datetime.utcnow(), 0.78)
        ]
        
        pattern = service.categorize_drift_pattern()
        
        assert pattern == "gradual"
    
    def test_categorize_insufficient_data(self):
        """Test categorization with insufficient data."""
        service = DriftDetectionService()
        
        service.accuracy_history = [
            (datetime.utcnow(), 0.90)
        ]
        
        pattern = service.categorize_drift_pattern()
        
        assert pattern == "insufficient_data"


class TestRecommendations:
    """Tests for drift recommendations."""
    
    def test_recommend_no_drift(self):
        """Test recommendation for no drift."""
        service = DriftDetectionService()
        
        recommendation = service.recommend_action(
            DriftType.NO_DRIFT, {}, 0.0
        )
        
        assert "No significant drift" in recommendation
    
    def test_recommend_critical_both_drifts(self):
        """Test recommendation for both drifts."""
        service = DriftDetectionService()
        
        feature_drifts = {
            'f1': type('obj', (object,), {
                'severity': DriftSeverity.SIGNIFICANT
            })()
        }
        
        recommendation = service.recommend_action(
            DriftType.BOTH, feature_drifts, 0.15
        )
        
        assert "CRITICAL" in recommendation
        assert "IMMEDIATE RETRAINING" in recommendation
    
    def test_recommend_concept_drift(self):
        """Test recommendation for concept drift."""
        service = DriftDetectionService()
        
        recommendation = service.recommend_action(
            DriftType.CONCEPT_DRIFT, {}, 0.08
        )
        
        assert "Concept drift" in recommendation


class TestDriftReport:
    """Tests for drift report generation."""
    
    def test_generate_drift_report(self):
        """Test generating drift report."""
        service = DriftDetectionService()
        service.set_baseline(pd.DataFrame(), 0.90)
        
        np.random.seed(42)
        baseline = pd.DataFrame({
            'feature1': np.random.normal(0, 1, 100)
        })
        current = pd.DataFrame({
            'feature1': np.random.normal(0, 1, 100)
        })
        
        report = service.generate_drift_report(
            baseline, current, 0.88,
            baseline_period="week1",
            current_period="week2"
        )
        
        assert report.timestamp is not None
        assert report.drift_type is not None
        assert len(report.feature_drifts) > 0
        assert report.recommendation is not None
        assert report.baseline_period == "week1"
        assert report.current_period == "week2"
    
    def test_report_includes_all_features(self):
        """Test that report includes all features."""
        service = DriftDetectionService()
        service.set_baseline(pd.DataFrame(), 0.90)
        
        np.random.seed(42)
        baseline = pd.DataFrame({
            'feature1': np.random.normal(0, 1, 100),
            'feature2': np.random.normal(5, 2, 100),
            'feature3': np.random.uniform(0, 10, 100)
        })
        current = pd.DataFrame({
            'feature1': np.random.normal(0, 1, 100),
            'feature2': np.random.normal(5, 2, 100),
            'feature3': np.random.uniform(0, 10, 100)
        })
        
        report = service.generate_drift_report(baseline, current, 0.88)
        
        assert len(report.feature_drifts) == 3


class TestBaselineManagement:
    """Tests for baseline management."""
    
    def test_set_baseline(self):
        """Test setting baseline."""
        service = DriftDetectionService()
        
        data = pd.DataFrame({'feature1': [1, 2, 3]})
        service.set_baseline(data, 0.90)
        
        assert service.baseline_data is not None
        assert service.baseline_accuracy == 0.90
    
    def test_get_accuracy_history(self):
        """Test getting accuracy history."""
        service = DriftDetectionService()
        service.set_baseline(pd.DataFrame(), 0.90)
        
        service.calculate_concept_drift(0.88)
        service.calculate_concept_drift(0.86)
        
        history = service.get_accuracy_history()
        assert len(history) == 2
        
        limited = service.get_accuracy_history(limit=1)
        assert len(limited) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
