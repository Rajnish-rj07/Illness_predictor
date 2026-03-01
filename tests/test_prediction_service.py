"""
Unit tests for PredictionService.

Tests cover:
- Prediction generation and coordination with MLModelService
- Severity scoring logic
- Confidence threshold filtering
- Top-3 prediction limiting
- Treatment suggestion lookup
- Result formatting
- Edge cases (low confidence, critical severity, multiple high severity)

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 12.1, 12.2, 12.3, 12.4, 12.5
"""

import pytest
from unittest.mock import Mock, MagicMock
from typing import List, Tuple

from src.prediction.prediction_service import PredictionService
from src.models.data_models import (
    SymptomVector,
    SymptomInfo,
    Prediction,
    Severity,
    TreatmentInfo,
)
from src.ml.ml_model_service import MLModelService


@pytest.fixture
def mock_ml_model_service():
    """Create a mock MLModelService."""
    mock_service = Mock(spec=MLModelService)
    return mock_service


@pytest.fixture
def prediction_service(mock_ml_model_service):
    """Create a PredictionService with mocked MLModelService."""
    return PredictionService(ml_model_service=mock_ml_model_service)


@pytest.fixture
def sample_symptom_vector():
    """Create a sample symptom vector."""
    return SymptomVector(
        symptoms={
            'fever': SymptomInfo(present=True, severity=8, duration='1-3d'),
            'cough': SymptomInfo(present=True, severity=6, duration='3-7d'),
            'fatigue': SymptomInfo(present=True, severity=7, duration='1-3d'),
        },
        question_count=5,
        confidence_threshold_met=True,
    )


class TestPredictionGeneration:
    """Test prediction generation and coordination."""
    
    def test_predict_returns_predictions_with_severity_and_treatment(
        self, prediction_service, mock_ml_model_service, sample_symptom_vector
    ):
        """Test that predict() returns predictions with severity and treatment."""
        # Mock ML model predictions
        mock_ml_model_service.predict.return_value = [
            ('influenza', 0.75),
            ('common_cold', 0.45),
            ('bronchitis', 0.35),
        ]
        
        # Generate predictions
        predictions = prediction_service.predict(sample_symptom_vector)
        
        # Verify predictions returned
        assert len(predictions) == 3
        
        # Verify each prediction has required fields
        for pred in predictions:
            assert isinstance(pred, Prediction)
            assert pred.illness in ['influenza', 'common_cold', 'bronchitis']
            assert 0.30 <= pred.confidence_score <= 1.0
            assert isinstance(pred.severity, Severity)
            assert isinstance(pred.treatment_suggestions, TreatmentInfo)
        
        # Verify ML model service was called correctly
        mock_ml_model_service.predict.assert_called_once_with(
            symptom_vector=sample_symptom_vector,
            model_version=None,
            top_k=3,
            confidence_threshold=0.30,
        )
    
    def test_predict_returns_empty_list_when_no_predictions_meet_threshold(
        self, prediction_service, mock_ml_model_service, sample_symptom_vector
    ):
        """Test that predict() returns empty list when no predictions meet threshold."""
        # Mock ML model returning no predictions
        mock_ml_model_service.predict.return_value = []
        
        # Generate predictions
        predictions = prediction_service.predict(sample_symptom_vector)
        
        # Verify empty list returned
        assert predictions == []
    
    def test_predict_limits_to_top_3_predictions(
        self, prediction_service, mock_ml_model_service, sample_symptom_vector
    ):
        """Test that predict() limits results to top 3 predictions (Requirement 3.2)."""
        # Mock ML model predictions (already limited by MLModelService)
        mock_ml_model_service.predict.return_value = [
            ('influenza', 0.75),
            ('common_cold', 0.45),
            ('bronchitis', 0.35),
        ]
        
        # Generate predictions
        predictions = prediction_service.predict(sample_symptom_vector)
        
        # Verify at most 3 predictions
        assert len(predictions) <= 3
    
    def test_predict_passes_model_version_to_ml_service(
        self, prediction_service, mock_ml_model_service, sample_symptom_vector
    ):
        """Test that predict() passes model version to MLModelService."""
        mock_ml_model_service.predict.return_value = [('influenza', 0.75)]
        
        # Generate predictions with specific model version
        prediction_service.predict(sample_symptom_vector, model_version='v2.0.0')
        
        # Verify model version was passed
        mock_ml_model_service.predict.assert_called_once()
        call_kwargs = mock_ml_model_service.predict.call_args[1]
        assert call_kwargs['model_version'] == 'v2.0.0'


class TestSeverityScoring:
    """Test severity scoring logic."""
    
    def test_calculate_severity_returns_base_severity_for_known_illness(
        self, prediction_service
    ):
        """Test that calculate_severity() returns base severity for known illnesses."""
        symptom_vector = SymptomVector(
            symptoms={'fever': SymptomInfo(present=True, severity=7)}
        )
        
        # Test various illnesses
        assert prediction_service.calculate_severity('common_cold', symptom_vector) == Severity.LOW
        assert prediction_service.calculate_severity('influenza', symptom_vector) == Severity.MODERATE
        assert prediction_service.calculate_severity('pneumonia', symptom_vector) == Severity.HIGH
        assert prediction_service.calculate_severity('meningitis', symptom_vector) == Severity.CRITICAL
    
    def test_calculate_severity_escalates_to_critical_with_critical_symptoms(
        self, prediction_service
    ):
        """Test that critical symptoms escalate severity to CRITICAL (Requirement 12.2)."""
        # Symptom vector with critical symptom
        symptom_vector = SymptomVector(
            symptoms={
                'fever': SymptomInfo(present=True, severity=7),
                'chest_pain': SymptomInfo(present=True, severity=9),  # Critical symptom
            }
        )
        
        # Even low severity illness should be escalated
        severity = prediction_service.calculate_severity('common_cold', symptom_vector)
        assert severity == Severity.CRITICAL
    
    def test_calculate_severity_keeps_high_with_many_symptoms(
        self, prediction_service
    ):
        """Test that HIGH severity with many symptoms stays HIGH."""
        # Symptom vector with 6 symptoms
        symptom_vector = SymptomVector(
            symptoms={
                f'symptom_{i}': SymptomInfo(present=True, severity=5)
                for i in range(6)
            }
        )
        
        # High severity illness with many symptoms
        severity = prediction_service.calculate_severity('pneumonia', symptom_vector)
        assert severity == Severity.HIGH
    
    def test_calculate_severity_defaults_to_moderate_for_unknown_illness(
        self, prediction_service
    ):
        """Test that unknown illnesses default to MODERATE severity."""
        symptom_vector = SymptomVector(
            symptoms={'fever': SymptomInfo(present=True, severity=7)}
        )
        
        severity = prediction_service.calculate_severity('unknown_illness', symptom_vector)
        assert severity == Severity.MODERATE


class TestTreatmentSuggestions:
    """Test treatment suggestion lookup."""
    
    def test_get_treatment_suggestions_for_low_severity(
        self, prediction_service
    ):
        """Test treatment suggestions for LOW severity illnesses."""
        treatment = prediction_service.get_treatment_suggestions('common_cold', Severity.LOW)
        
        # Should have medications and non-medication options
        assert len(treatment.medications) > 0
        assert len(treatment.non_medication) > 0
        assert treatment.disclaimer != ""
        assert treatment.seek_professional is True
    
    def test_get_treatment_suggestions_for_moderate_severity(
        self, prediction_service
    ):
        """Test treatment suggestions for MODERATE severity illnesses."""
        treatment = prediction_service.get_treatment_suggestions('influenza', Severity.MODERATE)
        
        # Should have medications and non-medication options
        assert len(treatment.medications) > 0
        assert len(treatment.non_medication) > 0
        assert treatment.disclaimer != ""
        assert treatment.seek_professional is True
    
    def test_get_treatment_suggestions_for_high_severity_no_medications(
        self, prediction_service
    ):
        """Test that HIGH severity has no medication suggestions (Requirement 18.4)."""
        treatment = prediction_service.get_treatment_suggestions('pneumonia', Severity.HIGH)
        
        # Should NOT have medication suggestions
        assert len(treatment.medications) == 0
        # Should have non-medication recommendations (seek care)
        assert len(treatment.non_medication) > 0
        assert any('immediate' in rec.lower() for rec in treatment.non_medication)
        assert treatment.seek_professional is True
        assert 'serious condition' in treatment.disclaimer.lower()
    
    def test_get_treatment_suggestions_for_critical_severity_no_medications(
        self, prediction_service
    ):
        """Test that CRITICAL severity has no medication suggestions (Requirement 18.4)."""
        treatment = prediction_service.get_treatment_suggestions('meningitis', Severity.CRITICAL)
        
        # Should NOT have medication suggestions
        assert len(treatment.medications) == 0
        # Should have urgent care recommendations
        assert len(treatment.non_medication) > 0
        assert any('immediate' in rec.lower() for rec in treatment.non_medication)
        assert treatment.seek_professional is True
        assert 'serious condition' in treatment.disclaimer.lower()
    
    def test_get_treatment_suggestions_includes_disclaimer(
        self, prediction_service
    ):
        """Test that all treatment suggestions include disclaimers (Requirement 18.2)."""
        # Test LOW severity
        treatment_low = prediction_service.get_treatment_suggestions('common_cold', Severity.LOW)
        assert 'DISCLAIMER' in treatment_low.disclaimer or 'informational' in treatment_low.disclaimer.lower()
        
        # Test CRITICAL severity
        treatment_critical = prediction_service.get_treatment_suggestions('meningitis', Severity.CRITICAL)
        assert 'IMPORTANT' in treatment_critical.disclaimer or 'serious' in treatment_critical.disclaimer.lower()
    
    def test_get_treatment_suggestions_for_unknown_illness(
        self, prediction_service
    ):
        """Test treatment suggestions for illnesses not in database."""
        treatment = prediction_service.get_treatment_suggestions('unknown_illness', Severity.MODERATE)
        
        # Should have default non-medication options
        assert len(treatment.non_medication) > 0
        assert treatment.seek_professional is True


class TestSeverityRanking:
    """Test severity-based ranking logic."""
    
    def test_rank_by_severity_when_confidence_similar(
        self, prediction_service
    ):
        """Test that predictions with similar confidence are ranked by severity (Requirement 12.3)."""
        # Create predictions with similar confidence but different severity
        predictions = [
            Prediction(
                illness='common_cold',
                confidence_score=0.75,
                severity=Severity.LOW,
                treatment_suggestions=TreatmentInfo(),
            ),
            Prediction(
                illness='pneumonia',
                confidence_score=0.73,  # Within 10% of 0.75
                severity=Severity.HIGH,
                treatment_suggestions=TreatmentInfo(),
            ),
            Prediction(
                illness='influenza',
                confidence_score=0.74,  # Within 10% of 0.75
                severity=Severity.MODERATE,
                treatment_suggestions=TreatmentInfo(),
            ),
        ]
        
        # Rank by severity
        ranked = prediction_service._rank_by_severity_if_needed(predictions)
        
        # Should be ranked: HIGH > MODERATE > LOW
        assert ranked[0].severity == Severity.HIGH
        assert ranked[1].severity == Severity.MODERATE
        assert ranked[2].severity == Severity.LOW
    
    def test_rank_preserves_order_when_confidence_different(
        self, prediction_service
    ):
        """Test that ranking preserves order when confidence scores differ significantly."""
        predictions = [
            Prediction(
                illness='common_cold',
                confidence_score=0.80,
                severity=Severity.LOW,
                treatment_suggestions=TreatmentInfo(),
            ),
            Prediction(
                illness='pneumonia',
                confidence_score=0.50,  # More than 10% difference
                severity=Severity.HIGH,
                treatment_suggestions=TreatmentInfo(),
            ),
        ]
        
        # Rank by severity
        ranked = prediction_service._rank_by_severity_if_needed(predictions)
        
        # Should preserve original order (confidence-based)
        assert ranked[0].illness == 'common_cold'
        assert ranked[1].illness == 'pneumonia'


class TestResultFormatting:
    """Test result formatting for user presentation."""
    
    def test_format_results_with_predictions(
        self, prediction_service
    ):
        """Test formatting of prediction results."""
        predictions = [
            Prediction(
                illness='influenza',
                confidence_score=0.75,
                severity=Severity.MODERATE,
                treatment_suggestions=TreatmentInfo(
                    medications=['Acetaminophen'],
                    non_medication=['Rest', 'Stay hydrated'],
                    disclaimer='Test disclaimer',
                    seek_professional=True,
                ),
            ),
        ]
        
        result = prediction_service.format_results(predictions)
        
        # Verify formatted output contains key information
        assert 'influenza' in result.lower()
        assert '75' in result  # Confidence percentage
        assert 'moderate' in result.lower()
        assert 'Acetaminophen' in result
        assert 'Rest' in result
    
    def test_format_results_empty_predictions(
        self, prediction_service
    ):
        """Test formatting when no predictions available."""
        result = prediction_service.format_results([])
        
        # Should provide helpful message
        assert 'unable' in result.lower() or 'no' in result.lower()
        assert 'consult' in result.lower() or 'medical' in result.lower()
    
    def test_format_results_includes_emergency_warning_for_critical(
        self, prediction_service
    ):
        """Test that critical predictions include emergency warning."""
        predictions = [
            Prediction(
                illness='meningitis',
                confidence_score=0.85,
                severity=Severity.CRITICAL,
                treatment_suggestions=TreatmentInfo(
                    medications=[],
                    non_medication=['Seek immediate care'],
                    disclaimer='Urgent',
                    seek_professional=True,
                ),
            ),
        ]
        
        result = prediction_service.format_results(predictions)
        
        # Should include emergency warning
        assert 'URGENT' in result or 'emergency' in result.lower() or 'immediate' in result.lower()
    
    def test_format_results_includes_severity_indicators(
        self, prediction_service
    ):
        """Test that formatted results include severity indicators."""
        predictions = [
            Prediction(
                illness='common_cold',
                confidence_score=0.70,
                severity=Severity.LOW,
                treatment_suggestions=TreatmentInfo(),
            ),
        ]
        
        result = prediction_service.format_results(predictions)
        
        # Should include severity level
        assert 'low' in result.lower() or '🟢' in result


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_predict_with_single_symptom(
        self, prediction_service, mock_ml_model_service
    ):
        """Test prediction with minimal symptom vector."""
        symptom_vector = SymptomVector(
            symptoms={'fever': SymptomInfo(present=True, severity=7)}
        )
        
        mock_ml_model_service.predict.return_value = [('influenza', 0.60)]
        
        predictions = prediction_service.predict(symptom_vector)
        
        assert len(predictions) == 1
        assert predictions[0].illness == 'influenza'
    
    def test_predict_with_many_symptoms(
        self, prediction_service, mock_ml_model_service
    ):
        """Test prediction with many symptoms."""
        symptom_vector = SymptomVector(
            symptoms={
                f'symptom_{i}': SymptomInfo(present=True, severity=5)
                for i in range(10)
            }
        )
        
        mock_ml_model_service.predict.return_value = [
            ('pneumonia', 0.80),
            ('bronchitis', 0.50),
        ]
        
        predictions = prediction_service.predict(symptom_vector)
        
        assert len(predictions) == 2
        # With many symptoms, HIGH severity should be maintained
        assert predictions[0].severity == Severity.HIGH
    
    def test_multiple_critical_predictions_logged(
        self, prediction_service, mock_ml_model_service, caplog
    ):
        """Test that multiple critical predictions are logged (Requirement 12.5)."""
        symptom_vector = SymptomVector(
            symptoms={
                'chest_pain': SymptomInfo(present=True, severity=9),
                'shortness_of_breath': SymptomInfo(present=True, severity=8),
            }
        )
        
        mock_ml_model_service.predict.return_value = [
            ('heart_attack', 0.70),
            ('pulmonary_embolism', 0.65),
        ]
        
        with caplog.at_level('WARNING'):
            predictions = prediction_service.predict(symptom_vector)
        
        # Both should be CRITICAL due to critical symptoms
        critical_count = sum(1 for p in predictions if p.severity == Severity.CRITICAL)
        assert critical_count >= 2
        
        # Should log warning about multiple critical predictions
        assert any('critical' in record.message.lower() for record in caplog.records)
    
    def test_severity_calculation_with_empty_symptoms(
        self, prediction_service
    ):
        """Test severity calculation with empty symptom vector."""
        symptom_vector = SymptomVector(symptoms={})
        
        severity = prediction_service.calculate_severity('influenza', symptom_vector)
        
        # Should return base severity
        assert severity == Severity.MODERATE
    
    def test_treatment_suggestions_validation(
        self, prediction_service
    ):
        """Test that treatment suggestions are valid TreatmentInfo objects."""
        treatment = prediction_service.get_treatment_suggestions('common_cold', Severity.LOW)
        
        # Should be valid TreatmentInfo
        assert isinstance(treatment, TreatmentInfo)
        # Should pass validation
        treatment.validate()


class TestSeverityEdgeCases:
    """Test severity edge cases as specified in Task 8.5.
    
    Tests cover:
    - Low confidence predictions (< 30%)
    - Multiple critical predictions
    - Severity ranking with similar confidence scores
    
    Validates: Requirements 3.5, 12.3, 12.5
    """
    
    def test_low_confidence_predictions_filtered_out(
        self, prediction_service, mock_ml_model_service, sample_symptom_vector
    ):
        """Test that predictions below 30% confidence are filtered out (Requirement 3.3, 3.5)."""
        # Mock ML model returning predictions with some below threshold
        # Note: MLModelService already filters, but we test the contract
        mock_ml_model_service.predict.return_value = [
            ('influenza', 0.45),
            ('common_cold', 0.32),
            # Predictions below 30% should already be filtered by MLModelService
        ]
        
        predictions = prediction_service.predict(sample_symptom_vector)
        
        # All returned predictions should have confidence >= 30%
        for pred in predictions:
            assert pred.confidence_score >= 0.30, \
                f"Prediction {pred.illness} has confidence {pred.confidence_score} < 0.30"
        
        # Verify we got the expected predictions
        assert len(predictions) == 2
        assert predictions[0].illness == 'influenza'
        assert predictions[1].illness == 'common_cold'
    
    def test_exactly_30_percent_confidence_included(
        self, prediction_service, mock_ml_model_service, sample_symptom_vector
    ):
        """Test that predictions with exactly 30% confidence are included (boundary case)."""
        # Mock ML model returning prediction at exact threshold
        mock_ml_model_service.predict.return_value = [
            ('influenza', 0.30),  # Exactly at threshold
        ]
        
        predictions = prediction_service.predict(sample_symptom_vector)
        
        # Should include the 30% prediction
        assert len(predictions) == 1
        assert predictions[0].confidence_score == 0.30
        assert predictions[0].illness == 'influenza'
    
    def test_all_predictions_below_threshold_returns_empty(
        self, prediction_service, mock_ml_model_service, sample_symptom_vector
    ):
        """Test that when all predictions are below 30%, empty list is returned (Requirement 3.5)."""
        # Mock ML model returning no predictions (all filtered)
        mock_ml_model_service.predict.return_value = []
        
        predictions = prediction_service.predict(sample_symptom_vector)
        
        # Should return empty list
        assert predictions == []
        assert len(predictions) == 0
    
    def test_multiple_critical_predictions_with_different_illnesses(
        self, prediction_service, mock_ml_model_service
    ):
        """Test handling of multiple critical predictions (Requirement 12.5)."""
        # Symptom vector with critical symptoms
        symptom_vector = SymptomVector(
            symptoms={
                'chest_pain': SymptomInfo(present=True, severity=9, duration='<1d'),
                'shortness_of_breath': SymptomInfo(present=True, severity=8, duration='<1d'),
                'confusion': SymptomInfo(present=True, severity=7, duration='<1d'),
            }
        )
        
        # Mock multiple critical illness predictions
        mock_ml_model_service.predict.return_value = [
            ('heart_attack', 0.65),
            ('pulmonary_embolism', 0.55),
            ('sepsis', 0.45),
        ]
        
        predictions = prediction_service.predict(symptom_vector)
        
        # All should be escalated to CRITICAL due to critical symptoms
        critical_predictions = [p for p in predictions if p.severity == Severity.CRITICAL]
        assert len(critical_predictions) == 3, \
            f"Expected 3 critical predictions, got {len(critical_predictions)}"
        
        # All should have no medication suggestions
        for pred in predictions:
            assert len(pred.treatment_suggestions.medications) == 0, \
                f"Critical prediction {pred.illness} should not have medication suggestions"
            assert pred.treatment_suggestions.seek_professional is True
            assert 'immediate' in pred.treatment_suggestions.disclaimer.lower()
    
    def test_multiple_high_severity_predictions_logged(
        self, prediction_service, mock_ml_model_service, caplog
    ):
        """Test that multiple HIGH severity predictions are properly logged (Requirement 12.5)."""
        symptom_vector = SymptomVector(
            symptoms={
                'fever': SymptomInfo(present=True, severity=9, duration='3-7d'),
                'cough': SymptomInfo(present=True, severity=8, duration='3-7d'),
                'fatigue': SymptomInfo(present=True, severity=7, duration='3-7d'),
            }
        )
        
        # Mock multiple HIGH severity illness predictions
        mock_ml_model_service.predict.return_value = [
            ('pneumonia', 0.70),
            ('covid_19', 0.60),
            ('tuberculosis', 0.50),
        ]
        
        with caplog.at_level('WARNING'):
            predictions = prediction_service.predict(symptom_vector)
        
        # All should be HIGH severity
        high_predictions = [p for p in predictions if p.severity == Severity.HIGH]
        assert len(high_predictions) == 3
        
        # Should log warning about multiple high/critical predictions
        warning_logged = any(
            'high/critical' in record.message.lower() or 'multiple' in record.message.lower()
            for record in caplog.records
        )
        assert warning_logged, "Expected warning log for multiple high severity predictions"
    
    def test_severity_ranking_with_similar_confidence_scores(
        self, prediction_service, mock_ml_model_service
    ):
        """Test that predictions with similar confidence are ranked by severity (Requirement 12.3)."""
        symptom_vector = SymptomVector(
            symptoms={
                'fever': SymptomInfo(present=True, severity=7, duration='1-3d'),
                'cough': SymptomInfo(present=True, severity=6, duration='1-3d'),
            }
        )
        
        # Mock predictions with similar confidence scores (within 10%)
        # Return them in non-severity order to test re-ranking
        mock_ml_model_service.predict.return_value = [
            ('common_cold', 0.75),      # LOW severity
            ('pneumonia', 0.73),        # HIGH severity (within 10% of 0.75)
            ('influenza', 0.74),        # MODERATE severity (within 10% of 0.75)
        ]
        
        predictions = prediction_service.predict(symptom_vector)
        
        # Should be re-ranked by severity: HIGH > MODERATE > LOW
        assert len(predictions) == 3
        assert predictions[0].severity == Severity.HIGH, \
            f"First prediction should be HIGH severity, got {predictions[0].severity}"
        assert predictions[0].illness == 'pneumonia'
        
        assert predictions[1].severity == Severity.MODERATE, \
            f"Second prediction should be MODERATE severity, got {predictions[1].severity}"
        assert predictions[1].illness == 'influenza'
        
        assert predictions[2].severity == Severity.LOW, \
            f"Third prediction should be LOW severity, got {predictions[2].severity}"
        assert predictions[2].illness == 'common_cold'
    
    def test_severity_ranking_preserves_order_when_confidence_differs_significantly(
        self, prediction_service, mock_ml_model_service
    ):
        """Test that severity ranking doesn't override significant confidence differences."""
        symptom_vector = SymptomVector(
            symptoms={
                'fever': SymptomInfo(present=True, severity=7, duration='1-3d'),
            }
        )
        
        # Mock predictions with significantly different confidence scores (>10% difference)
        mock_ml_model_service.predict.return_value = [
            ('common_cold', 0.80),      # LOW severity, high confidence
            ('pneumonia', 0.50),        # HIGH severity, lower confidence (30% difference)
        ]
        
        predictions = prediction_service.predict(symptom_vector)
        
        # Should preserve confidence-based order (not re-rank by severity)
        assert len(predictions) == 2
        assert predictions[0].illness == 'common_cold', \
            "Higher confidence prediction should come first despite lower severity"
        assert predictions[0].confidence_score == 0.80
        
        assert predictions[1].illness == 'pneumonia'
        assert predictions[1].confidence_score == 0.50
    
    def test_severity_ranking_with_three_similar_confidence_scores(
        self, prediction_service, mock_ml_model_service
    ):
        """Test severity ranking with three predictions having similar confidence (edge case)."""
        symptom_vector = SymptomVector(
            symptoms={
                'fever': SymptomInfo(present=True, severity=8, duration='1-3d'),
                'headache': SymptomInfo(present=True, severity=7, duration='1-3d'),
            }
        )
        
        # All three within 10% of each other (0.60 to 0.66)
        mock_ml_model_service.predict.return_value = [
            ('influenza', 0.65),        # MODERATE
            ('common_cold', 0.64),      # LOW
            ('pneumonia', 0.60),        # HIGH
        ]
        
        predictions = prediction_service.predict(symptom_vector)
        
        # Should be re-ranked by severity
        assert len(predictions) == 3
        severities = [p.severity for p in predictions]
        
        # HIGH should come first, then MODERATE, then LOW
        assert severities[0] == Severity.HIGH
        assert severities[1] == Severity.MODERATE
        assert severities[2] == Severity.LOW
    
    def test_critical_and_moderate_predictions_mixed(
        self, prediction_service, mock_ml_model_service
    ):
        """Test handling of mixed severity predictions with critical symptoms present."""
        # Symptom vector with one critical symptom
        symptom_vector = SymptomVector(
            symptoms={
                'chest_pain': SymptomInfo(present=True, severity=9, duration='<1d'),
                'fever': SymptomInfo(present=True, severity=6, duration='1-3d'),
            }
        )
        
        # Mock predictions: some would normally be moderate, but critical symptom escalates
        mock_ml_model_service.predict.return_value = [
            ('heart_attack', 0.70),     # Already CRITICAL
            ('influenza', 0.50),        # Would be MODERATE, escalated to CRITICAL
            ('common_cold', 0.35),      # Would be LOW, escalated to CRITICAL
        ]
        
        predictions = prediction_service.predict(symptom_vector)
        
        # All should be escalated to CRITICAL due to chest_pain
        for pred in predictions:
            assert pred.severity == Severity.CRITICAL, \
                f"Prediction {pred.illness} should be CRITICAL due to critical symptom"
            assert len(pred.treatment_suggestions.medications) == 0
    
    def test_low_confidence_boundary_with_different_severities(
        self, prediction_service, mock_ml_model_service
    ):
        """Test predictions near 30% threshold with different severities."""
        symptom_vector = SymptomVector(
            symptoms={
                'fever': SymptomInfo(present=True, severity=5, duration='1-3d'),
            }
        )
        
        # Mock predictions at or near threshold with different severities
        mock_ml_model_service.predict.return_value = [
            ('pneumonia', 0.32),        # HIGH severity, just above threshold
            ('influenza', 0.31),        # MODERATE severity, just above threshold
            ('common_cold', 0.30),      # LOW severity, exactly at threshold
        ]
        
        predictions = prediction_service.predict(symptom_vector)
        
        # All should be included (all >= 30%)
        assert len(predictions) == 3
        
        # Verify all have correct confidence
        for pred in predictions:
            assert pred.confidence_score >= 0.30
        
        # Should be re-ranked by severity (all within 10%)
        assert predictions[0].severity == Severity.HIGH
        assert predictions[1].severity == Severity.MODERATE
        assert predictions[2].severity == Severity.LOW


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
