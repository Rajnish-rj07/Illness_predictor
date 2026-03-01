"""
Property-based tests for PredictionService.

These tests validate universal properties that should hold across all inputs:
- Property 11: Top-K prediction limit
- Property 12: Severity assignment completeness

Validates: Requirements 3.2, 12.1
"""

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, patch

from src.prediction.prediction_service import PredictionService
from src.ml.ml_model_service import MLModelService
from src.models.data_models import SymptomVector, SymptomInfo, Severity


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


class TestPredictionServiceProperties:
    """Property-based tests for PredictionService."""
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_11_top_k_prediction_limit(self, symptom_vector):
        """
        Feature: illness-prediction-system, Property 11: Top-K prediction limit
        
        For any prediction result, the number of returned predictions should be at most 3.
        
        **Validates: Requirements 3.2**
        """
        # Create fresh mocks for each test run
        mock_ml_service = Mock(spec=MLModelService)
        prediction_service = PredictionService(ml_model_service=mock_ml_service)
        
        # Mock ML model to return various numbers of predictions
        # The MLModelService is already configured to return at most 3 predictions
        # but we test that PredictionService respects this limit
        
        # Generate between 0 and 10 mock predictions (to test various scenarios)
        num_mock_predictions = np.random.randint(0, 11)
        
        mock_predictions = [
            (f'illness_{i}', 0.30 + (0.70 * (num_mock_predictions - i) / max(num_mock_predictions, 1)))
            for i in range(num_mock_predictions)
        ]
        
        # Ensure all predictions are above threshold and in descending order
        mock_predictions = [
            (illness, max(0.30, min(0.99, conf)))
            for illness, conf in mock_predictions
        ]
        mock_predictions.sort(key=lambda x: x[1], reverse=True)
        
        # MLModelService should already limit to top 3, but we test various inputs
        mock_ml_service.predict.return_value = mock_predictions[:3]
        
        # Make prediction
        predictions = prediction_service.predict(symptom_vector)
        
        # Property: Should have at most 3 predictions (Requirement 3.2)
        assert len(predictions) <= 3, (
            f"Returned {len(predictions)} predictions, expected at most 3. "
            f"Predictions: {[p.illness for p in predictions]}"
        )
        
        # Verify MLModelService was called with top_k=3
        mock_ml_service.predict.assert_called_once()
        call_kwargs = mock_ml_service.predict.call_args[1]
        assert call_kwargs['top_k'] == 3, (
            f"MLModelService should be called with top_k=3, got {call_kwargs.get('top_k')}"
        )
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_11_top_k_limit_with_many_predictions(self, symptom_vector):
        """
        Feature: illness-prediction-system, Property 11: Top-K prediction limit
        
        Even when the ML model could return many predictions above threshold,
        the result should be limited to at most 3 predictions.
        
        **Validates: Requirements 3.2**
        """
        # Create fresh mocks for each test run
        mock_ml_service = Mock(spec=MLModelService)
        prediction_service = PredictionService(ml_model_service=mock_ml_service)
        
        # Simulate scenario where many illnesses have high confidence
        # In reality, MLModelService limits this, but we test the contract
        many_predictions = [
            ('influenza', 0.85),
            ('common_cold', 0.80),
            ('bronchitis', 0.75),
            # These would be filtered by MLModelService's top_k=3
            ('pneumonia', 0.70),
            ('covid_19', 0.65),
            ('sinusitis', 0.60),
        ]
        
        # MLModelService returns only top 3 (as it should)
        mock_ml_service.predict.return_value = many_predictions[:3]
        
        # Make prediction
        predictions = prediction_service.predict(symptom_vector)
        
        # Property: Should have at most 3 predictions
        assert len(predictions) <= 3, (
            f"Returned {len(predictions)} predictions, expected at most 3"
        )
        
        # Should have the top 3 illnesses (order may vary due to severity ranking)
        illness_names = {p.illness for p in predictions}
        expected_illnesses = {'influenza', 'common_cold', 'bronchitis'}
        assert illness_names == expected_illnesses, (
            f"Expected illnesses {expected_illnesses}, got {illness_names}"
        )
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=50, deadline=None)
    def test_property_11_top_k_limit_with_zero_predictions(self, symptom_vector):
        """
        Feature: illness-prediction-system, Property 11: Top-K prediction limit
        
        When no predictions meet the threshold, the result should be an empty list
        (which is <= 3).
        
        **Validates: Requirements 3.2, 3.5**
        """
        # Create fresh mocks for each test run
        mock_ml_service = Mock(spec=MLModelService)
        prediction_service = PredictionService(ml_model_service=mock_ml_service)
        
        # Mock ML model returning no predictions (all below threshold)
        mock_ml_service.predict.return_value = []
        
        # Make prediction
        predictions = prediction_service.predict(symptom_vector)
        
        # Property: Should have at most 3 predictions (in this case, 0)
        assert len(predictions) <= 3
        assert len(predictions) == 0, (
            f"Expected 0 predictions when all below threshold, got {len(predictions)}"
        )
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=50, deadline=None)
    def test_property_11_top_k_limit_with_one_prediction(self, symptom_vector):
        """
        Feature: illness-prediction-system, Property 11: Top-K prediction limit
        
        When only one prediction meets the threshold, the result should have exactly 1
        prediction (which is <= 3).
        
        **Validates: Requirements 3.2**
        """
        # Create fresh mocks for each test run
        mock_ml_service = Mock(spec=MLModelService)
        prediction_service = PredictionService(ml_model_service=mock_ml_service)
        
        # Mock ML model returning only one prediction
        mock_ml_service.predict.return_value = [('influenza', 0.75)]
        
        # Make prediction
        predictions = prediction_service.predict(symptom_vector)
        
        # Property: Should have at most 3 predictions (in this case, 1)
        assert len(predictions) <= 3
        assert len(predictions) == 1, (
            f"Expected 1 prediction, got {len(predictions)}"
        )
        assert predictions[0].illness == 'influenza'
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=50, deadline=None)
    def test_property_11_top_k_limit_with_two_predictions(self, symptom_vector):
        """
        Feature: illness-prediction-system, Property 11: Top-K prediction limit
        
        When two predictions meet the threshold, the result should have exactly 2
        predictions (which is <= 3).
        
        **Validates: Requirements 3.2**
        """
        # Create fresh mocks for each test run
        mock_ml_service = Mock(spec=MLModelService)
        prediction_service = PredictionService(ml_model_service=mock_ml_service)
        
        # Mock ML model returning two predictions
        mock_ml_service.predict.return_value = [
            ('influenza', 0.75),
            ('common_cold', 0.60),
        ]
        
        # Make prediction
        predictions = prediction_service.predict(symptom_vector)
        
        # Property: Should have at most 3 predictions (in this case, 2)
        assert len(predictions) <= 3
        assert len(predictions) == 2, (
            f"Expected 2 predictions, got {len(predictions)}"
        )
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=50, deadline=None)
    def test_property_11_top_k_limit_with_exactly_three_predictions(self, symptom_vector):
        """
        Feature: illness-prediction-system, Property 11: Top-K prediction limit
        
        When three predictions meet the threshold, the result should have exactly 3
        predictions (the maximum allowed).
        
        **Validates: Requirements 3.2**
        """
        # Create fresh mocks for each test run
        mock_ml_service = Mock(spec=MLModelService)
        prediction_service = PredictionService(ml_model_service=mock_ml_service)
        
        # Mock ML model returning exactly three predictions
        mock_ml_service.predict.return_value = [
            ('influenza', 0.75),
            ('common_cold', 0.60),
            ('bronchitis', 0.45),
        ]
        
        # Make prediction
        predictions = prediction_service.predict(symptom_vector)
        
        # Property: Should have at most 3 predictions (in this case, exactly 3)
        assert len(predictions) <= 3
        assert len(predictions) == 3, (
            f"Expected 3 predictions, got {len(predictions)}"
        )
    
    @given(
        symptom_vector=symptom_vector_strategy(),
        num_predictions=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_top_k_limit_universal(self, symptom_vector, num_predictions):
        """
        Feature: illness-prediction-system, Property 11: Top-K prediction limit
        
        Universal test: For ANY symptom vector and ANY number of potential predictions,
        the result should ALWAYS have at most 3 predictions.
        
        **Validates: Requirements 3.2**
        """
        # Create fresh mocks for each test run
        mock_ml_service = Mock(spec=MLModelService)
        prediction_service = PredictionService(ml_model_service=mock_ml_service)
        
        # Generate mock predictions (MLModelService would limit to 3)
        mock_predictions = [
            (f'illness_{i}', max(0.30, 0.95 - (i * 0.05)))
            for i in range(min(num_predictions, 3))  # MLModelService limits to top_k=3
        ]
        
        mock_ml_service.predict.return_value = mock_predictions
        
        # Make prediction
        predictions = prediction_service.predict(symptom_vector)
        
        # Universal property: ALWAYS at most 3 predictions
        assert len(predictions) <= 3, (
            f"PROPERTY VIOLATION: Returned {len(predictions)} predictions, "
            f"expected at most 3 for ANY input. "
            f"Input had {len(symptom_vector.symptoms)} symptoms, "
            f"mock returned {len(mock_predictions)} predictions."
        )
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_12_severity_assignment_completeness(self, symptom_vector):
        """
        Feature: illness-prediction-system, Property 12: Severity assignment completeness
        
        For ANY symptom vector, ALL predictions returned should have an assigned 
        severity level (LOW, MODERATE, HIGH, or CRITICAL).
        
        **Validates: Requirements 12.1**
        """
        # Create fresh mocks for each test run
        mock_ml_service = Mock(spec=MLModelService)
        prediction_service = PredictionService(ml_model_service=mock_ml_service)
        
        # Generate random number of mock predictions (0-3)
        num_predictions = np.random.randint(0, 4)
        
        mock_predictions = [
            (f'illness_{i}', max(0.30, 0.95 - (i * 0.10)))
            for i in range(num_predictions)
        ]
        
        mock_ml_service.predict.return_value = mock_predictions
        
        # Make prediction
        predictions = prediction_service.predict(symptom_vector)
        
        # Property: ALL predictions must have assigned severity
        for i, prediction in enumerate(predictions):
            assert prediction.severity is not None, (
                f"PROPERTY VIOLATION: Prediction {i} ({prediction.illness}) "
                f"has no severity assigned (severity is None)"
            )
            
            # Verify severity is one of the valid values
            valid_severities = [Severity.LOW, Severity.MODERATE, Severity.HIGH, Severity.CRITICAL]
            assert prediction.severity in valid_severities, (
                f"PROPERTY VIOLATION: Prediction {i} ({prediction.illness}) "
                f"has invalid severity: {prediction.severity}. "
                f"Expected one of: {[s.value for s in valid_severities]}"
            )
            
            # Verify severity is a Severity enum instance
            assert isinstance(prediction.severity, Severity), (
                f"PROPERTY VIOLATION: Prediction {i} ({prediction.illness}) "
                f"severity is not a Severity enum instance. "
                f"Got type: {type(prediction.severity)}"
            )
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=50, deadline=None)
    def test_property_12_severity_assignment_with_known_illnesses(self, symptom_vector):
        """
        Feature: illness-prediction-system, Property 12: Severity assignment completeness
        
        For ANY symptom vector, when predictions include known illnesses from the 
        severity map, they should have appropriate severity levels assigned.
        
        **Validates: Requirements 12.1**
        """
        # Create fresh mocks for each test run
        mock_ml_service = Mock(spec=MLModelService)
        prediction_service = PredictionService(ml_model_service=mock_ml_service)
        
        # Use known illnesses from the severity map
        known_illnesses = [
            ('meningitis', 0.85),  # Should be CRITICAL
            ('pneumonia', 0.75),   # Should be HIGH
            ('influenza', 0.65),   # Should be MODERATE
        ]
        
        mock_ml_service.predict.return_value = known_illnesses
        
        # Make prediction
        predictions = prediction_service.predict(symptom_vector)
        
        # Property: ALL predictions must have assigned severity
        assert len(predictions) == 3, f"Expected 3 predictions, got {len(predictions)}"
        
        for prediction in predictions:
            assert prediction.severity is not None, (
                f"PROPERTY VIOLATION: Prediction {prediction.illness} "
                f"has no severity assigned"
            )
            
            assert isinstance(prediction.severity, Severity), (
                f"PROPERTY VIOLATION: Prediction {prediction.illness} "
                f"severity is not a Severity enum instance"
            )
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=50, deadline=None)
    def test_property_12_severity_assignment_with_unknown_illnesses(self, symptom_vector):
        """
        Feature: illness-prediction-system, Property 12: Severity assignment completeness
        
        For ANY symptom vector, even when predictions include unknown illnesses 
        (not in severity map), they should still have severity assigned (defaults to MODERATE).
        
        **Validates: Requirements 12.1**
        """
        # Create fresh mocks for each test run
        mock_ml_service = Mock(spec=MLModelService)
        prediction_service = PredictionService(ml_model_service=mock_ml_service)
        
        # Remove any critical symptoms from the symptom vector to test default behavior
        critical_symptoms = [
            'chest_pain', 'shortness_of_breath', 'confusion', 'seizures',
            'severe_headache', 'loss_of_consciousness', 'difficulty_breathing',
            'severe_abdominal_pain', 'blood_in_stool', 'blood_in_urine',
            'severe_bleeding', 'paralysis', 'slurred_speech', 'sudden_vision_loss',
            'severe_allergic_reaction'
        ]
        
        for critical_symptom in critical_symptoms:
            if critical_symptom in symptom_vector.symptoms:
                del symptom_vector.symptoms[critical_symptom]
        
        # Use unknown illnesses not in the severity map
        unknown_illnesses = [
            ('rare_disease_xyz', 0.75),
            ('unknown_condition_abc', 0.60),
            ('mystery_illness_123', 0.45),
        ]
        
        mock_ml_service.predict.return_value = unknown_illnesses
        
        # Make prediction
        predictions = prediction_service.predict(symptom_vector)
        
        # Property: ALL predictions must have assigned severity (even unknown illnesses)
        assert len(predictions) == 3, f"Expected 3 predictions, got {len(predictions)}"
        
        for prediction in predictions:
            assert prediction.severity is not None, (
                f"PROPERTY VIOLATION: Unknown illness {prediction.illness} "
                f"has no severity assigned. Even unknown illnesses should default to MODERATE."
            )
            
            assert isinstance(prediction.severity, Severity), (
                f"PROPERTY VIOLATION: Unknown illness {prediction.illness} "
                f"severity is not a Severity enum instance"
            )
            
            # Unknown illnesses should default to MODERATE (unless critical symptoms present)
            assert prediction.severity == Severity.MODERATE, (
                f"Unknown illness {prediction.illness} should default to MODERATE severity, "
                f"got {prediction.severity.value}"
            )
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=50, deadline=None)
    def test_property_12_severity_assignment_with_critical_symptoms(self, symptom_vector):
        """
        Feature: illness-prediction-system, Property 12: Severity assignment completeness
        
        For ANY symptom vector containing critical symptoms (e.g., chest_pain, 
        shortness_of_breath), predictions should be escalated to CRITICAL severity.
        
        **Validates: Requirements 12.1, 12.2**
        """
        # Create fresh mocks for each test run
        mock_ml_service = Mock(spec=MLModelService)
        prediction_service = PredictionService(ml_model_service=mock_ml_service)
        
        # Add critical symptoms to the symptom vector
        symptom_vector.symptoms['chest_pain'] = SymptomInfo(
            present=True,
            severity=9,
            duration='<1d',
            description='severe chest pain'
        )
        
        # Use a low severity illness that should be escalated
        mock_predictions = [('common_cold', 0.75)]
        mock_ml_service.predict.return_value = mock_predictions
        
        # Make prediction
        predictions = prediction_service.predict(symptom_vector)
        
        # Property: Prediction should have severity assigned
        assert len(predictions) == 1
        prediction = predictions[0]
        
        assert prediction.severity is not None, (
            "PROPERTY VIOLATION: Prediction has no severity assigned"
        )
        
        # With critical symptoms, severity should be escalated to CRITICAL
        assert prediction.severity == Severity.CRITICAL, (
            f"Expected CRITICAL severity due to critical symptoms, "
            f"got {prediction.severity.value}"
        )
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=50, deadline=None)
    def test_property_12_severity_assignment_with_empty_predictions(self, symptom_vector):
        """
        Feature: illness-prediction-system, Property 12: Severity assignment completeness
        
        For ANY symptom vector, when no predictions meet the confidence threshold,
        the result should be an empty list (vacuously true - all zero predictions have severity).
        
        **Validates: Requirements 12.1, 3.5**
        """
        # Create fresh mocks for each test run
        mock_ml_service = Mock(spec=MLModelService)
        prediction_service = PredictionService(ml_model_service=mock_ml_service)
        
        # Mock ML model returning no predictions (all below threshold)
        mock_ml_service.predict.return_value = []
        
        # Make prediction
        predictions = prediction_service.predict(symptom_vector)
        
        # Property: Empty list is valid (all zero predictions have severity - vacuously true)
        assert len(predictions) == 0, (
            f"Expected 0 predictions when all below threshold, got {len(predictions)}"
        )
        
        # Verify that if there were predictions, they would all have severity
        # (This is vacuously true for empty list)
        for prediction in predictions:
            assert prediction.severity is not None


    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_13_critical_severity_safety_protocol(self, symptom_vector):
        """
        Feature: illness-prediction-system, Property 13: Critical severity safety protocol
        
        For ANY symptom vector that results in CRITICAL severity predictions:
        - Treatment suggestions should have NO medications (empty list)
        - Treatment suggestions should include immediate medical attention warnings
        - seek_professional flag should be True
        
        **Validates: Requirements 12.2, 18.4**
        """
        # Create fresh mocks for each test run
        mock_ml_service = Mock(spec=MLModelService)
        prediction_service = PredictionService(ml_model_service=mock_ml_service)
        
        # Add critical symptoms to force CRITICAL severity
        # This ensures we test the critical severity path
        symptom_vector.symptoms['chest_pain'] = SymptomInfo(
            present=True,
            severity=9,
            duration='<1d',
            description='severe chest pain'
        )
        symptom_vector.symptoms['shortness_of_breath'] = SymptomInfo(
            present=True,
            severity=8,
            duration='<1d',
            description='difficulty breathing'
        )
        
        # Mock predictions - use various illnesses (some critical, some not)
        # The critical symptoms should escalate ALL predictions to CRITICAL
        mock_predictions = [
            ('common_cold', 0.75),  # Normally LOW, but should be escalated
            ('influenza', 0.65),    # Normally MODERATE, but should be escalated
            ('pneumonia', 0.55),    # Normally HIGH, but should be escalated
        ]
        
        mock_ml_service.predict.return_value = mock_predictions
        
        # Make prediction
        predictions = prediction_service.predict(symptom_vector)
        
        # Property: ALL predictions should be CRITICAL due to critical symptoms
        for i, prediction in enumerate(predictions):
            # Verify severity is CRITICAL
            assert prediction.severity == Severity.CRITICAL, (
                f"PROPERTY VIOLATION: Prediction {i} ({prediction.illness}) "
                f"should have CRITICAL severity due to critical symptoms, "
                f"got {prediction.severity.value}"
            )
            
            # Verify treatment suggestions exist
            assert prediction.treatment_suggestions is not None, (
                f"PROPERTY VIOLATION: Prediction {i} ({prediction.illness}) "
                f"has no treatment suggestions"
            )
            
            treatment = prediction.treatment_suggestions
            
            # Property 1: NO medication suggestions for CRITICAL severity (Requirement 18.4)
            assert treatment.medications == [], (
                f"PROPERTY VIOLATION: CRITICAL prediction {i} ({prediction.illness}) "
                f"should have NO medication suggestions, but got: {treatment.medications}. "
                f"Requirement 18.4: High/Critical severity should not provide medication suggestions."
            )
            
            # Property 2: Should include immediate medical attention warnings (Requirement 12.2)
            assert treatment.non_medication is not None and len(treatment.non_medication) > 0, (
                f"PROPERTY VIOLATION: CRITICAL prediction {i} ({prediction.illness}) "
                f"should have non-medication recommendations (medical attention warnings)"
            )
            
            # Verify the warnings include immediate medical attention language
            non_med_text = ' '.join(treatment.non_medication).lower()
            assert any(keyword in non_med_text for keyword in [
                'immediate', 'emergency', 'medical attention', 'seek', 'urgent'
            ]), (
                f"PROPERTY VIOLATION: CRITICAL prediction {i} ({prediction.illness}) "
                f"should include immediate medical attention warnings in non-medication options. "
                f"Got: {treatment.non_medication}"
            )
            
            # Property 3: seek_professional flag should be True (Requirement 12.2)
            assert treatment.seek_professional is True, (
                f"PROPERTY VIOLATION: CRITICAL prediction {i} ({prediction.illness}) "
                f"should have seek_professional=True, got {treatment.seek_professional}"
            )
            
            # Verify disclaimer includes serious/immediate language
            assert treatment.disclaimer is not None, (
                f"PROPERTY VIOLATION: CRITICAL prediction {i} ({prediction.illness}) "
                f"should have a disclaimer"
            )
            
            disclaimer_lower = treatment.disclaimer.lower()
            assert any(keyword in disclaimer_lower for keyword in [
                'serious', 'immediate', 'emergency', 'urgent', 'critical'
            ]), (
                f"PROPERTY VIOLATION: CRITICAL prediction {i} ({prediction.illness}) "
                f"disclaimer should emphasize seriousness. Got: {treatment.disclaimer}"
            )
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=50, deadline=None)
    def test_property_13_critical_severity_with_critical_illness(self, symptom_vector):
        """
        Feature: illness-prediction-system, Property 13: Critical severity safety protocol
        
        For ANY symptom vector with predictions of inherently CRITICAL illnesses
        (e.g., meningitis, heart_attack), the safety protocol should apply.
        
        **Validates: Requirements 12.2, 18.4**
        """
        # Create fresh mocks for each test run
        mock_ml_service = Mock(spec=MLModelService)
        prediction_service = PredictionService(ml_model_service=mock_ml_service)
        
        # Use inherently critical illnesses from the severity map
        critical_illnesses = [
            ('meningitis', 0.85),
            ('heart_attack', 0.75),
            ('stroke', 0.65),
        ]
        
        mock_ml_service.predict.return_value = critical_illnesses
        
        # Make prediction
        predictions = prediction_service.predict(symptom_vector)
        
        # Property: ALL critical illness predictions should follow safety protocol
        assert len(predictions) > 0, "Should have at least one prediction"
        
        for prediction in predictions:
            # Should be CRITICAL severity
            assert prediction.severity == Severity.CRITICAL, (
                f"Inherently critical illness {prediction.illness} should have CRITICAL severity"
            )
            
            treatment = prediction.treatment_suggestions
            
            # NO medications
            assert treatment.medications == [], (
                f"CRITICAL illness {prediction.illness} should have NO medication suggestions"
            )
            
            # Should recommend immediate medical attention
            assert len(treatment.non_medication) > 0
            non_med_text = ' '.join(treatment.non_medication).lower()
            assert 'immediate' in non_med_text or 'emergency' in non_med_text
            
            # seek_professional should be True
            assert treatment.seek_professional is True
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=50, deadline=None)
    def test_property_13_high_severity_safety_protocol(self, symptom_vector):
        """
        Feature: illness-prediction-system, Property 13: Critical severity safety protocol
        
        For ANY symptom vector with HIGH severity predictions, the same safety protocol
        should apply (no medications, recommend immediate care).
        
        **Validates: Requirements 18.4**
        """
        # Create fresh mocks for each test run
        mock_ml_service = Mock(spec=MLModelService)
        prediction_service = PredictionService(ml_model_service=mock_ml_service)
        
        # Use inherently HIGH severity illnesses
        high_severity_illnesses = [
            ('pneumonia', 0.85),
            ('covid_19', 0.75),
            ('tuberculosis', 0.65),
        ]
        
        mock_ml_service.predict.return_value = high_severity_illnesses
        
        # Make prediction
        predictions = prediction_service.predict(symptom_vector)
        
        # Property: HIGH severity predictions should also follow safety protocol
        assert len(predictions) > 0, "Should have at least one prediction"
        
        for prediction in predictions:
            # Should be HIGH severity (unless escalated by critical symptoms)
            assert prediction.severity in [Severity.HIGH, Severity.CRITICAL], (
                f"High severity illness {prediction.illness} should have HIGH or CRITICAL severity"
            )
            
            treatment = prediction.treatment_suggestions
            
            # NO medications for HIGH/CRITICAL severity (Requirement 18.4)
            assert treatment.medications == [], (
                f"HIGH severity illness {prediction.illness} should have NO medication suggestions. "
                f"Requirement 18.4: High or Critical severity should not provide medication suggestions."
            )
            
            # Should recommend immediate medical attention
            assert len(treatment.non_medication) > 0
            
            # seek_professional should be True
            assert treatment.seek_professional is True
    
    @given(symptom_vector=symptom_vector_strategy())
    @settings(max_examples=50, deadline=None)
    def test_property_13_low_moderate_severity_can_have_medications(self, symptom_vector):
        """
        Feature: illness-prediction-system, Property 13: Critical severity safety protocol
        
        For ANY symptom vector with LOW or MODERATE severity predictions (and no critical
        symptoms), medications CAN be suggested (contrast to critical severity).
        
        **Validates: Requirements 18.1, 18.2, 18.3**
        """
        # Create fresh mocks for each test run
        mock_ml_service = Mock(spec=MLModelService)
        prediction_service = PredictionService(ml_model_service=mock_ml_service)
        
        # Remove any critical symptoms to ensure LOW/MODERATE severity
        critical_symptoms = [
            'chest_pain', 'shortness_of_breath', 'confusion', 'seizures',
            'severe_headache', 'loss_of_consciousness', 'difficulty_breathing',
            'severe_abdominal_pain', 'blood_in_stool', 'blood_in_urine',
            'severe_bleeding', 'paralysis', 'slurred_speech', 'sudden_vision_loss',
            'severe_allergic_reaction'
        ]
        
        for critical_symptom in critical_symptoms:
            if critical_symptom in symptom_vector.symptoms:
                del symptom_vector.symptoms[critical_symptom]
        
        # Use LOW/MODERATE severity illnesses
        low_moderate_illnesses = [
            ('common_cold', 0.75),      # LOW
            ('influenza', 0.65),        # MODERATE
            ('allergic_rhinitis', 0.55), # LOW
        ]
        
        mock_ml_service.predict.return_value = low_moderate_illnesses
        
        # Make prediction
        predictions = prediction_service.predict(symptom_vector)
        
        # Property: LOW/MODERATE severity predictions CAN have medications
        assert len(predictions) > 0, "Should have at least one prediction"
        
        for prediction in predictions:
            # Should be LOW or MODERATE severity
            assert prediction.severity in [Severity.LOW, Severity.MODERATE], (
                f"Expected LOW or MODERATE severity, got {prediction.severity.value}"
            )
            
            treatment = prediction.treatment_suggestions
            
            # CAN have medications (not required, but allowed)
            # This is the contrast to CRITICAL/HIGH severity
            # If medications are provided, they should include disclaimers
            if treatment.medications:
                assert treatment.disclaimer is not None, (
                    f"Medications provided for {prediction.illness} should include disclaimer"
                )
                
                disclaimer_lower = treatment.disclaimer.lower()
                assert 'disclaimer' in disclaimer_lower or 'informational' in disclaimer_lower, (
                    f"Disclaimer should be clear for {prediction.illness}"
                )
            
            # Should still recommend professional consultation
            assert treatment.seek_professional is True, (
                f"All predictions should recommend professional consultation"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
