"""
Unit tests for TreatmentService.

Tests cover:
- Treatment suggestion retrieval for different severity levels
- Medication filtering based on severity
- Non-medication option inclusion
- Disclaimer and professional consultation recommendations
- Integration with treatment database
- Formatting and utility methods

Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
"""

import pytest
from src.treatment.treatment_service import TreatmentService
from src.models.data_models import Severity, Prediction, TreatmentInfo


class TestTreatmentService:
    """Test suite for TreatmentService."""
    
    @pytest.fixture
    def treatment_service(self):
        """Create a TreatmentService instance for testing."""
        return TreatmentService()
    
    # Test basic treatment retrieval
    
    def test_get_treatment_for_low_severity(self, treatment_service):
        """Test that low severity illnesses include medication suggestions."""
        # Validates: Requirements 18.1, 18.2, 18.3
        treatment = treatment_service.get_treatment_suggestions("common_cold", Severity.LOW)
        
        assert isinstance(treatment, TreatmentInfo)
        assert len(treatment.medications) > 0, "Low severity should include medications"
        assert len(treatment.non_medication) > 0, "Should include non-medication options"
        assert treatment.disclaimer is not None
        assert treatment.seek_professional is True
    
    def test_get_treatment_for_moderate_severity(self, treatment_service):
        """Test that moderate severity illnesses include medication suggestions."""
        # Validates: Requirements 18.1, 18.2, 18.3
        treatment = treatment_service.get_treatment_suggestions("influenza", Severity.MODERATE)
        
        assert isinstance(treatment, TreatmentInfo)
        assert len(treatment.medications) > 0, "Moderate severity should include medications"
        assert len(treatment.non_medication) > 0, "Should include non-medication options"
        assert treatment.disclaimer is not None
        assert treatment.seek_professional is True
    
    def test_get_treatment_for_high_severity(self, treatment_service):
        """Test that high severity illnesses do NOT include medication suggestions."""
        # Validates: Requirement 18.4
        treatment = treatment_service.get_treatment_suggestions("pneumonia", Severity.HIGH)
        
        assert isinstance(treatment, TreatmentInfo)
        assert len(treatment.medications) == 0, "High severity should NOT include medications"
        assert len(treatment.non_medication) > 0, "Should still include non-medication options"
        assert treatment.disclaimer is not None
        assert "immediate" in treatment.disclaimer.lower() or "emergency" in treatment.disclaimer.lower()
        assert treatment.seek_professional is True
    
    def test_get_treatment_for_critical_severity(self, treatment_service):
        """Test that critical severity illnesses do NOT include medication suggestions."""
        # Validates: Requirement 18.4
        treatment = treatment_service.get_treatment_suggestions("meningitis", Severity.CRITICAL)
        
        assert isinstance(treatment, TreatmentInfo)
        assert len(treatment.medications) == 0, "Critical severity should NOT include medications"
        assert len(treatment.non_medication) > 0, "Should still include non-medication options"
        assert treatment.disclaimer is not None
        assert "CRITICAL" in treatment.disclaimer or "emergency" in treatment.disclaimer.lower()
        assert treatment.seek_professional is True
    
    # Test non-medication option inclusion
    
    def test_non_medication_options_always_included(self, treatment_service):
        """Test that non-medication options are included for all severity levels."""
        # Validates: Requirement 18.5
        severities = [Severity.LOW, Severity.MODERATE, Severity.HIGH, Severity.CRITICAL]
        illnesses = ["common_cold", "influenza", "pneumonia", "meningitis"]
        
        for illness, severity in zip(illnesses, severities):
            treatment = treatment_service.get_treatment_suggestions(illness, severity)
            assert len(treatment.non_medication) > 0, \
                f"Non-medication options should be included for {severity.value} severity"
    
    # Test disclaimer inclusion
    
    def test_disclaimer_included_for_low_moderate(self, treatment_service):
        """Test that disclaimers are included for low/moderate severity."""
        # Validates: Requirements 18.2, 18.3
        treatment_low = treatment_service.get_treatment_suggestions("common_cold", Severity.LOW)
        treatment_mod = treatment_service.get_treatment_suggestions("influenza", Severity.MODERATE)
        
        assert treatment_low.disclaimer is not None
        assert len(treatment_low.disclaimer) > 0
        assert "informational" in treatment_low.disclaimer.lower() or "not medical advice" in treatment_low.disclaimer.lower()
        
        assert treatment_mod.disclaimer is not None
        assert len(treatment_mod.disclaimer) > 0
    
    def test_emergency_disclaimer_for_high_critical(self, treatment_service):
        """Test that emergency disclaimers are included for high/critical severity."""
        # Validates: Requirement 18.4
        treatment_high = treatment_service.get_treatment_suggestions("pneumonia", Severity.HIGH)
        treatment_critical = treatment_service.get_treatment_suggestions("meningitis", Severity.CRITICAL)
        
        assert treatment_high.disclaimer is not None
        assert "immediate" in treatment_high.disclaimer.lower() or "emergency" in treatment_high.disclaimer.lower()
        
        assert treatment_critical.disclaimer is not None
        assert "CRITICAL" in treatment_critical.disclaimer or "emergency" in treatment_critical.disclaimer.lower()
    
    # Test professional consultation recommendation
    
    def test_seek_professional_always_true(self, treatment_service):
        """Test that seek_professional is always True."""
        # Validates: Requirement 18.3
        severities = [Severity.LOW, Severity.MODERATE, Severity.HIGH, Severity.CRITICAL]
        illnesses = ["common_cold", "influenza", "pneumonia", "meningitis"]
        
        for illness, severity in zip(illnesses, severities):
            treatment = treatment_service.get_treatment_suggestions(illness, severity)
            assert treatment.seek_professional is True, \
                f"seek_professional should always be True for {severity.value} severity"
    
    # Test get_treatment_for_prediction method
    
    def test_get_treatment_for_prediction(self, treatment_service):
        """Test getting treatment for a Prediction object."""
        prediction = Prediction(
            illness="common_cold",
            confidence_score=0.85,
            severity=Severity.LOW,
            explanation=None,
            treatment_suggestions=None,
        )
        
        treatment = treatment_service.get_treatment_for_prediction(prediction)
        
        assert isinstance(treatment, TreatmentInfo)
        assert len(treatment.medications) > 0
        assert len(treatment.non_medication) > 0
    
    def test_get_treatment_for_multiple_predictions(self, treatment_service):
        """Test getting treatment for multiple predictions."""
        predictions = [
            Prediction(
                illness="common_cold",
                confidence_score=0.85,
                severity=Severity.LOW,
                explanation=None,
                treatment_suggestions=None,
            ),
            Prediction(
                illness="influenza",
                confidence_score=0.75,
                severity=Severity.MODERATE,
                explanation=None,
                treatment_suggestions=None,
            ),
            Prediction(
                illness="pneumonia",
                confidence_score=0.65,
                severity=Severity.HIGH,
                explanation=None,
                treatment_suggestions=None,
            ),
        ]
        
        treatments = treatment_service.get_treatment_for_multiple_predictions(predictions)
        
        assert len(treatments) == 3
        assert all(isinstance(t, TreatmentInfo) for t in treatments)
        
        # First two should have medications, third should not
        assert len(treatments[0].medications) > 0
        assert len(treatments[1].medications) > 0
        assert len(treatments[2].medications) == 0
    
    # Test utility methods
    
    def test_check_illness_exists(self, treatment_service):
        """Test checking if illness exists in database."""
        assert treatment_service.check_illness_exists("common_cold") is True
        assert treatment_service.check_illness_exists("influenza") is True
        assert treatment_service.check_illness_exists("nonexistent_illness") is False
    
    def test_get_base_severity_for_illness(self, treatment_service):
        """Test getting base severity for an illness."""
        assert treatment_service.get_base_severity_for_illness("common_cold") == Severity.LOW
        assert treatment_service.get_base_severity_for_illness("influenza") == Severity.MODERATE
        assert treatment_service.get_base_severity_for_illness("pneumonia") == Severity.HIGH
        assert treatment_service.get_base_severity_for_illness("meningitis") == Severity.CRITICAL
        
        # Unknown illness should default to MODERATE
        assert treatment_service.get_base_severity_for_illness("unknown_illness") == Severity.MODERATE
    
    def test_format_treatment_info(self, treatment_service):
        """Test formatting treatment information."""
        treatment = treatment_service.get_treatment_suggestions("common_cold", Severity.LOW)
        formatted = treatment_service.format_treatment_info(treatment)
        
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        assert "Medications" in formatted or "medications" in formatted
        assert "Self-Care" in formatted or "Recommendations" in formatted
    
    def test_format_treatment_info_without_disclaimer(self, treatment_service):
        """Test formatting treatment information without disclaimer."""
        treatment = treatment_service.get_treatment_suggestions("common_cold", Severity.LOW)
        formatted = treatment_service.format_treatment_info(treatment, include_disclaimer=False)
        
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        # Disclaimer should not be in the formatted output
        assert "DISCLAIMER" not in formatted
    
    def test_has_emergency_recommendations(self, treatment_service):
        """Test checking for emergency recommendations."""
        treatment_low = treatment_service.get_treatment_suggestions("common_cold", Severity.LOW)
        treatment_critical = treatment_service.get_treatment_suggestions("meningitis", Severity.CRITICAL)
        
        assert treatment_service.has_emergency_recommendations(treatment_low) is False
        assert treatment_service.has_emergency_recommendations(treatment_critical) is True
    
    def test_get_severity_appropriate_message(self, treatment_service):
        """Test getting severity-appropriate messages."""
        msg_low = treatment_service.get_severity_appropriate_message(Severity.LOW)
        msg_moderate = treatment_service.get_severity_appropriate_message(Severity.MODERATE)
        msg_high = treatment_service.get_severity_appropriate_message(Severity.HIGH)
        msg_critical = treatment_service.get_severity_appropriate_message(Severity.CRITICAL)
        
        assert "LOW" in msg_low or "mild" in msg_low.lower()
        assert "MODERATE" in msg_moderate
        assert "HIGH" in msg_high or "serious" in msg_high.lower()
        assert "CRITICAL" in msg_critical or "emergency" in msg_critical.lower()
    
    # Test edge cases
    
    def test_unknown_illness_returns_default_treatment(self, treatment_service):
        """Test that unknown illnesses return default treatment."""
        treatment = treatment_service.get_treatment_suggestions("unknown_illness", Severity.LOW)
        
        assert isinstance(treatment, TreatmentInfo)
        assert len(treatment.non_medication) > 0, "Should have default non-medication options"
        assert treatment.disclaimer is not None
        assert treatment.seek_professional is True
    
    def test_severity_override_for_high_critical(self, treatment_service):
        """Test that high/critical severity overrides medication suggestions."""
        # Even if the illness has medications in the database, high/critical severity should block them
        treatment_high = treatment_service.get_treatment_suggestions("common_cold", Severity.HIGH)
        treatment_critical = treatment_service.get_treatment_suggestions("common_cold", Severity.CRITICAL)
        
        assert len(treatment_high.medications) == 0, "High severity should block medications"
        assert len(treatment_critical.medications) == 0, "Critical severity should block medications"
    
    def test_treatment_consistency_for_same_illness(self, treatment_service):
        """Test that treatment is consistent for the same illness at the same severity."""
        treatment1 = treatment_service.get_treatment_suggestions("common_cold", Severity.LOW)
        treatment2 = treatment_service.get_treatment_suggestions("common_cold", Severity.LOW)
        
        assert treatment1.medications == treatment2.medications
        assert treatment1.non_medication == treatment2.non_medication
        assert treatment1.disclaimer == treatment2.disclaimer
        assert treatment1.seek_professional == treatment2.seek_professional
    
    # Test specific illnesses from the database
    
    def test_respiratory_infections(self, treatment_service):
        """Test treatment for respiratory infections."""
        illnesses = ["common_cold", "influenza", "bronchitis"]
        
        for illness in illnesses:
            treatment = treatment_service.get_treatment_suggestions(illness, Severity.MODERATE)
            assert len(treatment.non_medication) > 0
            # Should include rest and hydration
            non_med_text = " ".join(treatment.non_medication).lower()
            assert "rest" in non_med_text or "sleep" in non_med_text
            assert "hydrat" in non_med_text or "water" in non_med_text or "fluid" in non_med_text
    
    def test_gastrointestinal_issues(self, treatment_service):
        """Test treatment for gastrointestinal issues."""
        treatment = treatment_service.get_treatment_suggestions("gastroenteritis", Severity.MODERATE)
        
        assert len(treatment.medications) > 0
        assert len(treatment.non_medication) > 0
        
        # Should include hydration recommendations
        non_med_text = " ".join(treatment.non_medication).lower()
        assert "hydrat" in non_med_text or "fluid" in non_med_text
    
    def test_critical_conditions(self, treatment_service):
        """Test treatment for critical conditions."""
        critical_illnesses = ["appendicitis", "meningitis", "heart_attack", "stroke"]
        
        for illness in critical_illnesses:
            treatment = treatment_service.get_treatment_suggestions(illness, Severity.CRITICAL)
            
            assert len(treatment.medications) == 0, f"{illness} should have no medications"
            assert len(treatment.non_medication) > 0, f"{illness} should have non-medication guidance"
            assert "CRITICAL" in treatment.disclaimer or "emergency" in treatment.disclaimer.lower()
            assert treatment.seek_professional is True


class TestTreatmentServiceIntegration:
    """Integration tests for TreatmentService with other components."""
    
    @pytest.fixture
    def treatment_service(self):
        """Create a TreatmentService instance for testing."""
        return TreatmentService()
    
    def test_integration_with_prediction_object(self, treatment_service):
        """Test that TreatmentService integrates properly with Prediction objects."""
        # Create a prediction
        prediction = Prediction(
            illness="influenza",
            confidence_score=0.82,
            severity=Severity.MODERATE,
            explanation=None,
            treatment_suggestions=None,
        )
        
        # Get treatment
        treatment = treatment_service.get_treatment_for_prediction(prediction)
        
        # Update prediction with treatment
        prediction.treatment_suggestions = treatment
        
        # Verify
        assert prediction.treatment_suggestions is not None
        assert isinstance(prediction.treatment_suggestions, TreatmentInfo)
        assert len(prediction.treatment_suggestions.medications) > 0
        assert len(prediction.treatment_suggestions.non_medication) > 0
    
    def test_full_workflow_low_severity(self, treatment_service):
        """Test full workflow for low severity prediction."""
        # Simulate a low severity prediction
        prediction = Prediction(
            illness="tension_headache",
            confidence_score=0.75,
            severity=Severity.LOW,
            explanation=None,
            treatment_suggestions=None,
        )
        
        # Get treatment
        treatment = treatment_service.get_treatment_for_prediction(prediction)
        prediction.treatment_suggestions = treatment
        
        # Format for user
        formatted = treatment_service.format_treatment_info(treatment)
        
        # Verify complete workflow
        assert prediction.treatment_suggestions is not None
        assert len(prediction.treatment_suggestions.medications) > 0
        assert "Medications" in formatted or "medications" in formatted
        assert "Self-Care" in formatted or "Recommendations" in formatted
    
    def test_full_workflow_critical_severity(self, treatment_service):
        """Test full workflow for critical severity prediction."""
        # Simulate a critical severity prediction
        prediction = Prediction(
            illness="heart_attack",
            confidence_score=0.88,
            severity=Severity.CRITICAL,
            explanation=None,
            treatment_suggestions=None,
        )
        
        # Get treatment
        treatment = treatment_service.get_treatment_for_prediction(prediction)
        prediction.treatment_suggestions = treatment
        
        # Check for emergency recommendations
        has_emergency = treatment_service.has_emergency_recommendations(treatment)
        
        # Get severity message
        severity_msg = treatment_service.get_severity_appropriate_message(prediction.severity)
        
        # Verify complete workflow
        assert prediction.treatment_suggestions is not None
        assert len(prediction.treatment_suggestions.medications) == 0
        assert has_emergency is True
        assert "CRITICAL" in severity_msg or "emergency" in severity_msg.lower()
