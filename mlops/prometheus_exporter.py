"""
Prometheus metrics exporter for the Illness Prediction System.

Exposes monitoring metrics in Prometheus format for Grafana dashboards.

Validates: Requirements 7.1, 7.2, 8.5
"""

import logging
from typing import Dict, Optional
from prometheus_client import (
    Counter, Gauge, Histogram, Info, 
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)
from datetime import datetime

logger = logging.getLogger(__name__)


class PrometheusExporter:
    """
    Prometheus metrics exporter for monitoring service.
    
    Exposes metrics for:
    - Prediction counts and rates
    - Model performance (accuracy, confidence)
    - System performance (latency, throughput)
    - Drift detection
    - Alerts
    
    Validates: Requirements 7.1, 7.2, 8.5
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize Prometheus exporter.
        
        Args:
            registry: Optional custom registry (defaults to default registry)
        """
        self.registry = registry or CollectorRegistry()
        
        # Prediction metrics
        self.prediction_total = Counter(
            'illness_prediction_total',
            'Total number of predictions made',
            ['model_version'],
            registry=self.registry
        )
        
        self.prediction_by_illness = Counter(
            'illness_prediction_by_illness_total',
            'Total predictions by illness',
            ['illness', 'model_version'],
            registry=self.registry
        )
        
        self.prediction_latency = Histogram(
            'illness_prediction_latency',
            'Prediction latency in milliseconds',
            ['model_version'],
            buckets=[10, 50, 100, 200, 500, 1000, 2000, 5000],
            registry=self.registry
        )
        
        # Model performance metrics
        self.accuracy = Gauge(
            'illness_prediction_accuracy',
            'Overall model accuracy',
            ['model_version'],
            registry=self.registry
        )
        
        self.top3_accuracy = Gauge(
            'illness_prediction_top3_accuracy',
            'Top-3 model accuracy',
            ['model_version'],
            registry=self.registry
        )
        
        self.accuracy_by_illness = Gauge(
            'illness_prediction_accuracy_by_illness',
            'Per-illness accuracy',
            ['illness', 'model_version'],
            registry=self.registry
        )
        
        self.precision = Gauge(
            'illness_prediction_precision',
            'Model precision',
            ['model_version'],
            registry=self.registry
        )
        
        self.recall = Gauge(
            'illness_prediction_recall',
            'Model recall',
            ['model_version'],
            registry=self.registry
        )
        
        self.f1_score = Gauge(
            'illness_prediction_f1_score',
            'Model F1 score',
            ['model_version'],
            registry=self.registry
        )
        
        self.confidence_mean = Gauge(
            'illness_prediction_confidence_mean',
            'Mean prediction confidence',
            ['model_version'],
            registry=self.registry
        )
        
        self.confidence_std = Gauge(
            'illness_prediction_confidence_std',
            'Standard deviation of prediction confidence',
            ['model_version'],
            registry=self.registry
        )
        
        self.baseline_accuracy = Gauge(
            'illness_prediction_baseline_accuracy',
            'Baseline accuracy for comparison',
            registry=self.registry
        )
        
        # Feedback metrics
        self.feedback_total = Counter(
            'illness_prediction_feedback_total',
            'Total feedback received',
            ['model_version'],
            registry=self.registry
        )
        
        # Session metrics
        self.active_sessions = Gauge(
            'illness_prediction_active_sessions',
            'Number of active sessions',
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'illness_prediction_errors_total',
            'Total prediction errors',
            ['error_type', 'model_version'],
            registry=self.registry
        )
        
        # Drift detection metrics
        self.feature_drift_psi = Gauge(
            'illness_prediction_feature_drift_psi',
            'PSI score for feature drift',
            ['feature'],
            registry=self.registry
        )
        
        self.ks_statistic = Gauge(
            'illness_prediction_ks_statistic',
            'KS test statistic for feature drift',
            ['feature'],
            registry=self.registry
        )
        
        self.drift_events_total = Counter(
            'illness_prediction_drift_events_total',
            'Total drift events detected',
            ['drift_type'],
            registry=self.registry
        )
        
        self.retraining_recommended = Gauge(
            'illness_prediction_retraining_recommended',
            'Whether retraining is recommended (1=yes, 0=no)',
            registry=self.registry
        )
        
        self.last_training_timestamp = Gauge(
            'illness_prediction_last_training_timestamp',
            'Timestamp of last model training',
            registry=self.registry
        )
        
        # Database metrics
        self.db_connections_active = Gauge(
            'illness_prediction_db_connections_active',
            'Active database connections',
            registry=self.registry
        )
        
        self.db_connections_idle = Gauge(
            'illness_prediction_db_connections_idle',
            'Idle database connections',
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_hits_total = Counter(
            'illness_prediction_cache_hits_total',
            'Total cache hits',
            registry=self.registry
        )
        
        self.cache_misses_total = Counter(
            'illness_prediction_cache_misses_total',
            'Total cache misses',
            registry=self.registry
        )
        
        # External API metrics
        self.external_api_duration = Histogram(
            'illness_prediction_external_api_duration',
            'External API call duration in milliseconds',
            ['api'],
            buckets=[50, 100, 200, 500, 1000, 2000, 5000, 10000],
            registry=self.registry
        )
        
        # Model info
        self.model_info = Info(
            'illness_prediction_model',
            'Information about the current model',
            registry=self.registry
        )
        
        logger.info("PrometheusExporter initialized")
    
    def record_prediction(
        self,
        illness: str,
        confidence: float,
        latency_ms: float,
        model_version: str = "unknown"
    ) -> None:
        """
        Record a prediction event.
        
        Args:
            illness: Predicted illness
            confidence: Prediction confidence
            latency_ms: Prediction latency in milliseconds
            model_version: Model version used
        """
        self.prediction_total.labels(model_version=model_version).inc()
        self.prediction_by_illness.labels(
            illness=illness,
            model_version=model_version
        ).inc()
        self.prediction_latency.labels(model_version=model_version).observe(latency_ms)
    
    def update_model_metrics(
        self,
        accuracy: Optional[float],
        top3_accuracy: Optional[float],
        precision: Optional[float],
        recall: Optional[float],
        f1_score: Optional[float],
        confidence_mean: float,
        confidence_std: float,
        model_version: str = "unknown"
    ) -> None:
        """
        Update model performance metrics.
        
        Args:
            accuracy: Overall accuracy
            top3_accuracy: Top-3 accuracy
            precision: Precision score
            recall: Recall score
            f1_score: F1 score
            confidence_mean: Mean confidence
            confidence_std: Confidence standard deviation
            model_version: Model version
        """
        if accuracy is not None:
            self.accuracy.labels(model_version=model_version).set(accuracy)
        
        if top3_accuracy is not None:
            self.top3_accuracy.labels(model_version=model_version).set(top3_accuracy)
        
        if precision is not None:
            self.precision.labels(model_version=model_version).set(precision)
        
        if recall is not None:
            self.recall.labels(model_version=model_version).set(recall)
        
        if f1_score is not None:
            self.f1_score.labels(model_version=model_version).set(f1_score)
        
        self.confidence_mean.labels(model_version=model_version).set(confidence_mean)
        self.confidence_std.labels(model_version=model_version).set(confidence_std)
    
    def update_per_illness_metrics(
        self,
        illness_metrics: Dict[str, Dict],
        model_version: str = "unknown"
    ) -> None:
        """
        Update per-illness metrics.
        
        Args:
            illness_metrics: Dictionary mapping illness to metrics
            model_version: Model version
        """
        for illness, metrics in illness_metrics.items():
            if metrics.get('accuracy') is not None:
                self.accuracy_by_illness.labels(
                    illness=illness,
                    model_version=model_version
                ).set(metrics['accuracy'])
    
    def record_feedback(self, model_version: str = "unknown") -> None:
        """
        Record feedback received.
        
        Args:
            model_version: Model version
        """
        self.feedback_total.labels(model_version=model_version).inc()
    
    def update_active_sessions(self, count: int) -> None:
        """
        Update active session count.
        
        Args:
            count: Number of active sessions
        """
        self.active_sessions.set(count)
    
    def record_error(self, error_type: str, model_version: str = "unknown") -> None:
        """
        Record an error.
        
        Args:
            error_type: Type of error
            model_version: Model version
        """
        self.errors_total.labels(
            error_type=error_type,
            model_version=model_version
        ).inc()
    
    def update_drift_metrics(
        self,
        feature_psi: Dict[str, float],
        ks_statistics: Dict[str, float]
    ) -> None:
        """
        Update drift detection metrics.
        
        Args:
            feature_psi: PSI scores by feature
            ks_statistics: KS statistics by feature
        """
        for feature, psi in feature_psi.items():
            self.feature_drift_psi.labels(feature=feature).set(psi)
        
        for feature, ks_stat in ks_statistics.items():
            self.ks_statistic.labels(feature=feature).set(ks_stat)
    
    def record_drift_event(self, drift_type: str) -> None:
        """
        Record a drift detection event.
        
        Args:
            drift_type: Type of drift detected
        """
        self.drift_events_total.labels(drift_type=drift_type).inc()
    
    def set_retraining_recommended(self, recommended: bool) -> None:
        """
        Set retraining recommendation flag.
        
        Args:
            recommended: Whether retraining is recommended
        """
        self.retraining_recommended.set(1 if recommended else 0)
    
    def set_last_training_timestamp(self, timestamp: datetime) -> None:
        """
        Set last training timestamp.
        
        Args:
            timestamp: Training timestamp
        """
        self.last_training_timestamp.set(timestamp.timestamp())
    
    def set_baseline_accuracy(self, accuracy: float) -> None:
        """
        Set baseline accuracy.
        
        Args:
            accuracy: Baseline accuracy value
        """
        self.baseline_accuracy.set(accuracy)
    
    def update_db_connections(self, active: int, idle: int) -> None:
        """
        Update database connection metrics.
        
        Args:
            active: Active connections
            idle: Idle connections
        """
        self.db_connections_active.set(active)
        self.db_connections_idle.set(idle)
    
    def record_cache_hit(self) -> None:
        """Record a cache hit."""
        self.cache_hits_total.inc()
    
    def record_cache_miss(self) -> None:
        """Record a cache miss."""
        self.cache_misses_total.inc()
    
    def record_external_api_call(self, api: str, duration_ms: float) -> None:
        """
        Record external API call.
        
        Args:
            api: API name (llm, location, translation)
            duration_ms: Call duration in milliseconds
        """
        self.external_api_duration.labels(api=api).observe(duration_ms)
    
    def set_model_info(
        self,
        version: str,
        training_date: str,
        accuracy: str,
        framework: str = "xgboost"
    ) -> None:
        """
        Set model information.
        
        Args:
            version: Model version
            training_date: Training date
            accuracy: Model accuracy
            framework: ML framework used
        """
        self.model_info.info({
            'version': version,
            'training_date': training_date,
            'accuracy': accuracy,
            'framework': framework
        })
    
    def get_metrics(self) -> bytes:
        """
        Get metrics in Prometheus format.
        
        Returns:
            Metrics in Prometheus text format
        """
        return generate_latest(self.registry)
    
    def get_content_type(self) -> str:
        """
        Get content type for metrics endpoint.
        
        Returns:
            Content type string
        """
        return CONTENT_TYPE_LATEST
