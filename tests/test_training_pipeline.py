"""
Unit tests for TrainingPipeline.

Tests dataset validation, feature engineering, model training, and evaluation.
"""

import pytest
import pandas as pd
import numpy as np
from src.mlops.training_pipeline import TrainingPipeline, TrainingConfig, DatasetValidationReport


class TestDatasetValidation:
    """Test dataset validation functionality."""
    
    def test_validate_empty_dataset(self):
        """Test validation of empty dataset."""
        pipeline = TrainingPipeline()
        dataset = pd.DataFrame()
        
        report = pipeline.validate_dataset(dataset)
        
        assert report.is_valid is False
        assert "empty" in report.errors[0].lower()
    
    def test_validate_dataset_missing_label_column(self):
        """Test validation when label column is missing."""
        pipeline = TrainingPipeline()
        dataset = pd.DataFrame({
            'feature1': [1, 2, 3],
            'feature2': [4, 5, 6]
        })
        
        report = pipeline.validate_dataset(dataset)
        
        assert report.is_valid is False
        assert report.schema_valid is False
        assert any('label' in err.lower() for err in report.errors)
    
    def test_validate_dataset_no_features(self):
        """Test validation when no feature columns exist."""
        pipeline = TrainingPipeline()
        dataset = pd.DataFrame({
            'label': [0, 1, 2]
        })
        
        report = pipeline.validate_dataset(dataset)
        
        assert report.is_valid is False
        assert any('feature' in err.lower() for err in report.errors)
    
    def test_validate_valid_dataset(self):
        """Test validation of valid dataset."""
        pipeline = TrainingPipeline()
        dataset = pd.DataFrame({
            'feature1': np.random.rand(100),
            'feature2': np.random.rand(100),
            'feature3': np.random.rand(100),
            'label': np.random.randint(0, 5, 100)
        })
        
        report = pipeline.validate_dataset(dataset)
        
        assert report.is_valid is True
        assert report.schema_valid is True
        assert report.total_samples == 100
        assert report.num_features == 3
    
    def test_validate_dataset_with_missing_values(self):
        """Test validation with missing values."""
        pipeline = TrainingPipeline()
        dataset = pd.DataFrame({
            'feature1': [1, 2, np.nan, 4, 5] * 20,
            'feature2': [1, 2, 3, 4, 5] * 20,
            'label': [0, 1, 0, 1, 0] * 20
        })
        
        report = pipeline.validate_dataset(dataset)
        
        # Should have warnings about missing values
        assert len(report.warnings) > 0
    
    def test_validate_dataset_class_imbalance(self):
        """Test validation with class imbalance."""
        pipeline = TrainingPipeline()
        # Create severely imbalanced dataset
        labels = [0] * 95 + [1] * 5
        dataset = pd.DataFrame({
            'feature1': np.random.rand(100),
            'feature2': np.random.rand(100),
            'label': labels
        })
        
        report = pipeline.validate_dataset(dataset)
        
        # Should have warnings about class imbalance
        assert len(report.warnings) > 0


class TestFeatureEngineering:
    """Test feature engineering functionality."""
    
    def test_engineer_features_returns_dataframe(self):
        """Test that feature engineering returns a DataFrame."""
        pipeline = TrainingPipeline()
        dataset = pd.DataFrame({
            'feature1': [1, 2, 3],
            'feature2': [4, 5, 6],
            'label': [0, 1, 0]
        })
        
        result = pipeline.engineer_features(dataset)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(dataset)


class TestModelTraining:
    """Test model training functionality."""
    
    def test_train_model_creates_model(self):
        """Test that training creates a model."""
        pipeline = TrainingPipeline()
        
        # Create simple dataset
        X_train = pd.DataFrame({
            'feature1': np.random.rand(100),
            'feature2': np.random.rand(100)
        })
        y_train = pd.Series(np.random.randint(0, 3, 100))
        
        X_val = pd.DataFrame({
            'feature1': np.random.rand(20),
            'feature2': np.random.rand(20)
        })
        y_val = pd.Series(np.random.randint(0, 3, 20))
        
        model = pipeline.train_model(X_train, y_train, X_val, y_val)
        
        assert model is not None
        assert pipeline.model is not None
    
    def test_train_model_with_custom_config(self):
        """Test training with custom configuration."""
        config = TrainingConfig(
            max_depth=5,
            learning_rate=0.05,
            n_estimators=50
        )
        pipeline = TrainingPipeline(config=config)
        
        X_train = pd.DataFrame({
            'feature1': np.random.rand(100),
            'feature2': np.random.rand(100)
        })
        y_train = pd.Series(np.random.randint(0, 3, 100))
        
        X_val = pd.DataFrame({
            'feature1': np.random.rand(20),
            'feature2': np.random.rand(20)
        })
        y_val = pd.Series(np.random.randint(0, 3, 20))
        
        model = pipeline.train_model(X_train, y_train, X_val, y_val)
        
        assert model.max_depth == 5
        assert model.n_estimators == 50


class TestModelEvaluation:
    """Test model evaluation functionality."""
    
    def test_evaluate_model_returns_metrics(self):
        """Test that evaluation returns metrics."""
        pipeline = TrainingPipeline()
        
        # Train a simple model
        X_train = pd.DataFrame({
            'feature1': np.random.rand(100),
            'feature2': np.random.rand(100)
        })
        y_train = pd.Series(np.random.randint(0, 3, 100))
        
        X_val = pd.DataFrame({
            'feature1': np.random.rand(20),
            'feature2': np.random.rand(20)
        })
        y_val = pd.Series(np.random.randint(0, 3, 20))
        
        model = pipeline.train_model(X_train, y_train, X_val, y_val)
        metrics = pipeline.evaluate_model(model, X_val, y_val, "v1.0.0")
        
        assert metrics is not None
        assert 0 <= metrics.accuracy <= 1
        assert 0 <= metrics.precision <= 1
        assert 0 <= metrics.recall <= 1
        assert 0 <= metrics.f1_score <= 1
        assert metrics.top_3_accuracy is not None
    
    def test_evaluate_model_computes_per_class_metrics(self):
        """Test that per-class metrics are computed."""
        pipeline = TrainingPipeline()
        
        X_train = pd.DataFrame({
            'feature1': np.random.rand(100),
            'feature2': np.random.rand(100)
        })
        y_train = pd.Series(np.random.randint(0, 3, 100))
        
        X_val = pd.DataFrame({
            'feature1': np.random.rand(20),
            'feature2': np.random.rand(20)
        })
        y_val = pd.Series(np.random.randint(0, 3, 20))
        
        model = pipeline.train_model(X_train, y_train, X_val, y_val)
        metrics = pipeline.evaluate_model(model, X_val, y_val, "v1.0.0")
        
        assert len(metrics.per_class_metrics) > 0
        
        # Check that each class has metrics
        for class_metrics in metrics.per_class_metrics.values():
            assert 0 <= class_metrics.precision <= 1
            assert 0 <= class_metrics.recall <= 1
            assert 0 <= class_metrics.f1_score <= 1
            assert class_metrics.support >= 0


class TestTopKAccuracy:
    """Test top-k accuracy computation."""
    
    def test_compute_top_k_accuracy(self):
        """Test top-k accuracy calculation."""
        pipeline = TrainingPipeline()
        
        # Create mock predictions
        y_true = pd.Series([0, 1, 2, 0, 1])
        y_pred_proba = np.array([
            [0.7, 0.2, 0.1],  # Correct: 0
            [0.1, 0.6, 0.3],  # Correct: 1
            [0.2, 0.3, 0.5],  # Correct: 2
            [0.4, 0.4, 0.2],  # Correct: 0 (in top 2)
            [0.3, 0.4, 0.3],  # Correct: 1
        ])
        
        top_3_acc = pipeline._compute_top_k_accuracy(y_true, y_pred_proba, k=3)
        
        # All should be in top 3
        assert top_3_acc == 1.0


class TestTrainingPipeline:
    """Test complete training pipeline."""
    
    def test_run_training_pipeline_success(self):
        """Test successful pipeline execution."""
        pipeline = TrainingPipeline()
        
        # Create valid dataset
        dataset = pd.DataFrame({
            'feature1': np.random.rand(100),
            'feature2': np.random.rand(100),
            'feature3': np.random.rand(100),
            'label': np.random.randint(0, 3, 100)
        })
        
        model, metrics, report = pipeline.run_training_pipeline(
            dataset,
            model_version="v1.0.0",
            test_size=0.2
        )
        
        assert model is not None
        assert metrics is not None
        assert report.is_valid is True
        assert metrics.model_version == "v1.0.0"
    
    def test_run_training_pipeline_invalid_dataset(self):
        """Test pipeline with invalid dataset."""
        pipeline = TrainingPipeline()
        
        # Create invalid dataset (no features)
        dataset = pd.DataFrame({
            'label': [0, 1, 2]
        })
        
        with pytest.raises(ValueError, match="validation failed"):
            pipeline.run_training_pipeline(dataset, "v1.0.0")
    
    def test_run_training_pipeline_with_warnings(self):
        """Test pipeline with dataset that has warnings."""
        pipeline = TrainingPipeline()
        
        # Create dataset with some issues but still valid
        # Use 3 classes to avoid binary classification issues
        dataset = pd.DataFrame({
            'feature1': np.random.rand(100),
            'feature2': np.random.rand(100),
            'label': [0] * 80 + [1] * 15 + [2] * 5  # Imbalanced
        })
        
        model, metrics, report = pipeline.run_training_pipeline(
            dataset,
            model_version="v1.0.0"
        )
        
        assert model is not None
        assert len(report.warnings) > 0


class TestModelSaveLoad:
    """Test model save and load functionality."""
    
    def test_save_and_load_model(self, tmp_path):
        """Test saving and loading a model."""
        pipeline = TrainingPipeline()
        
        # Train a simple model
        X_train = pd.DataFrame({
            'feature1': np.random.rand(100),
            'feature2': np.random.rand(100)
        })
        y_train = pd.Series(np.random.randint(0, 3, 100))
        
        X_val = pd.DataFrame({
            'feature1': np.random.rand(20),
            'feature2': np.random.rand(20)
        })
        y_val = pd.Series(np.random.randint(0, 3, 20))
        
        model = pipeline.train_model(X_train, y_train, X_val, y_val)
        
        # Save model
        model_path = tmp_path / "model.json"
        pipeline.save_model(model, str(model_path))
        
        assert model_path.exists()
        
        # Load model
        new_pipeline = TrainingPipeline()
        loaded_model = new_pipeline.load_model(str(model_path))
        
        assert loaded_model is not None


class TestTrainingConfig:
    """Test training configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = TrainingConfig()
        
        assert config.max_depth == 8
        assert config.learning_rate == 0.1
        assert config.n_estimators == 200
        assert config.min_accuracy == 0.85
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = TrainingConfig(
            max_depth=10,
            learning_rate=0.05,
            min_accuracy=0.90
        )
        
        assert config.max_depth == 10
        assert config.learning_rate == 0.05
        assert config.min_accuracy == 0.90


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
