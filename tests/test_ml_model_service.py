"""
Unit tests for MLModelService.

Tests cover:
- Model loading and caching
- Feature vectorization
- Prediction generation with filtering and ranking
- Model versioning
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.ml.ml_model_service import MLModelService
from src.models.data_models import SymptomVector, SymptomInfo


class TestMLModelService:
    """Unit tests for MLModelService class."""
    
    @pytest.fixture
    def mock_mlflow_client(self):
        """Mock MLflow client."""
        with patch('src.ml.ml_model_service.MlflowClient') as mock_client:
            yield mock_client
    
    @pytest.fixture
    def mock_mlflow_load(self):
        """Mock mlflow.xgboost.load_model."""
        with patch('src.ml.ml_model_service.mlflow.xgboost.load_model') as mock_load:
            # Create a mock model with predict_proba method
            mock_model = Mock()
            mock_model.predict_proba = Mock()
            mock_load.return_value = mock_model
            yield mock_load, mock_model
    
    @pytest.fixture
    def service(self, mock_mlflow_client):
        """Create MLModelService instance."""
        return MLModelService(
            mlflow_tracking_uri="file:./test_mlruns",
            model_name="test_model",
            default_version="1"
        )
    
    def test_initialization(self, service):
        """Test service initialization."""
        assert service.model_name == "test_model"
        assert service.default_version == "1"
        assert service._active_version is None
        assert len(service._model_cache) == 0
    
    def test_load_model_from_cache(self, service, mock_mlflow_load):
        """Test loading model from cache."""
        mock_load, mock_model = mock_mlflow_load
        
        # First load - should call mlflow
        model1 = service.load_model("1")
        assert mock_load.call_count == 1
        assert model1 == mock_model
        
        # Second load - should use cache
        model2 = service.load_model("1")
        assert mock_load.call_count == 1  # Not called again
        assert model2 == mock_model
        assert "1" in service._model_cache
    
    def test_load_model_different_versions(self, service, mock_mlflow_load):
        """Test loading different model versions."""
        mock_load, mock_model = mock_mlflow_load
        
        # Load version 1
        service.load_model("1")
        assert mock_load.call_count == 1
        
        # Load version 2 - should call mlflow again
        service.load_model("2")
        assert mock_load.call_count == 2
        
        # Both should be cached
        assert "1" in service._model_cache
        assert "2" in service._model_cache
    
    def test_get_active_model(self, service):
        """Test getting active model version."""
        # Should return default version
        active = service.get_active_model()
        assert active == "1"
    
    def test_set_active_model(self, service, mock_mlflow_load):
        """Test setting active model version."""
        mock_load, mock_model = mock_mlflow_load
        
        service.set_active_model("2")
        assert service._active_version == "2"
        assert mock_load.call_count == 1  # Should load the model
    
    def test_vectorize_symptoms_empty(self, service):
        """Test vectorizing empty symptom vector."""
        symptom_vector = SymptomVector()
        features = service.vectorize_symptoms(symptom_vector)
        
        # Should have shape (1, num_features)
        num_symptoms = len(service.KNOWN_SYMPTOMS)
        expected_features = num_symptoms * 3  # presence + severity + duration
        assert features.shape == (1, expected_features)
        
        # All features should be zero
        assert np.all(features == 0)
    
    def test_vectorize_symptoms_single_symptom(self, service):
        """Test vectorizing single symptom."""
        symptom_vector = SymptomVector(
            symptoms={
                'fever': SymptomInfo(
                    present=True,
                    severity=8,
                    duration='1-3d',
                    description='High fever'
                )
            }
        )
        
        features = service.vectorize_symptoms(symptom_vector)
        
        # Check shape
        num_symptoms = len(service.KNOWN_SYMPTOMS)
        expected_features = num_symptoms * 3
        assert features.shape == (1, expected_features)
        
        # Find fever index
        fever_idx = service.KNOWN_SYMPTOMS.index('fever')
        
        # Check presence (first num_symptoms features)
        assert features[0, fever_idx] == 1.0
        
        # Check severity (next num_symptoms features)
        assert features[0, num_symptoms + fever_idx] == 0.8  # 8/10
        
        # Check duration (last num_symptoms features)
        # '1-3d' encodes to 1, normalized to 1/3
        assert features[0, 2 * num_symptoms + fever_idx] == pytest.approx(1/3)
    
    def test_vectorize_symptoms_multiple_symptoms(self, service):
        """Test vectorizing multiple symptoms."""
        symptom_vector = SymptomVector(
            symptoms={
                'fever': SymptomInfo(present=True, severity=9, duration='3-7d'),
                'cough': SymptomInfo(present=True, severity=7, duration='3-7d'),
                'headache': SymptomInfo(present=True, severity=6, duration='1-3d'),
            }
        )
        
        features = service.vectorize_symptoms(symptom_vector)
        num_symptoms = len(service.KNOWN_SYMPTOMS)
        
        # Check that all three symptoms are present
        fever_idx = service.KNOWN_SYMPTOMS.index('fever')
        cough_idx = service.KNOWN_SYMPTOMS.index('cough')
        headache_idx = service.KNOWN_SYMPTOMS.index('headache')
        
        assert features[0, fever_idx] == 1.0
        assert features[0, cough_idx] == 1.0
        assert features[0, headache_idx] == 1.0
        
        # Check severities
        assert features[0, num_symptoms + fever_idx] == 0.9
        assert features[0, num_symptoms + cough_idx] == 0.7
        assert features[0, num_symptoms + headache_idx] == 0.6
    
    def test_vectorize_symptoms_unknown_symptom(self, service):
        """Test vectorizing with unknown symptom (should be ignored)."""
        symptom_vector = SymptomVector(
            symptoms={
                'unknown_symptom': SymptomInfo(present=True, severity=5),
                'fever': SymptomInfo(present=True, severity=8),
            }
        )
        
        features = service.vectorize_symptoms(symptom_vector)
        
        # Fever should be present
        fever_idx = service.KNOWN_SYMPTOMS.index('fever')
        assert features[0, fever_idx] == 1.0
        
        # Unknown symptom should not cause errors
        # (it's simply not in the feature vector)
    
    def test_predict_basic(self, service, mock_mlflow_load):
        """Test basic prediction."""
        mock_load, mock_model = mock_mlflow_load
        
        # Mock predict_proba to return probabilities
        num_illnesses = len(service.KNOWN_ILLNESSES)
        probs = np.zeros(num_illnesses)
        probs[0] = 0.85  # common_cold
        probs[1] = 0.60  # influenza
        probs[2] = 0.40  # covid_19
        probs[3] = 0.25  # pneumonia (below threshold)
        mock_model.predict_proba.return_value = np.array([probs])
        
        symptom_vector = SymptomVector(
            symptoms={
                'fever': SymptomInfo(present=True, severity=8),
                'cough': SymptomInfo(present=True, severity=7),
            }
        )
        
        predictions = service.predict(symptom_vector)
        
        # Should return top 3 predictions above 0.30 threshold
        assert len(predictions) == 3
        
        # Check predictions are sorted by confidence descending
        assert predictions[0] == ('common_cold', 0.85)
        assert predictions[1] == ('influenza', 0.60)
        assert predictions[2] == ('covid_19', 0.40)
        
        # Verify model was called
        assert mock_model.predict_proba.call_count == 1
    
    def test_predict_confidence_threshold_filtering(self, service, mock_mlflow_load):
        """Test that predictions below confidence threshold are filtered out."""
        mock_load, mock_model = mock_mlflow_load
        
        # All predictions below threshold
        num_illnesses = len(service.KNOWN_ILLNESSES)
        probs = np.full(num_illnesses, 0.10)  # All below 0.30
        mock_model.predict_proba.return_value = np.array([probs])
        
        symptom_vector = SymptomVector(
            symptoms={'fever': SymptomInfo(present=True)}
        )
        
        predictions = service.predict(symptom_vector)
        
        # Should return empty list
        assert len(predictions) == 0
    
    def test_predict_top_k_limit(self, service, mock_mlflow_load):
        """Test that predictions are limited to top_k."""
        mock_load, mock_model = mock_mlflow_load
        
        # Create 5 predictions above threshold
        num_illnesses = len(service.KNOWN_ILLNESSES)
        probs = np.zeros(num_illnesses)
        probs[0] = 0.50
        probs[1] = 0.45
        probs[2] = 0.40
        probs[3] = 0.35
        probs[4] = 0.32
        mock_model.predict_proba.return_value = np.array([probs])
        
        symptom_vector = SymptomVector(
            symptoms={'fever': SymptomInfo(present=True)}
        )
        
        # Request top 3
        predictions = service.predict(symptom_vector, top_k=3)
        
        # Should return exactly 3
        assert len(predictions) == 3
        assert predictions[0][1] == 0.50
        assert predictions[1][1] == 0.45
        assert predictions[2][1] == 0.40
    
    def test_predict_ranking_descending(self, service, mock_mlflow_load):
        """Test that predictions are ranked in descending order by confidence."""
        mock_load, mock_model = mock_mlflow_load
        
        # Create predictions in random order
        num_illnesses = len(service.KNOWN_ILLNESSES)
        probs = np.zeros(num_illnesses)
        probs[5] = 0.35  # Should be 3rd
        probs[2] = 0.60  # Should be 1st
        probs[8] = 0.45  # Should be 2nd
        mock_model.predict_proba.return_value = np.array([probs])
        
        symptom_vector = SymptomVector(
            symptoms={'fever': SymptomInfo(present=True)}
        )
        
        predictions = service.predict(symptom_vector)
        
        # Check descending order
        assert len(predictions) == 3
        assert predictions[0][1] == 0.60
        assert predictions[1][1] == 0.45
        assert predictions[2][1] == 0.35
        
        # Verify each prediction has higher confidence than the next
        for i in range(len(predictions) - 1):
            assert predictions[i][1] >= predictions[i+1][1]
    
    def test_predict_custom_threshold(self, service, mock_mlflow_load):
        """Test prediction with custom confidence threshold."""
        mock_load, mock_model = mock_mlflow_load
        
        num_illnesses = len(service.KNOWN_ILLNESSES)
        probs = np.zeros(num_illnesses)
        probs[0] = 0.70
        probs[1] = 0.55
        probs[2] = 0.40  # Below custom threshold of 0.50
        mock_model.predict_proba.return_value = np.array([probs])
        
        symptom_vector = SymptomVector(
            symptoms={'fever': SymptomInfo(present=True)}
        )
        
        predictions = service.predict(symptom_vector, confidence_threshold=0.50)
        
        # Should only return 2 predictions
        assert len(predictions) == 2
        assert predictions[0][1] == 0.70
        assert predictions[1][1] == 0.55
    
    def test_predict_with_specific_version(self, service, mock_mlflow_load):
        """Test prediction with specific model version."""
        mock_load, mock_model = mock_mlflow_load
        
        num_illnesses = len(service.KNOWN_ILLNESSES)
        probs = np.zeros(num_illnesses)
        probs[0] = 0.80
        mock_model.predict_proba.return_value = np.array([probs])
        
        symptom_vector = SymptomVector(
            symptoms={'fever': SymptomInfo(present=True)}
        )
        
        predictions = service.predict(symptom_vector, model_version="2")
        
        # Verify correct model URI was used
        mock_load.assert_called_with("models:/test_model/2")
        assert len(predictions) > 0
    
    def test_clear_cache(self, service, mock_mlflow_load):
        """Test clearing model cache."""
        mock_load, mock_model = mock_mlflow_load
        
        # Load a model
        service.load_model("1")
        assert len(service._model_cache) == 1
        
        # Clear cache
        service.clear_cache()
        assert len(service._model_cache) == 0
    
    def test_get_cache_info(self, service, mock_mlflow_load):
        """Test getting cache information."""
        mock_load, mock_model = mock_mlflow_load
        
        # Load models
        service.load_model("1")
        service.load_model("2")
        
        cache_info = service.get_cache_info()
        
        assert "1" in cache_info
        assert "2" in cache_info
        assert isinstance(cache_info["1"], datetime)
        assert isinstance(cache_info["2"], datetime)
    
    def test_vectorize_symptoms_with_missing_attributes(self, service):
        """Test vectorizing symptoms with missing severity or duration."""
        symptom_vector = SymptomVector(
            symptoms={
                'fever': SymptomInfo(present=True),  # No severity or duration
                'cough': SymptomInfo(present=True, severity=7),  # No duration
                'headache': SymptomInfo(present=True, duration='1-3d'),  # No severity
            }
        )
        
        features = service.vectorize_symptoms(symptom_vector)
        num_symptoms = len(service.KNOWN_SYMPTOMS)
        
        # All should have presence set
        fever_idx = service.KNOWN_SYMPTOMS.index('fever')
        cough_idx = service.KNOWN_SYMPTOMS.index('cough')
        headache_idx = service.KNOWN_SYMPTOMS.index('headache')
        
        assert features[0, fever_idx] == 1.0
        assert features[0, cough_idx] == 1.0
        assert features[0, headache_idx] == 1.0
        
        # Fever should have no severity or duration
        assert features[0, num_symptoms + fever_idx] == 0.0
        assert features[0, 2 * num_symptoms + fever_idx] == 0.0
        
        # Cough should have severity but no duration
        assert features[0, num_symptoms + cough_idx] == 0.7
        assert features[0, 2 * num_symptoms + cough_idx] == 0.0
        
        # Headache should have duration but no severity
        assert features[0, num_symptoms + headache_idx] == 0.0
        assert features[0, 2 * num_symptoms + headache_idx] > 0.0
    
    def test_predict_empty_symptom_vector(self, service, mock_mlflow_load):
        """Test prediction with empty symptom vector."""
        mock_load, mock_model = mock_mlflow_load
        
        num_illnesses = len(service.KNOWN_ILLNESSES)
        probs = np.zeros(num_illnesses)
        probs[0] = 0.40
        mock_model.predict_proba.return_value = np.array([probs])
        
        symptom_vector = SymptomVector()  # Empty
        
        predictions = service.predict(symptom_vector)
        
        # Should still work, just with all-zero features
        assert isinstance(predictions, list)
        assert mock_model.predict_proba.call_count == 1


class TestMLModelServiceIntegration:
    """Integration tests for MLModelService (require MLflow setup)."""
    
    @pytest.mark.skip(reason="Requires MLflow server and trained model")
    def test_load_real_model(self):
        """Test loading a real model from MLflow (integration test)."""
        service = MLModelService(
            mlflow_tracking_uri="http://localhost:5000",
            model_name="illness_prediction_model"
        )
        
        model = service.load_model()
        assert model is not None
    
    @pytest.mark.skip(reason="Requires MLflow server and trained model")
    def test_real_prediction(self):
        """Test making a real prediction (integration test)."""
        service = MLModelService(
            mlflow_tracking_uri="http://localhost:5000",
            model_name="illness_prediction_model"
        )
        
        symptom_vector = SymptomVector(
            symptoms={
                'fever': SymptomInfo(present=True, severity=8, duration='1-3d'),
                'cough': SymptomInfo(present=True, severity=7, duration='3-7d'),
                'fatigue': SymptomInfo(present=True, severity=6, duration='3-7d'),
            }
        )
        
        predictions = service.predict(symptom_vector)
        
        assert len(predictions) > 0
        assert all(conf >= 0.30 for _, conf in predictions)
        assert all(predictions[i][1] >= predictions[i+1][1] for i in range(len(predictions)-1))
