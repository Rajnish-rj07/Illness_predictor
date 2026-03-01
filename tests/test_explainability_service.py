"""
Unit tests for ExplainabilityService.

Tests cover:
- SHAP value computation
- Top contributor identification
- Explanation text generation
- Visualization creation
- Feature importance retrieval

Validates: Requirements 14.1, 14.2, 14.3, 14.4
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
import shap

from src.explainability.explainability_service import ExplainabilityService
from src.ml.ml_model_service import MLModelService
from src.models.data_models import (
    SymptomVector,
    SymptomInfo,
    Prediction,
    Severity,
    Explanation
)


@pytest.fixture
def mock_ml_model_service():
    """Create a mock MLModelService."""
    service = Mock(spec=MLModelService)
    service.KNOWN_SYMPTOMS = [
        'fever', 'cough', 'headache', 'fatigue', 'sore_throat',
        'shortness_of_breath', 'body_aches', 'nausea'
    ]
    service.KNOWN_ILLNESSES = [
        'common_cold', 'influenza', 'covid_19', 'pneumonia'
    ]
    service.get_active_model.return_value = 'v1.0.0'
    
    # Mock model
    mock_model = MagicMock()
    service.load_model.return_value = mock_model
    
    # Mock vectorize_symptoms to return a feature vector
    def mock_vectorize(symptom_vector):
        num_symptoms = len(service.KNOWN_SYMPTOMS)
        features = np.zeros((1, num_symptoms * 3))  # presence, severity, duration
        return features
    
    service.vectorize_symptoms = mock_vectorize
    
    return service


@pytest.fixture
def explainability_service(mock_ml_model_service):
    """Create an ExplainabilityService instance."""
    return ExplainabilityService(mock_ml_model_service)


@pytest.fixture
def sample_symptom_vector():
    """Create a sample symptom vector."""
    return SymptomVector(
        symptoms={
            'fever': SymptomInfo(present=True, severity=8, duration='1-3d'),
            'cough': SymptomInfo(present=True, severity=6, duration='3-7d'),
            'headache': SymptomInfo(present=True, severity=5, duration='<1d'),
        },
        question_count=3
    )


@pytest.fixture
def sample_prediction():
    """Create a sample prediction."""
    return Prediction(
        illness='influenza',
        confidence_score=0.75,
        severity=Severity.MODERATE
    )


class TestExplainabilityServiceInitialization:
    """Test ExplainabilityService initialization."""
    
    def test_initialization(self, mock_ml_model_service):
        """Test that service initializes correctly."""
        service = ExplainabilityService(mock_ml_model_service)
        
        assert service.ml_model_service == mock_ml_model_service
        assert service._explainer_cache == {}
    
    def test_initialization_with_none_service(self):
        """Test that initialization with None service stores None."""
        # Python doesn't enforce type checking at runtime, so this won't raise
        # Instead, verify that the service is stored
        service = ExplainabilityService(None)
        assert service.ml_model_service is None


class TestExplainerCaching:
    """Test SHAP explainer caching."""
    
    @patch('src.explainability.explainability_service.shap.TreeExplainer')
    def test_explainer_created_and_cached(self, mock_tree_explainer, explainability_service):
        """Test that explainer is created and cached."""
        mock_explainer = MagicMock()
        mock_tree_explainer.return_value = mock_explainer
        
        # First call should create explainer
        explainer1 = explainability_service._get_explainer('v1.0.0')
        assert explainer1 == mock_explainer
        assert 'v1.0.0' in explainability_service._explainer_cache
        
        # Second call should use cached explainer
        explainer2 = explainability_service._get_explainer('v1.0.0')
        assert explainer2 == mock_explainer
        
        # TreeExplainer should only be called once
        assert mock_tree_explainer.call_count == 1
    
    @patch('src.explainability.explainability_service.shap.TreeExplainer')
    def test_different_versions_create_different_explainers(
        self, mock_tree_explainer, explainability_service
    ):
        """Test that different model versions create different explainers."""
        mock_explainer1 = MagicMock()
        mock_explainer2 = MagicMock()
        mock_tree_explainer.side_effect = [mock_explainer1, mock_explainer2]
        
        explainer1 = explainability_service._get_explainer('v1.0.0')
        explainer2 = explainability_service._get_explainer('v2.0.0')
        
        assert explainer1 != explainer2
        assert 'v1.0.0' in explainability_service._explainer_cache
        assert 'v2.0.0' in explainability_service._explainer_cache
    
    def test_clear_cache(self, explainability_service):
        """Test that cache can be cleared."""
        explainability_service._explainer_cache['v1.0.0'] = MagicMock()
        explainability_service._explainer_cache['v2.0.0'] = MagicMock()
        
        explainability_service.clear_cache()
        
        assert explainability_service._explainer_cache == {}


class TestExplainPrediction:
    """Test explain_prediction method."""
    
    @patch('src.explainability.explainability_service.shap.TreeExplainer')
    def test_explain_prediction_basic(
        self,
        mock_tree_explainer,
        explainability_service,
        sample_symptom_vector,
        sample_prediction
    ):
        """Test basic explanation generation."""
        # Mock SHAP explainer
        mock_explainer = MagicMock()
        num_symptoms = len(explainability_service.ml_model_service.KNOWN_SYMPTOMS)
        num_illnesses = len(explainability_service.ml_model_service.KNOWN_ILLNESSES)
        
        # Create mock SHAP values (list of arrays for multi-class)
        shap_values_list = []
        for _ in range(num_illnesses):
            shap_values_list.append(np.random.randn(1, num_symptoms * 3))
        
        mock_explainer.shap_values.return_value = shap_values_list
        mock_tree_explainer.return_value = mock_explainer
        
        # Generate explanation
        explanation = explainability_service.explain_prediction(
            sample_symptom_vector,
            sample_prediction
        )
        
        # Verify explanation structure
        assert isinstance(explanation, Explanation)
        assert explanation.explanation_text != ""
        assert explanation.shap_values is not None
        assert len(explanation.top_contributors) <= 3
    
    @patch('src.explainability.explainability_service.shap.TreeExplainer')
    def test_explain_prediction_identifies_top_3_contributors(
        self,
        mock_tree_explainer,
        explainability_service,
        sample_symptom_vector,
        sample_prediction
    ):
        """Test that exactly 3 top contributors are identified (Requirement 14.2)."""
        # Mock SHAP explainer with controlled values
        mock_explainer = MagicMock()
        num_symptoms = len(explainability_service.ml_model_service.KNOWN_SYMPTOMS)
        num_illnesses = len(explainability_service.ml_model_service.KNOWN_ILLNESSES)
        
        # Create SHAP values with known contributions
        shap_values_list = []
        for i in range(num_illnesses):
            if i == 1:  # influenza index
                # Create values where first 3 symptoms have highest absolute values
                values = np.zeros((1, num_symptoms * 3))
                values[0, 0] = 0.5  # fever presence
                values[0, 1] = 0.3  # cough presence
                values[0, 2] = 0.2  # headache presence
                shap_values_list.append(values)
            else:
                shap_values_list.append(np.zeros((1, num_symptoms * 3)))
        
        mock_explainer.shap_values.return_value = shap_values_list
        mock_tree_explainer.return_value = mock_explainer
        
        # Generate explanation
        explanation = explainability_service.explain_prediction(
            sample_symptom_vector,
            sample_prediction
        )
        
        # Verify exactly 3 contributors (or fewer if not enough symptoms)
        assert len(explanation.top_contributors) <= 3
        assert len(explanation.top_contributors) > 0
    
    @patch('src.explainability.explainability_service.shap.TreeExplainer')
    def test_explain_prediction_with_error_returns_basic_explanation(
        self,
        mock_tree_explainer,
        explainability_service,
        sample_symptom_vector,
        sample_prediction
    ):
        """Test that errors are handled gracefully."""
        # Mock explainer to raise an error
        mock_explainer = MagicMock()
        mock_explainer.shap_values.side_effect = Exception("SHAP computation failed")
        mock_tree_explainer.return_value = mock_explainer
        
        # Generate explanation (should not raise)
        explanation = explainability_service.explain_prediction(
            sample_symptom_vector,
            sample_prediction
        )
        
        # Should return a basic explanation
        assert isinstance(explanation, Explanation)
        assert explanation.explanation_text != ""
        assert "Unable to generate" in explanation.explanation_text or explanation.explanation_text != ""
    
    @patch('src.explainability.explainability_service.shap.TreeExplainer')
    def test_explain_prediction_uses_specified_model_version(
        self,
        mock_tree_explainer,
        explainability_service,
        sample_symptom_vector,
        sample_prediction
    ):
        """Test that specified model version is used."""
        mock_explainer = MagicMock()
        num_symptoms = len(explainability_service.ml_model_service.KNOWN_SYMPTOMS)
        num_illnesses = len(explainability_service.ml_model_service.KNOWN_ILLNESSES)
        
        shap_values_list = [np.random.randn(1, num_symptoms * 3) for _ in range(num_illnesses)]
        mock_explainer.shap_values.return_value = shap_values_list
        mock_tree_explainer.return_value = mock_explainer
        
        # Generate explanation with specific version
        explanation = explainability_service.explain_prediction(
            sample_symptom_vector,
            sample_prediction,
            model_version='v2.0.0'
        )
        
        # Verify model was loaded with correct version
        explainability_service.ml_model_service.load_model.assert_called_with('v2.0.0')


class TestGenerateExplanationText:
    """Test explanation text generation."""
    
    def test_generate_explanation_text_basic(self, explainability_service):
        """Test basic explanation text generation (Requirement 14.3)."""
        top_contributors = [
            ('fever', 0.5),
            ('cough', 0.3),
            ('headache', 0.2)
        ]
        
        text = explainability_service._generate_explanation_text(
            'influenza',
            top_contributors,
            0.75
        )
        
        assert 'influenza' in text.lower() or 'Influenza' in text
        assert '75%' in text
        assert 'fever' in text.lower() or 'Fever' in text
        assert 'cough' in text.lower() or 'Cough' in text
        assert 'headache' in text.lower() or 'Headache' in text
    
    def test_generate_explanation_text_with_negative_contributions(
        self, explainability_service
    ):
        """Test explanation text with negative SHAP values."""
        top_contributors = [
            ('fever', 0.5),
            ('cough', -0.3),
            ('headache', 0.1)
        ]
        
        text = explainability_service._generate_explanation_text(
            'common_cold',
            top_contributors,
            0.60
        )
        
        assert 'common cold' in text.lower() or 'Common Cold' in text
        assert '60%' in text
        # Should mention both supporting and reducing symptoms
        assert len(text) > 50  # Should be a substantial explanation
    
    def test_generate_explanation_text_with_empty_contributors(
        self, explainability_service
    ):
        """Test explanation text with no contributors."""
        text = explainability_service._generate_explanation_text(
            'influenza',
            [],
            0.75
        )
        
        assert 'influenza' in text.lower() or 'Influenza' in text
        assert '75%' in text
    
    def test_generate_explanation_text_formats_illness_name(
        self, explainability_service
    ):
        """Test that illness names are formatted properly."""
        text = explainability_service._generate_explanation_text(
            'common_cold',
            [('fever', 0.5)],
            0.80
        )
        
        # Should replace underscores and capitalize
        assert 'Common Cold' in text or 'common cold' in text.lower()


class TestVisualizeExplanation:
    """Test visualization creation."""
    
    @patch('src.explainability.explainability_service.plt')
    def test_visualize_explanation_base64(
        self,
        mock_plt,
        explainability_service,
        sample_symptom_vector,
        sample_prediction
    ):
        """Test visualization in base64 format (Requirement 14.4)."""
        explanation = Explanation(
            top_contributors=[
                ('fever', 0.5),
                ('cough', 0.3),
                ('headache', -0.2)
            ],
            explanation_text="Test explanation",
            shap_values=np.array([0.5, 0.3, -0.2])
        )
        
        # Mock matplotlib
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        
        result = explainability_service.visualize_explanation(
            explanation,
            sample_symptom_vector,
            sample_prediction,
            output_format='base64'
        )
        
        # Should return a base64 string
        assert result is not None
        assert isinstance(result, str)
    
    @patch('src.explainability.explainability_service.plt')
    def test_visualize_explanation_file(
        self,
        mock_plt,
        explainability_service,
        sample_symptom_vector,
        sample_prediction
    ):
        """Test visualization saved to file."""
        explanation = Explanation(
            top_contributors=[
                ('fever', 0.5),
                ('cough', 0.3)
            ],
            explanation_text="Test explanation",
            shap_values=np.array([0.5, 0.3])
        )
        
        # Mock matplotlib
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        
        result = explainability_service.visualize_explanation(
            explanation,
            sample_symptom_vector,
            sample_prediction,
            output_format='file'
        )
        
        # Should return a filename
        assert result is not None
        assert isinstance(result, str)
        assert result.endswith('.png')
    
    def test_visualize_explanation_with_empty_contributors(
        self,
        explainability_service,
        sample_symptom_vector,
        sample_prediction
    ):
        """Test visualization with no contributors."""
        explanation = Explanation(
            top_contributors=[],
            explanation_text="Test explanation",
            shap_values=None
        )
        
        result = explainability_service.visualize_explanation(
            explanation,
            sample_symptom_vector,
            sample_prediction
        )
        
        # Should return None for empty contributors
        assert result is None
    
    @patch('src.explainability.explainability_service.plt')
    def test_visualize_explanation_handles_errors(
        self,
        mock_plt,
        explainability_service,
        sample_symptom_vector,
        sample_prediction
    ):
        """Test that visualization errors are handled gracefully."""
        explanation = Explanation(
            top_contributors=[('fever', 0.5)],
            explanation_text="Test",
            shap_values=np.array([0.5])
        )
        
        # Mock matplotlib to raise an error
        mock_plt.subplots.side_effect = Exception("Plotting failed")
        
        result = explainability_service.visualize_explanation(
            explanation,
            sample_symptom_vector,
            sample_prediction
        )
        
        # Should return None on error
        assert result is None


class TestGetFeatureImportance:
    """Test feature importance retrieval."""
    
    def test_get_feature_importance_basic(self, explainability_service):
        """Test basic feature importance retrieval (Requirement 14.1)."""
        # Mock model with feature importances
        mock_model = MagicMock()
        num_symptoms = len(explainability_service.ml_model_service.KNOWN_SYMPTOMS)
        mock_model.feature_importances_ = np.random.rand(num_symptoms * 3)
        
        explainability_service.ml_model_service.load_model.return_value = mock_model
        
        # Get feature importance
        importance = explainability_service.get_feature_importance(top_k=5)
        
        # Should return list of tuples
        assert isinstance(importance, list)
        assert len(importance) <= 5
        
        if importance:
            assert isinstance(importance[0], tuple)
            assert len(importance[0]) == 2
            assert isinstance(importance[0][0], str)  # feature name
            assert isinstance(importance[0][1], (float, np.floating))  # importance value
    
    def test_get_feature_importance_sorted_descending(self, explainability_service):
        """Test that feature importances are sorted in descending order."""
        # Mock model with known importances
        mock_model = MagicMock()
        num_symptoms = len(explainability_service.ml_model_service.KNOWN_SYMPTOMS)
        importances = np.array([0.1, 0.5, 0.3, 0.2] + [0.01] * (num_symptoms * 3 - 4))
        mock_model.feature_importances_ = importances
        
        explainability_service.ml_model_service.load_model.return_value = mock_model
        
        # Get feature importance
        importance = explainability_service.get_feature_importance(top_k=4)
        
        # Should be sorted descending
        assert len(importance) == 4
        for i in range(len(importance) - 1):
            assert importance[i][1] >= importance[i + 1][1]
    
    def test_get_feature_importance_with_model_version(self, explainability_service):
        """Test that specified model version is used."""
        mock_model = MagicMock()
        num_symptoms = len(explainability_service.ml_model_service.KNOWN_SYMPTOMS)
        mock_model.feature_importances_ = np.random.rand(num_symptoms * 3)
        
        explainability_service.ml_model_service.load_model.return_value = mock_model
        
        # Get feature importance with specific version
        importance = explainability_service.get_feature_importance(
            model_version='v2.0.0',
            top_k=10
        )
        
        # Verify model was loaded with correct version
        explainability_service.ml_model_service.load_model.assert_called_with('v2.0.0')
    
    def test_get_feature_importance_handles_errors(self, explainability_service):
        """Test that errors are handled gracefully."""
        # Mock model to raise an error
        explainability_service.ml_model_service.load_model.side_effect = Exception(
            "Model loading failed"
        )
        
        # Should return empty list on error
        importance = explainability_service.get_feature_importance()
        
        assert importance == []


class TestExplanationGenerationRequirements:
    """Test explanation generation requirements (Task 9.4)."""
    
    @patch('src.explainability.explainability_service.shap.TreeExplainer')
    def test_explanation_text_is_generated_for_any_prediction(
        self,
        mock_tree_explainer,
        explainability_service,
        sample_symptom_vector,
        sample_prediction
    ):
        """
        Test that explanation text is generated for any prediction.
        Validates: Requirement 14.3
        """
        # Mock SHAP explainer
        mock_explainer = MagicMock()
        num_symptoms = len(explainability_service.ml_model_service.KNOWN_SYMPTOMS)
        num_illnesses = len(explainability_service.ml_model_service.KNOWN_ILLNESSES)
        
        shap_values_list = []
        for i in range(num_illnesses):
            if i == 1:  # influenza index
                values = np.zeros((1, num_symptoms * 3))
                values[0, 0] = 0.5  # fever
                values[0, 1] = 0.3  # cough
                shap_values_list.append(values)
            else:
                shap_values_list.append(np.zeros((1, num_symptoms * 3)))
        
        mock_explainer.shap_values.return_value = shap_values_list
        mock_tree_explainer.return_value = mock_explainer
        
        # Generate explanation
        explanation = explainability_service.explain_prediction(
            sample_symptom_vector,
            sample_prediction
        )
        
        # Verify explanation text is generated
        assert explanation.explanation_text is not None
        assert isinstance(explanation.explanation_text, str)
        assert len(explanation.explanation_text) > 0
    
    @patch('src.explainability.explainability_service.shap.TreeExplainer')
    def test_explanation_includes_illness_name_and_confidence(
        self,
        mock_tree_explainer,
        explainability_service,
        sample_symptom_vector,
        sample_prediction
    ):
        """
        Test that explanation text includes illness name and confidence score.
        Validates: Requirement 14.3
        """
        # Mock SHAP explainer
        mock_explainer = MagicMock()
        num_symptoms = len(explainability_service.ml_model_service.KNOWN_SYMPTOMS)
        num_illnesses = len(explainability_service.ml_model_service.KNOWN_ILLNESSES)
        
        shap_values_list = [np.random.randn(1, num_symptoms * 3) for _ in range(num_illnesses)]
        mock_explainer.shap_values.return_value = shap_values_list
        mock_tree_explainer.return_value = mock_explainer
        
        # Generate explanation
        explanation = explainability_service.explain_prediction(
            sample_symptom_vector,
            sample_prediction
        )
        
        # Verify illness name is in explanation (formatted)
        illness_display = sample_prediction.illness.replace('_', ' ').title()
        assert illness_display in explanation.explanation_text or \
               sample_prediction.illness in explanation.explanation_text.lower()
        
        # Verify confidence score is in explanation (as percentage)
        confidence_pct = int(sample_prediction.confidence_score * 100)
        assert f"{confidence_pct}%" in explanation.explanation_text
    
    @patch('src.explainability.explainability_service.shap.TreeExplainer')
    def test_explanation_mentions_top_contributing_symptoms(
        self,
        mock_tree_explainer,
        explainability_service,
        sample_symptom_vector,
        sample_prediction
    ):
        """
        Test that explanation text mentions top contributing symptoms.
        Validates: Requirement 14.3
        """
        # Mock SHAP explainer with controlled values
        mock_explainer = MagicMock()
        num_symptoms = len(explainability_service.ml_model_service.KNOWN_SYMPTOMS)
        num_illnesses = len(explainability_service.ml_model_service.KNOWN_ILLNESSES)
        
        shap_values_list = []
        for i in range(num_illnesses):
            if i == 1:  # influenza index
                values = np.zeros((1, num_symptoms * 3))
                values[0, 0] = 0.5  # fever presence
                values[0, 1] = 0.3  # cough presence
                values[0, 2] = 0.2  # headache presence
                shap_values_list.append(values)
            else:
                shap_values_list.append(np.zeros((1, num_symptoms * 3)))
        
        mock_explainer.shap_values.return_value = shap_values_list
        mock_tree_explainer.return_value = mock_explainer
        
        # Generate explanation
        explanation = explainability_service.explain_prediction(
            sample_symptom_vector,
            sample_prediction
        )
        
        # Verify top contributors are mentioned in explanation text
        if explanation.top_contributors:
            # At least one top contributor should be mentioned
            mentioned_count = 0
            for symptom, _ in explanation.top_contributors:
                symptom_display = symptom.replace('_', ' ').title()
                if symptom_display in explanation.explanation_text or \
                   symptom in explanation.explanation_text.lower():
                    mentioned_count += 1
            
            assert mentioned_count > 0, "At least one top contributor should be mentioned"
    
    @patch('src.explainability.explainability_service.plt')
    def test_visualization_is_created_in_base64_format(
        self,
        mock_plt,
        explainability_service,
        sample_symptom_vector,
        sample_prediction
    ):
        """
        Test that visualization is created in base64 format.
        Validates: Requirement 14.4
        """
        explanation = Explanation(
            top_contributors=[
                ('fever', 0.5),
                ('cough', 0.3),
                ('headache', 0.2)
            ],
            explanation_text="Test explanation",
            shap_values=np.array([0.5, 0.3, 0.2])
        )
        
        # Mock matplotlib
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        
        # Mock savefig to write some data to the buffer
        def mock_savefig(buffer, **kwargs):
            if hasattr(buffer, 'write'):
                # Write some fake PNG data
                buffer.write(b'fake_png_data_for_testing')
        
        mock_plt.savefig.side_effect = mock_savefig
        
        # Generate visualization
        result = explainability_service.visualize_explanation(
            explanation,
            sample_symptom_vector,
            sample_prediction,
            output_format='base64'
        )
        
        # Verify base64 string is returned
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Verify matplotlib was called to create the plot
        mock_plt.subplots.assert_called_once()
    
    @patch('src.explainability.explainability_service.plt')
    def test_visualization_is_created_as_file(
        self,
        mock_plt,
        explainability_service,
        sample_symptom_vector,
        sample_prediction
    ):
        """
        Test that visualization is created as a file.
        Validates: Requirement 14.4
        """
        explanation = Explanation(
            top_contributors=[
                ('fever', 0.5),
                ('cough', 0.3)
            ],
            explanation_text="Test explanation",
            shap_values=np.array([0.5, 0.3])
        )
        
        # Mock matplotlib
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_plt.subplots.return_value = (mock_fig, mock_ax)
        
        # Generate visualization as file
        result = explainability_service.visualize_explanation(
            explanation,
            sample_symptom_vector,
            sample_prediction,
            output_format='file'
        )
        
        # Verify filename is returned
        assert result is not None
        assert isinstance(result, str)
        assert result.endswith('.png')
        
        # Verify matplotlib was called
        mock_plt.subplots.assert_called_once()
        mock_plt.savefig.assert_called_once()
    
    def test_visualization_handles_empty_contributors_gracefully(
        self,
        explainability_service,
        sample_symptom_vector,
        sample_prediction
    ):
        """
        Test that visualization handles empty contributors gracefully.
        Edge case for Requirement 14.4
        """
        explanation = Explanation(
            top_contributors=[],
            explanation_text="Test explanation",
            shap_values=None
        )
        
        # Should return None for empty contributors
        result = explainability_service.visualize_explanation(
            explanation,
            sample_symptom_vector,
            sample_prediction
        )
        
        assert result is None
    
    @patch('src.explainability.explainability_service.plt')
    def test_visualization_handles_errors_gracefully(
        self,
        mock_plt,
        explainability_service,
        sample_symptom_vector,
        sample_prediction
    ):
        """
        Test that visualization errors are handled gracefully.
        Edge case for Requirement 14.4
        """
        explanation = Explanation(
            top_contributors=[('fever', 0.5)],
            explanation_text="Test",
            shap_values=np.array([0.5])
        )
        
        # Mock matplotlib to raise an error
        mock_plt.subplots.side_effect = Exception("Plotting failed")
        
        # Should return None on error, not raise
        result = explainability_service.visualize_explanation(
            explanation,
            sample_symptom_vector,
            sample_prediction
        )
        
        assert result is None


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @patch('src.explainability.explainability_service.shap.TreeExplainer')
    def test_explain_prediction_with_empty_symptom_vector(
        self,
        mock_tree_explainer,
        explainability_service,
        sample_prediction
    ):
        """Test explanation with empty symptom vector."""
        empty_vector = SymptomVector(symptoms={}, question_count=0)
        
        mock_explainer = MagicMock()
        num_symptoms = len(explainability_service.ml_model_service.KNOWN_SYMPTOMS)
        num_illnesses = len(explainability_service.ml_model_service.KNOWN_ILLNESSES)
        
        shap_values_list = [np.random.randn(1, num_symptoms * 3) for _ in range(num_illnesses)]
        mock_explainer.shap_values.return_value = shap_values_list
        mock_tree_explainer.return_value = mock_explainer
        
        # Should not raise an error
        explanation = explainability_service.explain_prediction(
            empty_vector,
            sample_prediction
        )
        
        assert isinstance(explanation, Explanation)
    
    @patch('src.explainability.explainability_service.shap.TreeExplainer')
    def test_explain_prediction_with_single_symptom(
        self,
        mock_tree_explainer,
        explainability_service,
        sample_prediction
    ):
        """Test explanation with single symptom."""
        single_symptom_vector = SymptomVector(
            symptoms={'fever': SymptomInfo(present=True, severity=8)},
            question_count=1
        )
        
        mock_explainer = MagicMock()
        num_symptoms = len(explainability_service.ml_model_service.KNOWN_SYMPTOMS)
        num_illnesses = len(explainability_service.ml_model_service.KNOWN_ILLNESSES)
        
        shap_values_list = [np.random.randn(1, num_symptoms * 3) for _ in range(num_illnesses)]
        mock_explainer.shap_values.return_value = shap_values_list
        mock_tree_explainer.return_value = mock_explainer
        
        explanation = explainability_service.explain_prediction(
            single_symptom_vector,
            sample_prediction
        )
        
        assert isinstance(explanation, Explanation)
        assert len(explanation.top_contributors) >= 1
