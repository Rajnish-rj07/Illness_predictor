"""
Property-based tests for DriftDetectionService.

Tests universal correctness properties for drift detection using hypothesis.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
import pandas as pd
import numpy as np
from src.mlops.drift_detection_service import (
    DriftDetectionService,
    DriftType,
    DriftSeverity,
    PSI_THRESHOLDS
)


# Custom strategies
@st.composite
def feature_data(draw, n_samples=100, n_features=5):
    """Generate feature data for drift detection."""
    data = {}
    for i in range(n_features):
        mean = draw(st.floats(min_value=-10, max_value=10))
        std = draw(st.floats(min_value=0.1, max_value=5))
        data[f'feature{i}'] = np.random.normal(mean, std, n_samples)
    
    return pd.DataFrame(data)


class TestProperty52FeatureDriftMonitoring:
    """
    Property 52: Feature drift monitoring
    
    For any set of features, the system should compute PSI for all features
    and detect drift when PSI exceeds thresholds.
    
    Validates: Requirements 7.4, 17.1
    """
    
    @given(
        n_features=st.integers(min_value=1, max_value=10),
        n_samples=st.integers(min_value=50, max_value=200)
    )
    @settings(max_examples=10, deadline=None)
    def test_psi_computed_for_all_features(self, n_features, n_samples):
        """Test that PSI is computed for all features."""
        service = DriftDetectionService()
        
        # Create datasets with same features
        np.random.seed(42)
        baseline = pd.DataFrame({
            f'feature{i}': np.random.normal(0, 1, n_samples)
            for i in range(n_features)
        })
        current = pd.DataFrame({
            f'feature{i}': np.random.normal(0, 1, n_samples)
            for i in range(n_features)
        })
        
        drifts = service.calculate_feature_drift(baseline, current)
        
        # PSI should be computed for all features
        assert len(drifts) == n_features
        for i in range(n_features):
            assert f'feature{i}' in drifts
            assert drifts[f'feature{i}'].psi_score is not None
    
    @given(n_samples=st.integers(min_value=50, max_value=200))
    @settings(max_examples=10, deadline=None)
    def test_identical_distributions_have_low_psi(self, n_samples):
        """Test that identical distributions have low PSI."""
        service = DriftDetectionService()
        
        np.random.seed(42)
        data = np.random.normal(0, 1, n_samples)
        baseline = pd.DataFrame({'feature1': data})
        current = pd.DataFrame({'feature1': data.copy()})
        
        drifts = service.calculate_feature_drift(baseline, current)
        
        # Identical distributions should have very low PSI
        assert drifts['feature1'].psi_score < 0.01
        assert drifts['feature1'].has_drift is False
    
    @given(
        shift=st.floats(min_value=5.0, max_value=10.0),
        n_samples=st.integers(min_value=100, max_value=200)
    )
    @settings(max_examples=10, deadline=None)
    def test_shifted_distributions_have_high_psi(self, shift, n_samples):
        """Test that shifted distributions have high PSI."""
        service = DriftDetectionService()
        
        np.random.seed(42)
        baseline = pd.DataFrame({'feature1': np.random.normal(0, 1, n_samples)})
        current = pd.DataFrame({'feature1': np.random.normal(shift, 1, n_samples)})
        
        drifts = service.calculate_feature_drift(baseline, current)
        
        # Shifted distributions should have high PSI
        assert drifts['feature1'].psi_score > PSI_THRESHOLDS['moderate']
        assert drifts['feature1'].has_drift is True


class TestProperty53DriftCategorization:
    """
    Property 53: Drift categorization
    
    For any detected drift, the system should categorize it as gradual or sudden
    based on the pattern of accuracy changes.
    
    Validates: Requirements 17.2
    """
    
    @given(drop_size=st.floats(min_value=0.11, max_value=0.30))
    @settings(max_examples=10, deadline=None)
    def test_large_single_drop_is_sudden(self, drop_size):
        """Test that large single drops are categorized as sudden."""
        service = DriftDetectionService()
        
        # Simulate sudden drop - ensure the drop between consecutive points is drop_size
        baseline_acc = 0.90
        service.accuracy_history = [
            (None, baseline_acc),
            (None, baseline_acc - 0.01),  # Small change
            (None, baseline_acc - 0.01 - drop_size),  # Sudden drop of drop_size
            (None, baseline_acc - 0.01 - drop_size - 0.01)  # Small change after
        ]
        
        pattern = service.categorize_drift_pattern()
        
        assert pattern == "sudden"
    
    @given(n_steps=st.integers(min_value=5, max_value=10))
    @settings(max_examples=10, deadline=None)
    def test_consistent_small_drops_are_gradual(self, n_steps):
        """Test that consistent small drops are categorized as gradual."""
        service = DriftDetectionService()
        
        # Simulate gradual decline
        service.accuracy_history = [
            (None, 0.90 - i * 0.03) for i in range(n_steps)
        ]
        
        pattern = service.categorize_drift_pattern()
        
        assert pattern == "gradual"


class TestProperty54ConceptDriftTracking:
    """
    Property 54: Concept drift tracking
    
    For any time window, the system should track accuracy and detect
    concept drift when accuracy drops significantly.
    
    Validates: Requirements 17.3
    """
    
    @given(
        baseline_acc=st.floats(min_value=0.80, max_value=0.95),
        current_acc=st.floats(min_value=0.70, max_value=0.95)
    )
    @settings(max_examples=20, deadline=None)
    def test_concept_drift_score_is_accuracy_drop(self, baseline_acc, current_acc):
        """Test that concept drift score equals accuracy drop."""
        service = DriftDetectionService()
        service.set_baseline(pd.DataFrame(), baseline_acc)
        
        drift_score = service.calculate_concept_drift(current_acc)
        
        expected_drop = baseline_acc - current_acc
        assert abs(drift_score - expected_drop) < 0.001
    
    @given(
        baseline_acc=st.floats(min_value=0.80, max_value=0.95),
        drop=st.floats(min_value=0.06, max_value=0.20)
    )
    @settings(max_examples=10, deadline=None)
    def test_significant_drop_detected_as_concept_drift(self, baseline_acc, drop):
        """Test that significant accuracy drops are detected."""
        service = DriftDetectionService()
        service.set_baseline(pd.DataFrame(), baseline_acc)
        
        current_acc = baseline_acc - drop
        drift_score = service.calculate_concept_drift(current_acc)
        
        # Should detect concept drift
        assert drift_score > 0.05
    
    @given(n_measurements=st.integers(min_value=1, max_value=20))
    @settings(max_examples=10, deadline=None)
    def test_accuracy_history_is_tracked(self, n_measurements):
        """Test that accuracy history is tracked over time."""
        service = DriftDetectionService()
        service.set_baseline(pd.DataFrame(), 0.90)
        
        for i in range(n_measurements):
            service.calculate_concept_drift(0.85 - i * 0.01)
        
        history = service.get_accuracy_history()
        assert len(history) == n_measurements


class TestProperty55DriftReportGeneration:
    """
    Property 55: Drift report generation
    
    For any drift detection event, the system should generate a comprehensive
    report with feature drifts, concept drift, and recommendations.
    
    Validates: Requirements 17.4
    """
    
    @given(
        n_features=st.integers(min_value=1, max_value=10),
        current_acc=st.floats(min_value=0.70, max_value=0.95)
    )
    @settings(max_examples=10, deadline=None)
    def test_report_includes_all_components(self, n_features, current_acc):
        """Test that drift reports include all required components."""
        service = DriftDetectionService()
        service.set_baseline(pd.DataFrame(), 0.90)
        
        np.random.seed(42)
        baseline = pd.DataFrame({
            f'feature{i}': np.random.normal(0, 1, 100)
            for i in range(n_features)
        })
        current = pd.DataFrame({
            f'feature{i}': np.random.normal(0, 1, 100)
            for i in range(n_features)
        })
        
        report = service.generate_drift_report(baseline, current, current_acc)
        
        # Report should have all components
        assert report.timestamp is not None
        assert report.drift_type is not None
        assert len(report.feature_drifts) == n_features
        assert report.concept_drift_score is not None
        assert report.recommendation is not None
    
    @given(n_features=st.integers(min_value=1, max_value=5))
    @settings(max_examples=10, deadline=None)
    def test_report_feature_count_matches_input(self, n_features):
        """Test that report includes all input features."""
        service = DriftDetectionService()
        service.set_baseline(pd.DataFrame(), 0.90)
        
        np.random.seed(42)
        baseline = pd.DataFrame({
            f'feature{i}': np.random.normal(0, 1, 100)
            for i in range(n_features)
        })
        current = pd.DataFrame({
            f'feature{i}': np.random.normal(0, 1, 100)
            for i in range(n_features)
        })
        
        report = service.generate_drift_report(baseline, current, 0.85)
        
        assert len(report.feature_drifts) == n_features


class TestProperty56RetrainingRecommendation:
    """
    Property 56: Drift-triggered retraining recommendation
    
    For any significant drift (PSI > 0.25 or accuracy drop > 5%), the system
    should recommend retraining.
    
    Validates: Requirements 7.5, 17.5
    """
    
    @given(drop=st.floats(min_value=0.11, max_value=0.30))
    @settings(max_examples=10, deadline=None)
    def test_large_accuracy_drop_triggers_retraining(self, drop):
        """Test that large accuracy drops trigger retraining recommendation."""
        service = DriftDetectionService()
        
        recommendation = service.recommend_action(
            DriftType.CONCEPT_DRIFT, {}, drop
        )
        
        assert "RETRAINING" in recommendation.upper()
    
    @given(n_significant=st.integers(min_value=6, max_value=15))
    @settings(max_examples=10, deadline=None)
    def test_many_feature_drifts_trigger_retraining(self, n_significant):
        """Test that many feature drifts trigger retraining."""
        service = DriftDetectionService()
        
        feature_drifts = {
            f'feature{i}': type('obj', (object,), {
                'severity': DriftSeverity.SIGNIFICANT
            })()
            for i in range(n_significant)
        }
        
        recommendation = service.recommend_action(
            DriftType.FEATURE_DRIFT, feature_drifts, 0.0
        )
        
        assert "retraining" in recommendation.lower()
    
    @given(
        concept_drop=st.floats(min_value=0.11, max_value=0.30),
        n_features=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=10, deadline=None)
    def test_both_drifts_trigger_immediate_retraining(self, concept_drop, n_features):
        """Test that both drifts trigger immediate retraining."""
        service = DriftDetectionService()
        
        feature_drifts = {
            f'feature{i}': type('obj', (object,), {
                'severity': DriftSeverity.SIGNIFICANT
            })()
            for i in range(n_features)
        }
        
        recommendation = service.recommend_action(
            DriftType.BOTH, feature_drifts, concept_drop
        )
        
        assert "IMMEDIATE" in recommendation.upper()
        assert "RETRAINING" in recommendation.upper()


class TestDriftDetectionInvariants:
    """Test invariants that should always hold for drift detection."""
    
    @given(
        baseline_dist=st.lists(
            st.floats(min_value=0.01, max_value=1.0),
            min_size=5,
            max_size=10
        )
    )
    @settings(max_examples=10, deadline=None)
    def test_psi_is_non_negative(self, baseline_dist):
        """Test that PSI is always non-negative."""
        service = DriftDetectionService()
        
        # Normalize to probabilities
        baseline = np.array(baseline_dist)
        baseline = baseline / baseline.sum()
        current = baseline.copy()
        
        psi = service.calculate_psi(baseline, current)
        
        assert psi >= 0
    
    @given(
        baseline_acc=st.floats(min_value=0.70, max_value=0.95),
        current_acc=st.floats(min_value=0.70, max_value=0.95)
    )
    @settings(max_examples=20, deadline=None)
    def test_drift_score_matches_accuracy_difference(self, baseline_acc, current_acc):
        """Test that drift score equals accuracy difference."""
        service = DriftDetectionService()
        service.set_baseline(pd.DataFrame(), baseline_acc)
        
        drift_score = service.calculate_concept_drift(current_acc)
        
        expected = baseline_acc - current_acc
        assert abs(drift_score - expected) < 0.001
    
    @given(n_features=st.integers(min_value=1, max_value=10))
    @settings(max_examples=10, deadline=None)
    def test_all_features_have_drift_results(self, n_features):
        """Test that all features get drift results."""
        service = DriftDetectionService()
        
        np.random.seed(42)
        baseline = pd.DataFrame({
            f'feature{i}': np.random.normal(0, 1, 100)
            for i in range(n_features)
        })
        current = pd.DataFrame({
            f'feature{i}': np.random.normal(0, 1, 100)
            for i in range(n_features)
        })
        
        drifts = service.calculate_feature_drift(baseline, current)
        
        # All features should have results
        assert len(drifts) == n_features
        for i in range(n_features):
            assert f'feature{i}' in drifts


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
