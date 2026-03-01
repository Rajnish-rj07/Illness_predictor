"""
Property-based tests for TrainingPipeline.

Tests universal correctness properties for model training using hypothesis.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
import pandas as pd
import numpy as np
from src.mlops.training_pipeline import TrainingPipeline, TrainingConfig


# Custom strategies
@st.composite
def valid_datasets(draw, min_samples=50, max_samples=200, min_features=2, max_features=10):
    """Generate valid training datasets."""
    n_samples = draw(st.integers(min_value=min_samples, max_value=max_samples))
    n_features = draw(st.integers(min_value=min_features, max_value=max_features))
    n_classes = draw(st.integers(min_value=2, max_value=5))
    
    # Generate features
    data = {}
    for i in range(n_features):
        data[f'feature{i}'] = np.random.rand(n_samples)
    
    # Generate labels with reasonable class balance
    labels = np.random.randint(0, n_classes, n_samples)
    data['label'] = labels
    
    return pd.DataFrame(data)


@st.composite
def invalid_datasets(draw):
    """Generate invalid training datasets."""
    choice = draw(st.integers(min_value=0, max_value=2))
    
    if choice == 0:
        # Empty dataset
        return pd.DataFrame()
    elif choice == 1:
        # Missing label column
        return pd.DataFrame({
            'feature1': [1, 2, 3],
            'feature2': [4, 5, 6]
        })
    else:
        # No features
        return pd.DataFrame({
            'label': [0, 1, 2]
        })


class TestProperty40TrainingTrigger:
    """
    Property 40: Training trigger on new data
    
    For any new Training_Dataset marked as ready, the MLOps_Pipeline 
    should initiate a training job.
    
    Validates: Requirements 5.1
    """
    
    @given(dataset=valid_datasets())
    @settings(max_examples=10, deadline=None)
    def test_new_dataset_triggers_training(self, dataset):
        """Test that any valid new dataset triggers training."""
        pipeline = TrainingPipeline()
        
        # Training should complete successfully for any valid dataset
        model, metrics, report = pipeline.run_training_pipeline(
            dataset,
            model_version="v1.0.0"
        )
        
        assert model is not None
        assert metrics is not None
        assert report.is_valid is True


class TestProperty41DatasetValidation:
    """
    Property 41: Dataset validation before training
    
    For any training job, the pipeline should validate the dataset 
    before starting model training, and reject invalid datasets.
    
    Validates: Requirements 5.2
    """
    
    @given(dataset=invalid_datasets())
    def test_invalid_datasets_rejected(self, dataset):
        """Test that invalid datasets are rejected before training."""
        pipeline = TrainingPipeline()
        
        # Invalid datasets should raise ValueError
        with pytest.raises(ValueError, match="validation failed"):
            pipeline.run_training_pipeline(dataset, "v1.0.0")
    
    @given(dataset=valid_datasets())
    @settings(max_examples=10, deadline=None)
    def test_valid_datasets_accepted(self, dataset):
        """Test that valid datasets pass validation."""
        pipeline = TrainingPipeline()
        
        report = pipeline.validate_dataset(dataset)
        
        assert report.is_valid is True
        assert report.schema_valid is True
        assert report.total_samples > 0
        assert report.num_features > 0
    
    @given(
        n_samples=st.integers(min_value=50, max_value=200),
        n_features=st.integers(min_value=2, max_value=10)
    )
    def test_validation_checks_schema(self, n_samples, n_features):
        """Test that validation checks dataset schema."""
        pipeline = TrainingPipeline()
        
        # Create dataset with proper schema
        data = {f'feature{i}': np.random.rand(n_samples) for i in range(n_features)}
        data['label'] = np.random.randint(0, 3, n_samples)
        dataset = pd.DataFrame(data)
        
        report = pipeline.validate_dataset(dataset)
        
        assert report.schema_valid is True
        assert report.num_features == n_features


class TestProperty42MetricsComputation:
    """
    Property 42: Metrics computation completeness
    
    For any completed training run, the pipeline should compute and store 
    all required metrics: accuracy, precision, recall, F1 score, and top-3 accuracy.
    
    Validates: Requirements 5.3, 8.1
    """
    
    @given(dataset=valid_datasets())
    @settings(max_examples=10, deadline=None)
    def test_all_metrics_computed(self, dataset):
        """Test that all required metrics are computed."""
        pipeline = TrainingPipeline()
        
        model, metrics, report = pipeline.run_training_pipeline(
            dataset,
            model_version="v1.0.0"
        )
        
        # All metrics should be present
        assert metrics.accuracy is not None
        assert metrics.precision is not None
        assert metrics.recall is not None
        assert metrics.f1_score is not None
        assert metrics.top_3_accuracy is not None
        
        # All metrics should be in valid range [0, 1]
        assert 0 <= metrics.accuracy <= 1
        assert 0 <= metrics.precision <= 1
        assert 0 <= metrics.recall <= 1
        assert 0 <= metrics.f1_score <= 1
        assert 0 <= metrics.top_3_accuracy <= 1
    
    @given(dataset=valid_datasets())
    @settings(max_examples=10, deadline=None)
    def test_per_class_metrics_computed(self, dataset):
        """Test that per-class metrics are computed."""
        pipeline = TrainingPipeline()
        
        model, metrics, report = pipeline.run_training_pipeline(
            dataset,
            model_version="v1.0.0"
        )
        
        # Per-class metrics should exist
        assert len(metrics.per_class_metrics) > 0
        
        # Each class should have complete metrics
        for class_metrics in metrics.per_class_metrics.values():
            assert 0 <= class_metrics.precision <= 1
            assert 0 <= class_metrics.recall <= 1
            assert 0 <= class_metrics.f1_score <= 1
            assert class_metrics.support >= 0
    
    @given(dataset=valid_datasets())
    @settings(max_examples=10, deadline=None)
    def test_metrics_have_timestamp(self, dataset):
        """Test that metrics include timestamp."""
        pipeline = TrainingPipeline()
        
        model, metrics, report = pipeline.run_training_pipeline(
            dataset,
            model_version="v1.0.0"
        )
        
        assert metrics.timestamp is not None
        assert metrics.model_version == "v1.0.0"


class TestProperty43ModelArtifactStorage:
    """
    Property 43: Model artifact storage
    
    For any successfully trained model, the pipeline should store the model file, 
    version metadata, training metrics, and explainability report.
    
    Validates: Requirements 5.4, 14.5
    """
    
    @given(dataset=valid_datasets())
    @settings(
        max_examples=5,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_model_can_be_saved(self, dataset, tmp_path):
        """Test that trained models can be saved."""
        pipeline = TrainingPipeline()
        
        model, metrics, report = pipeline.run_training_pipeline(
            dataset,
            model_version="v1.0.0"
        )
        
        # Model should be saveable
        model_path = tmp_path / "model.json"
        pipeline.save_model(model, str(model_path))
        
        assert model_path.exists()
    
    @given(dataset=valid_datasets())
    @settings(
        max_examples=5,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_model_can_be_loaded(self, dataset, tmp_path):
        """Test that saved models can be loaded."""
        pipeline = TrainingPipeline()
        
        model, metrics, report = pipeline.run_training_pipeline(
            dataset,
            model_version="v1.0.0"
        )
        
        # Save model
        model_path = tmp_path / "model.json"
        pipeline.save_model(model, str(model_path))
        
        # Load model
        new_pipeline = TrainingPipeline()
        loaded_model = new_pipeline.load_model(str(model_path))
        
        assert loaded_model is not None
    
    @given(dataset=valid_datasets())
    @settings(max_examples=5, deadline=None)
    def test_metrics_stored_with_version(self, dataset):
        """Test that metrics are stored with model version."""
        pipeline = TrainingPipeline()
        
        version = "v2.5.1"
        model, metrics, report = pipeline.run_training_pipeline(
            dataset,
            model_version=version
        )
        
        assert metrics.model_version == version


class TestTrainingPipelineInvariants:
    """Test training pipeline invariants."""
    
    @given(dataset=valid_datasets())
    @settings(max_examples=10, deadline=None)
    def test_training_is_deterministic(self, dataset):
        """Test that training with same seed produces consistent results."""
        config = TrainingConfig(random_state=42)
        
        # Train twice with same config
        pipeline1 = TrainingPipeline(config=config)
        model1, metrics1, _ = pipeline1.run_training_pipeline(
            dataset.copy(),
            model_version="v1.0.0"
        )
        
        pipeline2 = TrainingPipeline(config=config)
        model2, metrics2, _ = pipeline2.run_training_pipeline(
            dataset.copy(),
            model_version="v1.0.0"
        )
        
        # Metrics should be very close (allowing for small floating point differences)
        assert abs(metrics1.accuracy - metrics2.accuracy) < 0.01
    
    @given(
        dataset=valid_datasets(),
        test_size=st.floats(min_value=0.1, max_value=0.4)
    )
    @settings(max_examples=5, deadline=None)
    def test_test_size_affects_split(self, dataset, test_size):
        """Test that test_size parameter affects data split."""
        pipeline = TrainingPipeline()
        
        # Should complete successfully with any valid test_size
        model, metrics, report = pipeline.run_training_pipeline(
            dataset,
            model_version="v1.0.0",
            test_size=test_size
        )
        
        assert model is not None
        assert metrics is not None
    
    @given(dataset=valid_datasets())
    @settings(max_examples=10, deadline=None)
    def test_top_3_accuracy_greater_than_accuracy(self, dataset):
        """Test that top-3 accuracy is >= regular accuracy."""
        pipeline = TrainingPipeline()
        
        model, metrics, report = pipeline.run_training_pipeline(
            dataset,
            model_version="v1.0.0"
        )
        
        # Top-3 accuracy should always be >= regular accuracy
        assert metrics.top_3_accuracy >= metrics.accuracy


class TestDatasetValidationProperties:
    """Test dataset validation properties."""
    
    @given(
        n_samples=st.integers(min_value=1, max_value=1000),
        n_features=st.integers(min_value=1, max_value=50)
    )
    def test_validation_report_has_correct_counts(self, n_samples, n_features):
        """Test that validation report has correct sample and feature counts."""
        pipeline = TrainingPipeline()
        
        # Create dataset
        data = {f'feature{i}': np.random.rand(n_samples) for i in range(n_features)}
        data['label'] = np.random.randint(0, 3, n_samples)
        dataset = pd.DataFrame(data)
        
        report = pipeline.validate_dataset(dataset)
        
        assert report.total_samples == n_samples
        assert report.num_features == n_features
    
    @given(dataset=valid_datasets())
    def test_validation_is_idempotent(self, dataset):
        """Test that validating same dataset multiple times gives same result."""
        pipeline = TrainingPipeline()
        
        report1 = pipeline.validate_dataset(dataset)
        report2 = pipeline.validate_dataset(dataset)
        
        assert report1.is_valid == report2.is_valid
        assert report1.total_samples == report2.total_samples
        assert report1.num_features == report2.num_features


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
