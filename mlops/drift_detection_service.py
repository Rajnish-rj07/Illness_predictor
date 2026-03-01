"""
MLOps Drift Detection Service for the Illness Prediction System.

Implements feature drift and concept drift detection using statistical methods
to trigger retraining recommendations.

Validates: Requirements 7.4, 7.5, 17.1, 17.2, 17.3, 17.4, 17.5
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from scipy.stats import ks_2samp

logger = logging.getLogger(__name__)


class DriftType(Enum):
    """Types of drift detected."""
    NO_DRIFT = "no_drift"
    FEATURE_DRIFT = "feature_drift"
    CONCEPT_DRIFT = "concept_drift"
    BOTH = "both"


class DriftSeverity(Enum):
    """Severity of detected drift."""
    NONE = "none"
    MODERATE = "moderate"
    SIGNIFICANT = "significant"


@dataclass
class FeatureDriftResult:
    """Result of feature drift detection for a single feature."""
    feature_name: str
    psi_score: float
    ks_statistic: Optional[float] = None
    ks_p_value: Optional[float] = None
    has_drift: bool = False
    severity: DriftSeverity = DriftSeverity.NONE


@dataclass
class DriftReport:
    """Comprehensive drift detection report."""
    timestamp: datetime
    drift_type: DriftType
    feature_drifts: Dict[str, FeatureDriftResult]
    concept_drift_score: float
    recommendation: str
    baseline_period: str
    current_period: str
    visualizations: List[str] = field(default_factory=list)


# Drift thresholds
PSI_THRESHOLDS = {
    'moderate': 0.1,
    'significant': 0.25
}

CONCEPT_DRIFT_THRESHOLD = 0.05  # 5% accuracy drop


class DriftDetectionService:
    """
    Drift detection service for monitoring feature and concept drift.
    
    Responsibilities:
    - Calculate Population Stability Index (PSI) for feature drift
    - Perform Kolmogorov-Smirnov test for continuous features
    - Track concept drift via accuracy monitoring
    - Categorize drift as gradual or sudden
    - Generate drift reports with visualizations
    - Trigger retraining recommendations
    
    Validates: Requirements 7.4, 7.5, 17.1, 17.2, 17.3, 17.4, 17.5
    """
    
    def __init__(self):
        """Initialize drift detection service."""
        self.baseline_data: Optional[pd.DataFrame] = None
        self.baseline_accuracy: Optional[float] = None
        self.accuracy_history: List[Tuple[datetime, float]] = []
        
        logger.info("DriftDetectionService initialized")
    
    def set_baseline(self, data: pd.DataFrame, accuracy: float) -> None:
        """
        Set baseline data and accuracy for drift detection.
        
        Args:
            data: Baseline feature data
            accuracy: Baseline model accuracy
        """
        self.baseline_data = data.copy()
        self.baseline_accuracy = accuracy
        
        logger.info(f"Baseline set: {len(data)} samples, accuracy={accuracy:.3f}")
    
    def calculate_psi(
        self,
        baseline_dist: np.ndarray,
        current_dist: np.ndarray
    ) -> float:
        """
        Calculate Population Stability Index (PSI).
        
        Validates: Requirements 7.4, 17.1
        
        Args:
            baseline_dist: Baseline distribution (probabilities)
            current_dist: Current distribution (probabilities)
            
        Returns:
            PSI score
        """
        # Avoid division by zero and log(0) issues
        # Use a small epsilon to handle empty bins
        epsilon = 1e-10
        baseline_dist = np.where(baseline_dist == 0, epsilon, baseline_dist)
        current_dist = np.where(current_dist == 0, epsilon, current_dist)
        
        # Calculate PSI with safeguards against inf/nan
        ratio = current_dist / baseline_dist
        # Clip extreme ratios to prevent overflow
        ratio = np.clip(ratio, epsilon, 1/epsilon)
        
        psi = np.sum(
            (current_dist - baseline_dist) * np.log(ratio)
        )
        
        return psi
    
    def calculate_feature_drift(
        self,
        baseline: pd.DataFrame,
        current: pd.DataFrame,
        n_bins: int = 10
    ) -> Dict[str, FeatureDriftResult]:
        """
        Calculate feature drift for all features.
        
        Validates: Requirements 7.4, 17.1
        
        Args:
            baseline: Baseline feature data
            current: Current feature data
            n_bins: Number of bins for PSI calculation
            
        Returns:
            Dictionary mapping feature names to drift results
        """
        logger.info("Calculating feature drift...")
        
        feature_drifts = {}
        
        for feature in baseline.columns:
            if feature not in current.columns:
                logger.warning(f"Feature {feature} not in current data, skipping")
                continue
            
            baseline_values = baseline[feature].dropna()
            current_values = current[feature].dropna()
            
            if len(baseline_values) == 0 or len(current_values) == 0:
                logger.warning(f"Feature {feature} has no values, skipping")
                continue
            
            # Calculate PSI
            try:
                # Create bins that cover both baseline and current data ranges
                min_val = min(baseline_values.min(), current_values.min())
                max_val = max(baseline_values.max(), current_values.max())
                bins = np.linspace(min_val, max_val, n_bins + 1)
                
                # Calculate distributions
                baseline_hist, _ = np.histogram(baseline_values, bins=bins)
                current_hist, _ = np.histogram(current_values, bins=bins)
                
                # Normalize to probabilities
                baseline_dist = baseline_hist / baseline_hist.sum()
                current_dist = current_hist / current_hist.sum()
                
                psi_score = self.calculate_psi(baseline_dist, current_dist)
                
                # Perform KS test for continuous features
                ks_statistic, ks_p_value = ks_2samp(baseline_values, current_values)
                
                # Determine drift severity
                has_drift = False
                severity = DriftSeverity.NONE
                
                if psi_score >= PSI_THRESHOLDS['significant']:
                    has_drift = True
                    severity = DriftSeverity.SIGNIFICANT
                elif psi_score >= PSI_THRESHOLDS['moderate']:
                    has_drift = True
                    severity = DriftSeverity.MODERATE
                
                feature_drifts[feature] = FeatureDriftResult(
                    feature_name=feature,
                    psi_score=psi_score,
                    ks_statistic=ks_statistic,
                    ks_p_value=ks_p_value,
                    has_drift=has_drift,
                    severity=severity
                )
                
                if has_drift:
                    logger.info(
                        f"Drift detected in {feature}: PSI={psi_score:.3f}, "
                        f"severity={severity.value}"
                    )
            
            except Exception as e:
                logger.error(f"Error calculating drift for {feature}: {e}")
                continue
        
        logger.info(f"Feature drift calculated for {len(feature_drifts)} features")
        
        return feature_drifts
    
    def calculate_concept_drift(
        self,
        current_accuracy: float,
        time_window: str = "7d"
    ) -> float:
        """
        Calculate concept drift based on accuracy changes.
        
        Validates: Requirements 17.3
        
        Args:
            current_accuracy: Current model accuracy
            time_window: Time window for drift detection
            
        Returns:
            Concept drift score (accuracy drop)
        """
        # Record accuracy
        self.accuracy_history.append((datetime.utcnow(), current_accuracy))
        
        if self.baseline_accuracy is None:
            logger.warning("No baseline accuracy set")
            return 0.0
        
        # Calculate drift
        drift_score = self.baseline_accuracy - current_accuracy
        
        logger.info(
            f"Concept drift: baseline={self.baseline_accuracy:.3f}, "
            f"current={current_accuracy:.3f}, drift={drift_score:.3f}"
        )
        
        return drift_score
    
    def detect_drift_type(
        self,
        feature_drifts: Dict[str, FeatureDriftResult],
        concept_drift_score: float
    ) -> DriftType:
        """
        Determine the type of drift detected.
        
        Validates: Requirements 17.2
        
        Args:
            feature_drifts: Feature drift results
            concept_drift_score: Concept drift score
            
        Returns:
            Type of drift detected
        """
        has_feature_drift = any(
            result.has_drift for result in feature_drifts.values()
        )
        has_concept_drift = concept_drift_score > CONCEPT_DRIFT_THRESHOLD
        
        if has_feature_drift and has_concept_drift:
            return DriftType.BOTH
        elif has_feature_drift:
            return DriftType.FEATURE_DRIFT
        elif has_concept_drift:
            return DriftType.CONCEPT_DRIFT
        else:
            return DriftType.NO_DRIFT
    
    def categorize_drift_pattern(
        self,
        time_window: str = "7d"
    ) -> str:
        """
        Categorize drift as gradual or sudden.
        
        Validates: Requirements 17.2
        
        Args:
            time_window: Time window to analyze
            
        Returns:
            "gradual" or "sudden"
        """
        if len(self.accuracy_history) < 3:
            return "insufficient_data"
        
        # Get recent accuracy values
        recent_accuracies = [acc for _, acc in self.accuracy_history[-10:]]
        
        # Calculate rate of change
        changes = [
            abs(recent_accuracies[i] - recent_accuracies[i-1])
            for i in range(1, len(recent_accuracies))
        ]
        
        avg_change = np.mean(changes)
        max_change = np.max(changes)
        
        # Sudden drift: large single change (>= 10% drop in single step)
        # Gradual drift: consistent small changes
        if max_change >= 0.10:  # 10% or more drop in single step
            return "sudden"
        elif avg_change > 0.02:  # Consistent 2% changes
            return "gradual"
        else:
            return "stable"
    
    def recommend_action(
        self,
        drift_type: DriftType,
        feature_drifts: Dict[str, FeatureDriftResult],
        concept_drift_score: float
    ) -> str:
        """
        Generate recommendation based on drift detection.
        
        Validates: Requirements 7.5, 17.5
        
        Args:
            drift_type: Type of drift detected
            feature_drifts: Feature drift results
            concept_drift_score: Concept drift score
            
        Returns:
            Recommendation string
        """
        if drift_type == DriftType.NO_DRIFT:
            return "No significant drift detected. Continue monitoring."
        
        # Count significant drifts
        significant_features = [
            name for name, result in feature_drifts.items()
            if result.severity == DriftSeverity.SIGNIFICANT
        ]
        
        if drift_type == DriftType.BOTH:
            return (
                f"CRITICAL: Both feature and concept drift detected. "
                f"{len(significant_features)} features with significant drift. "
                f"Accuracy dropped by {concept_drift_score:.1%}. "
                f"IMMEDIATE RETRAINING RECOMMENDED."
            )
        elif drift_type == DriftType.CONCEPT_DRIFT:
            if concept_drift_score > 0.10:
                return (
                    f"CRITICAL: Concept drift detected. "
                    f"Accuracy dropped by {concept_drift_score:.1%}. "
                    f"IMMEDIATE RETRAINING RECOMMENDED."
                )
            else:
                return (
                    f"WARNING: Concept drift detected. "
                    f"Accuracy dropped by {concept_drift_score:.1%}. "
                    f"Schedule retraining soon."
                )
        elif drift_type == DriftType.FEATURE_DRIFT:
            if len(significant_features) > 5:
                return (
                    f"WARNING: Significant feature drift in {len(significant_features)} features. "
                    f"Retraining recommended within 7 days."
                )
            else:
                return (
                    f"INFO: Moderate feature drift detected in {len(significant_features)} features. "
                    f"Monitor closely and consider retraining."
                )
        
        return "Unknown drift type. Manual investigation required."
    
    def generate_drift_report(
        self,
        baseline: pd.DataFrame,
        current: pd.DataFrame,
        current_accuracy: float,
        baseline_period: str = "baseline",
        current_period: str = "current"
    ) -> DriftReport:
        """
        Generate comprehensive drift detection report.
        
        Validates: Requirements 17.4
        
        Args:
            baseline: Baseline feature data
            current: Current feature data
            current_accuracy: Current model accuracy
            baseline_period: Description of baseline period
            current_period: Description of current period
            
        Returns:
            Drift report
        """
        logger.info("Generating drift report...")
        
        # Calculate feature drift
        feature_drifts = self.calculate_feature_drift(baseline, current)
        
        # Calculate concept drift
        concept_drift_score = self.calculate_concept_drift(current_accuracy)
        
        # Detect drift type
        drift_type = self.detect_drift_type(feature_drifts, concept_drift_score)
        
        # Generate recommendation
        recommendation = self.recommend_action(
            drift_type, feature_drifts, concept_drift_score
        )
        
        report = DriftReport(
            timestamp=datetime.utcnow(),
            drift_type=drift_type,
            feature_drifts=feature_drifts,
            concept_drift_score=concept_drift_score,
            recommendation=recommendation,
            baseline_period=baseline_period,
            current_period=current_period,
            visualizations=[]
        )
        
        logger.info(
            f"Drift report generated: type={drift_type.value}, "
            f"features_with_drift={sum(1 for r in feature_drifts.values() if r.has_drift)}"
        )
        
        return report
    
    def get_accuracy_history(self, limit: Optional[int] = None) -> List[Tuple[datetime, float]]:
        """
        Get accuracy history.
        
        Args:
            limit: Maximum number of entries to return (most recent first)
            
        Returns:
            List of (timestamp, accuracy) tuples
        """
        if limit:
            return self.accuracy_history[-limit:]
        return self.accuracy_history
