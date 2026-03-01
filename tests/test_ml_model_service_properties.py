"""
Property-based tests for MLModelService.

These tests validate universal properties that should hold across all inputs:
- Property 8: Prediction generation completeness
- Property 9: Confidence threshold filtering
- Property 10: Prediction ranking invariant

Validates: Requirements 3.1, 3.3, 3.4
"""

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from unittest.mock import Mock, patch

from src.ml.ml_model_service import MLModelService
from src.models.data_models import SymptomVector, SymptomInfo


# Custom strategies for generating test data

@st.composite
def symptom_info_strategy(draw):
    """Generate random SymptomInfo objects."""
    present = draw(st.booleans())
    severity = draw(st.one_of(st.none(), st.integers(min_value=1, max_value=10)))
    duration = draw(st.one_of(st.none(), st.sampled_from(['<1d', '1-3d', '3-7d', '>7d'])))
    description = draw(st.text(min_size=0, max_size=100))
    
    return SymptomInfo(
        present=present,
        severity=severity,
        duration=duration,
        description=description
    )


@st.composite
def symptom_vector_strategy(draw):
    """Generate random SymptomVector objects."""
    # Sample a subset of known symptoms
    num_symptoms = draw(st.integers(min_value=0, max_value=20))
    
    # Use a fixed list of symptoms for testing
    available_symptoms = [
        'fever', 'cough', 'headache', 'fatigue', 'sore_throat',
        'shortness_of_breath', 'body_aches', 'nausea', 'vomiting',
        'diarrhea', 'chills', 'congestion', 'runny_nose', 'chest_pain',
        'dizziness', 'abdominal_pain', 'rash', 'joint_pain', 'muscle_pain',
        'weakness'
    ]
    
    selected_symptoms = draw(st.lists(
        st.sampled_from(available_symptoms),
        min_size=num_symptoms,
        max_size=num_symptoms,
        unique=True
    ))
    
    symptoms = {}
    for symptom_name in selected_symptoms:
        symptoms[symptom_name] = draw(symptom_info_strategy())
    
    question_count = draw(st.integers(min_value=0, max_value=15))
    confidence_threshold_met = draw(st.booleans())
    
    return SymptomVector(
        symptoms=symptoms,
        question_count=question_count,
        confidence_threshold_met=confidence_threshold_met
    )


@st.composite
def prediction_probabilities_strategy(draw, num_classes=200):
    """Generate random prediction probabilities that sum to 1."""
    # Generate random probabilities
    raw_probs = draw(st.lists(
        st.floats(min_value=0.0, max_value=1.0),
        min_size=num_classes,
        max_size=num_classes
    ))
    
    # Normalize to sum to 1
    total = sum(raw_probs)
    if total > 0:
        normalized = [p / total for p in raw_probs]
    else:
        normalized = [1.0 / num_classes] * num_classes
    
    return np.array(normalized)


class TestMLModelServiceProperties:
    """Property-based tests for MLModelService."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a mocked MLModelService for property testing."""
        with patch('src.ml.ml_model_service.MlflowClient'):
            with patch('src.ml.ml_model_service.mlflow.xgboost.load_model') as mock_load:
                # Create mock model
                mock_model = Mock()
                mock_load.return_value = mock_model
                
                service = MLModelService(
                    mlflow_tracking_uri="file:./test_mlruns",
                    model_name="test_model",
                    default_version="1"
                )
                
                yield service, mock_model
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_8_prediction_generation_completeness(self, symptom_vector, mock_service):
        """
        Feature: illness-prediction-system, Property 8: Prediction generation completeness
        
        For any completed SymptomVector, the ML_Model should generate at least one 
        prediction (or explicitly indicate insufficient information).
        
        **Validates: Requirements 3.1**
        """
        service, mock_model = mock_service
        
        # Generate probabilities with at least one above threshold
        num_illnesses = len(service.KNOWN_ILLNESSES)
        probs = np.zeros(num_illnesses)
        probs[0] = 0.50  # Ensure at least one prediction above 0.30
        probs[1] = 0.30  # Another at threshold
        
        mock_model.predict_proba.return_value = np.array([probs])
        
        # Make prediction
        predictions = service.predict(symptom_vector)
        
        # Should generate predictions (at least the ones we set)
        assert isinstance(predictions, list)
        assert len(predictions) >= 1  # At least one prediction
        
        # Each prediction should be a tuple of (illness_name, confidence)
        for illness, confidence in predictions:
            assert isinstance(illness, str)
            assert isinstance(confidence, float)
    
    @given(
        symptom_vector=symptom_vector_strategy(),
        probabilities=prediction_probabilities_strategy()
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_9_confidence_threshold_filtering(self, symptom_vector, probabilities, mock_service):
        """
        Feature: illness-prediction-system, Property 9: Confidence threshold filtering
        
        For any set of predictions returned to the user, all predictions should have 
        confidence scores >= 30%.
        
        **Validates: Requirements 3.3**
        """
        service, mock_model = mock_service
        
        # Use the generated probabilities
        mock_model.predict_proba.return_value = np.array([probabilities])
        
        # Make prediction with default threshold (0.30)
        predictions = service.predict(symptom_vector)
        
        # All returned predictions must have confidence >= 0.30
        for illness, confidence in predictions:
            assert confidence >= 0.30, (
                f"Prediction {illness} has confidence {confidence} < 0.30"
            )
    
    @given(
        symptom_vector=symptom_vector_strategy(),
        probabilities=prediction_probabilities_strategy()
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_10_prediction_ranking_invariant(self, symptom_vector, probabilities, mock_service):
        """
        Feature: illness-prediction-system, Property 10: Prediction ranking invariant
        
        For any list of predictions, each prediction should have a confidence score 
        greater than or equal to the next prediction in the list (descending order).
        
        **Validates: Requirements 3.4**
        """
        service, mock_model = mock_service
        
        # Use the generated probabilities
        mock_model.predict_proba.return_value = np.array([probabilities])
        
        # Make prediction
        predictions = service.predict(symptom_vector)
        
        # Verify descending order
        for i in range(len(predictions) - 1):
            current_confidence = predictions[i][1]
            next_confidence = predictions[i + 1][1]
            
            assert current_confidence >= next_confidence, (
                f"Predictions not in descending order: "
                f"{predictions[i][0]}({current_confidence}) < "
                f"{predictions[i+1][0]}({next_confidence})"
            )
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_vectorization_shape_consistency(self, symptom_vector, mock_service):
        """
        Property: Feature vectorization produces consistent shape.
        
        For any SymptomVector, the vectorized features should have a consistent shape
        matching the expected number of features.
        """
        service, _ = mock_service
        
        features = service.vectorize_symptoms(symptom_vector)
        
        # Check shape
        num_symptoms = len(service.KNOWN_SYMPTOMS)
        expected_features = num_symptoms * 3  # presence + severity + duration
        
        assert features.shape == (1, expected_features), (
            f"Feature shape {features.shape} does not match expected (1, {expected_features})"
        )
        
        # Check data type
        assert features.dtype in [np.float32, np.float64]
        
        # Check all values are finite
        assert np.all(np.isfinite(features))
    
    @given(
        symptom_vector=symptom_vector_strategy(),
        top_k=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_top_k_limit(self, symptom_vector, top_k, mock_service):
        """
        Property: Predictions are limited to top_k.
        
        For any symptom vector and top_k value, the number of returned predictions
        should not exceed top_k.
        
        **Validates: Requirements 3.2**
        """
        service, mock_model = mock_service
        
        # Generate probabilities with many above threshold
        num_illnesses = len(service.KNOWN_ILLNESSES)
        probs = np.full(num_illnesses, 0.40)  # All above threshold
        mock_model.predict_proba.return_value = np.array([probs])
        
        # Make prediction with specified top_k
        predictions = service.predict(symptom_vector, top_k=top_k)
        
        # Should not exceed top_k
        assert len(predictions) <= top_k, (
            f"Returned {len(predictions)} predictions, expected at most {top_k}"
        )
    
    @given(
        symptom_vector=symptom_vector_strategy(),
        threshold=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_custom_threshold_filtering(self, symptom_vector, threshold, mock_service):
        """
        Property: Custom confidence threshold is respected.
        
        For any symptom vector and confidence threshold, all returned predictions
        should have confidence >= threshold.
        """
        service, mock_model = mock_service
        
        # Generate random probabilities
        num_illnesses = len(service.KNOWN_ILLNESSES)
        probs = np.random.rand(num_illnesses)
        probs = probs / probs.sum()  # Normalize
        mock_model.predict_proba.return_value = np.array([probs])
        
        # Make prediction with custom threshold
        predictions = service.predict(symptom_vector, confidence_threshold=threshold)
        
        # All predictions should meet threshold
        for illness, confidence in predictions:
            assert confidence >= threshold, (
                f"Prediction {illness} has confidence {confidence} < {threshold}"
            )
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_vectorization_bounds(self, symptom_vector, mock_service):
        """
        Property: Vectorized features are within valid bounds.
        
        For any SymptomVector, all feature values should be in [0, 1] range.
        """
        service, _ = mock_service
        
        features = service.vectorize_symptoms(symptom_vector)
        
        # All features should be in [0, 1] range
        assert np.all(features >= 0.0), "Some features are negative"
        assert np.all(features <= 1.0), "Some features exceed 1.0"
    
    @given(
        symptom_vector=symptom_vector_strategy(),
        probabilities=prediction_probabilities_strategy()
    )
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_prediction_determinism(self, symptom_vector, probabilities, mock_service):
        """
        Property: Predictions are deterministic for same input.
        
        For any symptom vector, calling predict multiple times should return
        the same results.
        """
        service, mock_model = mock_service
        
        # Set up mock to return same probabilities
        mock_model.predict_proba.return_value = np.array([probabilities])
        
        # Make two predictions
        predictions1 = service.predict(symptom_vector)
        
        # Reset mock call count but keep same return value
        mock_model.predict_proba.reset_mock()
        mock_model.predict_proba.return_value = np.array([probabilities])
        
        predictions2 = service.predict(symptom_vector)
        
        # Should be identical
        assert len(predictions1) == len(predictions2)
        for (illness1, conf1), (illness2, conf2) in zip(predictions1, predictions2):
            assert illness1 == illness2
            assert conf1 == conf2
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_property_empty_predictions_when_all_below_threshold(self, symptom_vector, mock_service):
        """
        Property: Empty predictions when all below threshold.
        
        For any symptom vector, if all model predictions are below the confidence
        threshold, an empty list should be returned.
        
        **Validates: Requirements 3.5**
        """
        service, mock_model = mock_service
        
        # Generate probabilities all below threshold
        num_illnesses = len(service.KNOWN_ILLNESSES)
        probs = np.full(num_illnesses, 0.10)  # All below 0.30
        mock_model.predict_proba.return_value = np.array([probs])
        
        # Make prediction
        predictions = service.predict(symptom_vector)
        
        # Should return empty list
        assert len(predictions) == 0, (
            f"Expected empty predictions when all below threshold, got {len(predictions)}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
