"""
Property-based tests for ExplainabilityService.

These tests validate universal properties that should hold across all inputs:
- Property 27: SHAP value computation
- Property 28: Top contributor identification

Validates: Requirements 14.1, 14.2
"""

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, MagicMock, patch

from src.explainability.explainability_service import ExplainabilityService
from src.ml.ml_model_service import MLModelService
from src.models.data_models import (
    SymptomVector,
    SymptomInfo,
    Prediction,
    Severity,
    Explanation
)


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
    num_symptoms = draw(st.integers(min_value=1, max_value=20))
    
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
def prediction_strategy(draw):
    """Generate random Prediction objects."""
    illnesses = [
        'common_cold', 'influenza', 'covid_19', 'pneumonia',
        'bronchitis', 'strep_throat', 'sinusitis', 'allergies'
    ]
    
    illness = draw(st.sampled_from(illnesses))
    confidence_score = draw(st.floats(min_value=0.30, max_value=1.0))
    severity = draw(st.sampled_from(list(Severity)))
    
    return Prediction(
        illness=illness,
        confidence_score=confidence_score,
        severity=severity
    )


class TestExplainabilityServiceProperties:
    """Property-based tests for ExplainabilityService."""
    
    @patch('src.explainability.explainability_service.shap.TreeExplainer')
    @given(
        symptom_vector=symptom_vector_strategy(),
        prediction=prediction_strategy()
    )
    @settings(
        max_examples=100,
        deadline=None
    )
    def test_property_27_shap_value_computation(
        self,
        mock_tree_explainer,
        symptom_vector,
        prediction
    ):
        """
        Feature: illness-prediction-system, Property 27: SHAP value computation
        
        For any prediction generated, the system should compute SHAP values for 
        all input features.
        
        **Validates: Requirements 14.1**
        """
        # Create mock ML service inline
        mock_ml_service = Mock(spec=MLModelService)
        mock_ml_service.KNOWN_SYMPTOMS = [
            'fever', 'cough', 'headache', 'fatigue', 'sore_throat',
            'shortness_of_breath', 'body_aches', 'nausea'
        ]
        mock_ml_service.KNOWN_ILLNESSES = [
            'common_cold', 'influenza', 'covid_19', 'pneumonia',
            'bronchitis', 'strep_throat', 'sinusitis', 'allergies'
        ]
        mock_ml_service.get_active_model.return_value = 'v1.0.0'
        mock_model = MagicMock()
        mock_ml_service.load_model.return_value = mock_model
        
        def mock_vectorize(symptom_vector):
            num_symptoms = len(mock_ml_service.KNOWN_SYMPTOMS)
            features = np.zeros((1, num_symptoms * 3))
            return features
        
        mock_ml_service.vectorize_symptoms = mock_vectorize
        
        # Create service
        service = ExplainabilityService(mock_ml_service)
        
        # Set up mock SHAP explainer
        mock_explainer = MagicMock()
        num_symptoms = len(mock_ml_service.KNOWN_SYMPTOMS)
        num_illnesses = len(mock_ml_service.KNOWN_ILLNESSES)
        
        # Create mock SHAP values (list of arrays for multi-class)
        # Each array has shape (1, num_features) where num_features = num_symptoms * 3
        shap_values_list = []
        for _ in range(num_illnesses):
            shap_values_list.append(np.random.randn(1, num_symptoms * 3))
        
        mock_explainer.shap_values.return_value = shap_values_list
        mock_tree_explainer.return_value = mock_explainer
        
        # Generate explanation
        explanation = service.explain_prediction(symptom_vector, prediction)
        
        # Property: SHAP values should be computed
        assert isinstance(explanation, Explanation), (
            "explain_prediction should return an Explanation object"
        )
        
        assert explanation.shap_values is not None, (
            f"SHAP values should be computed for prediction '{prediction.illness}', "
            f"but got None"
        )
        
        # SHAP values should be a numpy array
        assert isinstance(explanation.shap_values, np.ndarray), (
            f"SHAP values should be a numpy array, got {type(explanation.shap_values)}"
        )
        
        # SHAP values should have the correct shape (one value per feature)
        expected_num_features = num_symptoms * 3  # presence, severity, duration
        assert explanation.shap_values.shape == (expected_num_features,), (
            f"SHAP values should have shape ({expected_num_features},), "
            f"got {explanation.shap_values.shape}"
        )
        
        # SHAP values should be finite (not NaN or Inf)
        assert np.all(np.isfinite(explanation.shap_values)), (
            "SHAP values should all be finite (not NaN or Inf)"
        )
        
        # Verify that the SHAP explainer was called
        mock_explainer.shap_values.assert_called_once()
    
    @patch('src.explainability.explainability_service.shap.TreeExplainer')
    @given(
        symptom_vector=symptom_vector_strategy(),
        prediction=prediction_strategy()
    )
    @settings(
        max_examples=100,
        deadline=None
    )
    def test_property_shap_values_for_all_features(
        self,
        mock_tree_explainer,
        symptom_vector,
        prediction
    ):
        """
        Property: SHAP values are computed for all input features.
        
        For any prediction, SHAP values should be computed for every feature
        in the input vector (presence, severity, duration for each symptom).
        """
        # Create mock ML service inline
        mock_ml_service = Mock(spec=MLModelService)
        mock_ml_service.KNOWN_SYMPTOMS = [
            'fever', 'cough', 'headache', 'fatigue', 'sore_throat',
            'shortness_of_breath', 'body_aches', 'nausea'
        ]
        mock_ml_service.KNOWN_ILLNESSES = [
            'common_cold', 'influenza', 'covid_19', 'pneumonia',
            'bronchitis', 'strep_throat', 'sinusitis', 'allergies'
        ]
        mock_ml_service.get_active_model.return_value = 'v1.0.0'
        mock_ml_service.load_model.return_value = MagicMock()
        mock_ml_service.vectorize_symptoms = lambda sv: np.zeros((1, len(mock_ml_service.KNOWN_SYMPTOMS) * 3))
        
        service = ExplainabilityService(mock_ml_service)
        
        # Set up mock SHAP explainer
        mock_explainer = MagicMock()
        num_symptoms = len(mock_ml_service.KNOWN_SYMPTOMS)
        num_illnesses = len(mock_ml_service.KNOWN_ILLNESSES)
        
        # Create mock SHAP values
        shap_values_list = []
        for _ in range(num_illnesses):
            shap_values_list.append(np.random.randn(1, num_symptoms * 3))
        
        mock_explainer.shap_values.return_value = shap_values_list
        mock_tree_explainer.return_value = mock_explainer
        
        # Generate explanation
        explanation = service.explain_prediction(symptom_vector, prediction)
        
        # SHAP values should exist for all features
        num_features = num_symptoms * 3
        assert len(explanation.shap_values) == num_features, (
            f"Expected SHAP values for {num_features} features, "
            f"got {len(explanation.shap_values)}"
        )
    
    @patch('src.explainability.explainability_service.shap.TreeExplainer')
    @given(
        symptom_vector=symptom_vector_strategy(),
        prediction=prediction_strategy()
    )
    @settings(
        max_examples=50,
        deadline=None
    )
    def test_property_explanation_includes_contributors(
        self,
        mock_tree_explainer,
        symptom_vector,
        prediction
    ):
        """
        Property: Explanations include top contributing symptoms.
        
        For any prediction with computed SHAP values, the explanation should
        identify top contributing symptoms (up to 3).
        """
        # Create mock ML service inline
        mock_ml_service = Mock(spec=MLModelService)
        mock_ml_service.KNOWN_SYMPTOMS = [
            'fever', 'cough', 'headache', 'fatigue', 'sore_throat',
            'shortness_of_breath', 'body_aches', 'nausea'
        ]
        mock_ml_service.KNOWN_ILLNESSES = [
            'common_cold', 'influenza', 'covid_19', 'pneumonia',
            'bronchitis', 'strep_throat', 'sinusitis', 'allergies'
        ]
        mock_ml_service.get_active_model.return_value = 'v1.0.0'
        mock_ml_service.load_model.return_value = MagicMock()
        mock_ml_service.vectorize_symptoms = lambda sv: np.zeros((1, len(mock_ml_service.KNOWN_SYMPTOMS) * 3))
        
        service = ExplainabilityService(mock_ml_service)
        
        # Set up mock SHAP explainer
        mock_explainer = MagicMock()
        num_symptoms = len(mock_ml_service.KNOWN_SYMPTOMS)
        num_illnesses = len(mock_ml_service.KNOWN_ILLNESSES)
        
        # Create mock SHAP values with some non-zero contributions
        shap_values_list = []
        for i in range(num_illnesses):
            if i == 0:  # First illness (will match most predictions)
                # Create values with clear top contributors
                values = np.random.randn(1, num_symptoms * 3) * 0.1
                values[0, 0] = 0.5  # Strong positive contribution
                values[0, 1] = -0.3  # Strong negative contribution
                values[0, 2] = 0.2  # Moderate contribution
                shap_values_list.append(values)
            else:
                shap_values_list.append(np.random.randn(1, num_symptoms * 3) * 0.1)
        
        mock_explainer.shap_values.return_value = shap_values_list
        mock_tree_explainer.return_value = mock_explainer
        
        # Generate explanation
        explanation = service.explain_prediction(symptom_vector, prediction)
        
        # Should have top contributors
        assert isinstance(explanation.top_contributors, list), (
            "top_contributors should be a list"
        )
        
        # Should have at most 3 contributors
        assert len(explanation.top_contributors) <= 3, (
            f"Should have at most 3 top contributors, got {len(explanation.top_contributors)}"
        )
        
        # Each contributor should be a tuple of (symptom_name, shap_value)
        for contributor in explanation.top_contributors:
            assert isinstance(contributor, tuple), (
                f"Each contributor should be a tuple, got {type(contributor)}"
            )
            assert len(contributor) == 2, (
                f"Each contributor tuple should have 2 elements, got {len(contributor)}"
            )
            symptom_name, shap_value = contributor
            assert isinstance(symptom_name, str), (
                f"Symptom name should be a string, got {type(symptom_name)}"
            )
            assert isinstance(shap_value, (float, np.floating)), (
                f"SHAP value should be a float, got {type(shap_value)}"
            )
    
    @patch('src.explainability.explainability_service.shap.TreeExplainer')
    @given(
        symptom_vector=symptom_vector_strategy(),
        prediction=prediction_strategy()
    )
    @settings(
        max_examples=50,
        deadline=None
    )
    def test_property_explanation_text_generated(
        self,
        mock_tree_explainer,
        symptom_vector,
        prediction
    ):
        """
        Property: Explanation text is always generated.
        
        For any prediction, the explanation should include human-readable
        explanation text.
        """
        # Create mock ML service inline
        mock_ml_service = Mock(spec=MLModelService)
        mock_ml_service.KNOWN_SYMPTOMS = [
            'fever', 'cough', 'headache', 'fatigue', 'sore_throat',
            'shortness_of_breath', 'body_aches', 'nausea'
        ]
        mock_ml_service.KNOWN_ILLNESSES = [
            'common_cold', 'influenza', 'covid_19', 'pneumonia',
            'bronchitis', 'strep_throat', 'sinusitis', 'allergies'
        ]
        mock_ml_service.get_active_model.return_value = 'v1.0.0'
        mock_ml_service.load_model.return_value = MagicMock()
        mock_ml_service.vectorize_symptoms = lambda sv: np.zeros((1, len(mock_ml_service.KNOWN_SYMPTOMS) * 3))
        
        service = ExplainabilityService(mock_ml_service)
        
        # Set up mock SHAP explainer
        mock_explainer = MagicMock()
        num_symptoms = len(mock_ml_service.KNOWN_SYMPTOMS)
        num_illnesses = len(mock_ml_service.KNOWN_ILLNESSES)
        
        shap_values_list = []
        for _ in range(num_illnesses):
            shap_values_list.append(np.random.randn(1, num_symptoms * 3))
        
        mock_explainer.shap_values.return_value = shap_values_list
        mock_tree_explainer.return_value = mock_explainer
        
        # Generate explanation
        explanation = service.explain_prediction(symptom_vector, prediction)
        
        # Should have explanation text
        assert explanation.explanation_text is not None, (
            "explanation_text should not be None"
        )
        assert isinstance(explanation.explanation_text, str), (
            f"explanation_text should be a string, got {type(explanation.explanation_text)}"
        )
        assert len(explanation.explanation_text) > 0, (
            "explanation_text should not be empty"
        )
    
    @patch('src.explainability.explainability_service.shap.TreeExplainer')
    @given(
        symptom_vector=symptom_vector_strategy(),
        prediction=prediction_strategy()
    )
    @settings(
        max_examples=30,
        deadline=None
    )
    def test_property_shap_computation_deterministic(
        self,
        mock_tree_explainer,
        symptom_vector,
        prediction
    ):
        """
        Property: SHAP computation is deterministic.
        
        For any symptom vector and prediction, calling explain_prediction
        multiple times should produce the same SHAP values.
        """
        # Create mock ML service inline
        mock_ml_service = Mock(spec=MLModelService)
        mock_ml_service.KNOWN_SYMPTOMS = [
            'fever', 'cough', 'headache', 'fatigue', 'sore_throat',
            'shortness_of_breath', 'body_aches', 'nausea'
        ]
        mock_ml_service.KNOWN_ILLNESSES = [
            'common_cold', 'influenza', 'covid_19', 'pneumonia',
            'bronchitis', 'strep_throat', 'sinusitis', 'allergies'
        ]
        mock_ml_service.get_active_model.return_value = 'v1.0.0'
        mock_ml_service.load_model.return_value = MagicMock()
        mock_ml_service.vectorize_symptoms = lambda sv: np.zeros((1, len(mock_ml_service.KNOWN_SYMPTOMS) * 3))
        
        service = ExplainabilityService(mock_ml_service)
        
        # Set up mock SHAP explainer with fixed values
        mock_explainer = MagicMock()
        num_symptoms = len(mock_ml_service.KNOWN_SYMPTOMS)
        num_illnesses = len(mock_ml_service.KNOWN_ILLNESSES)
        
        # Create fixed SHAP values
        fixed_shap_values = []
        for _ in range(num_illnesses):
            fixed_shap_values.append(np.random.randn(1, num_symptoms * 3))
        
        mock_explainer.shap_values.return_value = fixed_shap_values
        mock_tree_explainer.return_value = mock_explainer
        
        # Generate explanation twice
        explanation1 = service.explain_prediction(symptom_vector, prediction)
        
        # Reset mock but keep same return value
        mock_explainer.shap_values.reset_mock()
        mock_explainer.shap_values.return_value = fixed_shap_values
        
        explanation2 = service.explain_prediction(symptom_vector, prediction)
        
        # SHAP values should be identical
        assert np.array_equal(explanation1.shap_values, explanation2.shap_values), (
            "SHAP values should be deterministic for the same input"
        )
        
        # Top contributors should be identical
        assert len(explanation1.top_contributors) == len(explanation2.top_contributors)
        for (s1, v1), (s2, v2) in zip(
            explanation1.top_contributors,
            explanation2.top_contributors
        ):
            assert s1 == s2, "Contributor symptoms should match"
            assert v1 == v2, "Contributor SHAP values should match"
    
    @patch('src.explainability.explainability_service.shap.TreeExplainer')
    @given(
        symptom_vector=symptom_vector_strategy(),
        prediction=prediction_strategy()
    )
    @settings(
        max_examples=20,
        deadline=None
    )
    def test_property_28_top_contributor_identification(
        self,
        mock_tree_explainer,
        symptom_vector,
        prediction
    ):
        """
        Feature: illness-prediction-system, Property 28: Top contributor identification
        
        For any prediction with explanation, the explanation should identify exactly 3 
        symptoms with the highest absolute SHAP values (or fewer if there are fewer 
        than 3 symptoms present).
        
        **Validates: Requirements 14.2**
        """
        # Create mock ML service inline
        mock_ml_service = Mock(spec=MLModelService)
        mock_ml_service.KNOWN_SYMPTOMS = [
            'fever', 'cough', 'headache', 'fatigue', 'sore_throat',
            'shortness_of_breath', 'body_aches', 'nausea'
        ]
        mock_ml_service.KNOWN_ILLNESSES = [
            'common_cold', 'influenza', 'covid_19', 'pneumonia',
            'bronchitis', 'strep_throat', 'sinusitis', 'allergies'
        ]
        mock_ml_service.get_active_model.return_value = 'v1.0.0'
        mock_model = MagicMock()
        mock_ml_service.load_model.return_value = mock_model
        
        def mock_vectorize(symptom_vector):
            num_symptoms = len(mock_ml_service.KNOWN_SYMPTOMS)
            features = np.zeros((1, num_symptoms * 3))
            return features
        
        mock_ml_service.vectorize_symptoms = mock_vectorize
        
        # Create service
        service = ExplainabilityService(mock_ml_service)
        
        # Set up mock SHAP explainer with varied SHAP values
        mock_explainer = MagicMock()
        num_symptoms = len(mock_ml_service.KNOWN_SYMPTOMS)
        num_illnesses = len(mock_ml_service.KNOWN_ILLNESSES)
        
        # Find the index of the predicted illness
        try:
            illness_idx = mock_ml_service.KNOWN_ILLNESSES.index(prediction.illness)
        except ValueError:
            # If illness not in known list, use index 0
            illness_idx = 0
        
        # Create mock SHAP values with clear ranking for the predicted illness
        shap_values_list = []
        for i in range(num_illnesses):
            values = np.zeros((1, num_symptoms * 3))
            
            if i == illness_idx:
                # For the predicted illness, create a clear ranking of absolute values
                # Set specific values for presence features (first num_symptoms features)
                values[0, 0] = 0.8   # fever presence - highest absolute
                values[0, 1] = -0.6  # cough presence - second highest absolute
                values[0, 2] = 0.4   # headache presence - third highest absolute
                values[0, 3] = 0.2   # fatigue presence - fourth
                values[0, 4] = -0.1  # sore_throat presence - fifth
                # Rest are near zero
                for j in range(5, num_symptoms * 3):
                    values[0, j] = np.random.randn() * 0.01
            else:
                # Other illnesses get random small values
                values[0, :] = np.random.randn(num_symptoms * 3) * 0.05
            
            shap_values_list.append(values)
        
        mock_explainer.shap_values.return_value = shap_values_list
        mock_tree_explainer.return_value = mock_explainer
        
        # Generate explanation
        explanation = service.explain_prediction(symptom_vector, prediction)
        
        # Property 28: Top contributor identification
        
        # 1. Should have top contributors
        assert explanation.top_contributors is not None, (
            "Explanation should have top_contributors"
        )
        assert isinstance(explanation.top_contributors, list), (
            "top_contributors should be a list"
        )
        
        # 2. Should have at most 3 contributors
        assert len(explanation.top_contributors) <= 3, (
            f"Should have at most 3 top contributors, got {len(explanation.top_contributors)}"
        )
        
        # 3. If there are contributors, verify they are ranked by absolute SHAP value
        if len(explanation.top_contributors) > 1:
            for i in range(len(explanation.top_contributors) - 1):
                current_symptom, current_shap = explanation.top_contributors[i]
                next_symptom, next_shap = explanation.top_contributors[i + 1]
                
                assert abs(current_shap) >= abs(next_shap), (
                    f"Contributors should be ranked by absolute SHAP value. "
                    f"Position {i}: |{current_shap}| = {abs(current_shap)}, "
                    f"Position {i+1}: |{next_shap}| = {abs(next_shap)}"
                )
        
        # 4. Each contributor should be a valid tuple
        for i, contributor in enumerate(explanation.top_contributors):
            assert isinstance(contributor, tuple), (
                f"Contributor {i} should be a tuple, got {type(contributor)}"
            )
            assert len(contributor) == 2, (
                f"Contributor {i} should have 2 elements (symptom, shap_value), "
                f"got {len(contributor)}"
            )
            
            symptom_name, shap_value = contributor
            
            assert isinstance(symptom_name, str), (
                f"Contributor {i} symptom name should be a string, got {type(symptom_name)}"
            )
            assert len(symptom_name) > 0, (
                f"Contributor {i} symptom name should not be empty"
            )
            
            assert isinstance(shap_value, (float, np.floating, int, np.integer)), (
                f"Contributor {i} SHAP value should be numeric, got {type(shap_value)}"
            )
            assert np.isfinite(shap_value), (
                f"Contributor {i} SHAP value should be finite, got {shap_value}"
            )
        
        # 5. Verify that contributors are indeed from the top absolute SHAP values
        # This validates that the implementation correctly identifies the highest contributors
        if len(explanation.top_contributors) > 0 and explanation.shap_values is not None:
            # Calculate the aggregated SHAP values per symptom (as the implementation does)
            # Features are: [presence, severity, duration] for each symptom
            symptom_shap_aggregated = {}
            for i, symptom_name in enumerate(mock_ml_service.KNOWN_SYMPTOMS):
                presence_shap = explanation.shap_values[i]
                severity_shap = explanation.shap_values[num_symptoms + i]
                duration_shap = explanation.shap_values[2 * num_symptoms + i]
                total_shap = presence_shap + severity_shap + duration_shap
                
                # Only include symptoms that are in the symptom vector (matching implementation logic)
                normalized_name = symptom_name.replace('_', ' ')
                if symptom_name in symptom_vector.symptoms or normalized_name in symptom_vector.symptoms:
                    symptom_shap_aggregated[symptom_name] = total_shap
            
            # If no symptoms matched, use all symptoms with non-zero SHAP values (fallback logic)
            if not symptom_shap_aggregated:
                for i, symptom_name in enumerate(mock_ml_service.KNOWN_SYMPTOMS):
                    presence_shap = explanation.shap_values[i]
                    severity_shap = explanation.shap_values[num_symptoms + i]
                    duration_shap = explanation.shap_values[2 * num_symptoms + i]
                    total_shap = presence_shap + severity_shap + duration_shap
                    
                    if abs(total_shap) > 1e-6:  # Non-zero threshold
                        symptom_shap_aggregated[symptom_name] = total_shap
            
            # Get the top 3 by absolute value from our calculation
            expected_top_3 = sorted(
                symptom_shap_aggregated.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )[:3]
            
            # The contributors should match the expected top 3
            # Verify that we got the right number (up to 3)
            assert len(explanation.top_contributors) <= len(expected_top_3), (
                f"Should have at most {len(expected_top_3)} contributors, "
                f"got {len(explanation.top_contributors)}"
            )
            
            # Verify that the contributors match the expected top contributors
            for i, (contrib_symptom, contrib_shap) in enumerate(explanation.top_contributors):
                expected_symptom, expected_shap = expected_top_3[i]
                
                assert contrib_symptom == expected_symptom, (
                    f"Contributor {i} should be '{expected_symptom}', got '{contrib_symptom}'"
                )
                
                # SHAP values should match (with small tolerance for floating point)
                assert abs(contrib_shap - expected_shap) < 1e-6, (
                    f"Contributor {i} SHAP value should be {expected_shap}, "
                    f"got {contrib_shap}"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
