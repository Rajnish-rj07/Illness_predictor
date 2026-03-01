"""
Property-based tests for TreatmentService.

These tests use hypothesis to verify universal properties that should hold
for all valid inputs to the TreatmentService.

Properties tested:
- Property 34: Medication suggestion safety (Requirements 18.1, 18.2, 18.3)
- Property 35: High severity medication blocking (Requirement 18.4)
- Property 36: Non-medication option inclusion (Requirement 18.5)

Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
"""

import pytest
from hypothesis import given, strategies as st, settings
from src.treatment.treatment_service import TreatmentService
from src.models.data_models import Severity, Prediction, TreatmentInfo
from src.treatment.treatment_database import get_all_illnesses


# Custom strategies for generating test data

@st.composite
def illness_names(draw):
    """Generate valid illness names from the treatment database."""
    illnesses = get_all_illnesses()
    if illnesses:
        return draw(st.sampled_from(illnesses))
    else:
        # Fallback to common illnesses if database is empty
        return draw(st.sampled_from([
            "common_cold", "influenza", "pneumonia", "meningitis",
            "gastroenteritis", "migraine", "bronchitis"
        ]))


@st.composite
def severity_levels(draw):
    """Generate valid severity levels."""
    return draw(st.sampled_from([Severity.LOW, Severity.MODERATE, Severity.HIGH, Severity.CRITICAL]))


@st.composite
def low_moderate_severity(draw):
    """Generate only LOW or MODERATE severity levels."""
    return draw(st.sampled_from([Severity.LOW, Severity.MODERATE]))


@st.composite
def high_critical_severity(draw):
    """Generate only HIGH or CRITICAL severity levels."""
    return draw(st.sampled_from([Severity.HIGH, Severity.CRITICAL]))


@st.composite
def predictions(draw):
    """Generate valid Prediction objects."""
    illness = draw(illness_names())
    confidence = draw(st.floats(min_value=0.30, max_value=1.0))
    severity = draw(severity_levels())
    
    return Prediction(
        illness=illness,
        confidence_score=confidence,
        severity=severity,
        explanation=None,
        treatment_suggestions=None,
    )


class TestTreatmentServiceProperties:
    """Property-based tests for TreatmentService."""
    
    # Property 34: Medication suggestion safety
    # Validates: Requirements 18.1, 18.2, 18.3
    
    @given(
        illness=illness_names(),
        severity=low_moderate_severity(),
    )
    @settings(max_examples=20)  # Reduced from 100 for faster execution
    def test_property_34_medication_suggestion_safety(self, illness, severity):
        """
        Property 34: Medication suggestion safety
        
        For any prediction with Low or Moderate severity, medication suggestions
        should include both disclaimer text and professional consultation recommendation.
        
        **Validates: Requirements 18.1, 18.2, 18.3**
        """
        # Create service instance
        treatment_service = TreatmentService()
        
        # Get treatment suggestions
        treatment = treatment_service.get_treatment_suggestions(illness, severity)
        
        # Verify treatment info is returned
        assert isinstance(treatment, TreatmentInfo), \
            f"Treatment should be TreatmentInfo, got {type(treatment)}"
        
        # Verify disclaimer is present and non-empty
        assert treatment.disclaimer is not None, \
            f"Disclaimer should not be None for {severity.value} severity"
        assert len(treatment.disclaimer) > 0, \
            f"Disclaimer should not be empty for {severity.value} severity"
        
        # Verify disclaimer contains safety information
        disclaimer_lower = treatment.disclaimer.lower()
        assert any(keyword in disclaimer_lower for keyword in [
            "informational", "not medical advice", "consult", "healthcare professional",
            "disclaimer", "important"
        ]), f"Disclaimer should contain safety information for {severity.value} severity"
        
        # Verify professional consultation is recommended
        assert treatment.seek_professional is True, \
            f"seek_professional should be True for {severity.value} severity"
        
        # Verify disclaimer mentions professional consultation
        assert any(keyword in disclaimer_lower for keyword in [
            "consult", "healthcare professional", "doctor", "medical"
        ]), f"Disclaimer should recommend professional consultation for {severity.value} severity"
    
    # Property 35: High severity medication blocking
    # Validates: Requirement 18.4
    
    @given(
        illness=illness_names(),
        severity=high_critical_severity(),
    )
    @settings(max_examples=20)  # Reduced from 100 for faster execution
    def test_property_35_high_severity_medication_blocking(self, illness, severity):
        """
        Property 35: High severity medication blocking
        
        For any prediction with High or Critical severity, the response should not
        contain medication suggestions and should instead recommend immediate medical attention.
        
        **Validates: Requirement 18.4**
        """
        # Create service instance
        treatment_service = TreatmentService()
        
        # Get treatment suggestions
        treatment = treatment_service.get_treatment_suggestions(illness, severity)
        
        # Verify treatment info is returned
        assert isinstance(treatment, TreatmentInfo), \
            f"Treatment should be TreatmentInfo, got {type(treatment)}"
        
        # Verify NO medication suggestions for high/critical severity
        assert len(treatment.medications) == 0, \
            f"High/Critical severity should have NO medication suggestions, " \
            f"but got {len(treatment.medications)} medications for {illness} ({severity.value})"
        
        # Verify disclaimer contains emergency/immediate care language
        disclaimer_lower = treatment.disclaimer.lower()
        assert any(keyword in disclaimer_lower for keyword in [
            "immediate", "emergency", "urgent", "critical", "serious"
        ]), f"Disclaimer should recommend immediate care for {severity.value} severity"
        
        # Verify professional consultation is strongly recommended
        assert treatment.seek_professional is True, \
            f"seek_professional should be True for {severity.value} severity"
    
    # Property 36: Non-medication option inclusion
    # Validates: Requirement 18.5
    
    @given(
        illness=illness_names(),
        severity=severity_levels(),
    )
    @settings(max_examples=20)  # Reduced from 100 for faster execution
    def test_property_36_non_medication_option_inclusion(self, illness, severity):
        """
        Property 36: Non-medication option inclusion
        
        For any prediction, the treatment suggestions should include at least one
        non-medication option (rest, hydration, dietary recommendation, etc.).
        
        **Validates: Requirement 18.5**
        """
        # Create service instance
        treatment_service = TreatmentService()
        
        # Get treatment suggestions
        treatment = treatment_service.get_treatment_suggestions(illness, severity)
        
        # Verify treatment info is returned
        assert isinstance(treatment, TreatmentInfo), \
            f"Treatment should be TreatmentInfo, got {type(treatment)}"
        
        # Verify non-medication options are present
        assert treatment.non_medication is not None, \
            f"non_medication should not be None for {illness} ({severity.value})"
        assert len(treatment.non_medication) > 0, \
            f"All predictions should include at least one non-medication option, " \
            f"but got 0 for {illness} ({severity.value})"
        
        # Verify non-medication options are strings
        assert all(isinstance(option, str) for option in treatment.non_medication), \
            f"All non-medication options should be strings for {illness} ({severity.value})"
        
        # Verify non-medication options are non-empty
        assert all(len(option) > 0 for option in treatment.non_medication), \
            f"All non-medication options should be non-empty for {illness} ({severity.value})"
    
    # Additional property tests for comprehensive coverage
    
    @given(prediction=predictions())
    @settings(max_examples=20)
    def test_property_treatment_for_prediction_object(self, prediction):
        """
        Property: Treatment can be retrieved for any valid Prediction object.
        
        This tests the get_treatment_for_prediction method with various prediction inputs.
        """
        # Create service instance
        treatment_service = TreatmentService()
        
        # Get treatment for prediction
        treatment = treatment_service.get_treatment_for_prediction(prediction)
        
        # Verify treatment info is returned
        assert isinstance(treatment, TreatmentInfo), \
            f"Treatment should be TreatmentInfo, got {type(treatment)}"
        
        # Verify basic structure
        assert treatment.medications is not None
        assert treatment.non_medication is not None
        assert treatment.disclaimer is not None
        assert isinstance(treatment.seek_professional, bool)
        
        # Verify severity-based filtering
        if prediction.severity in [Severity.HIGH, Severity.CRITICAL]:
            assert len(treatment.medications) == 0, \
                f"High/Critical predictions should have no medications"
        
        # Verify non-medication options always present
        assert len(treatment.non_medication) > 0, \
            f"Non-medication options should always be present"
    
    @given(
        illness=illness_names(),
        severity=severity_levels(),
    )
    @settings(max_examples=20)
    def test_property_treatment_consistency(self, illness, severity):
        """
        Property: Treatment suggestions are consistent for the same illness and severity.
        
        Calling get_treatment_suggestions multiple times with the same inputs
        should return the same treatment information.
        """
        # Create service instance
        treatment_service = TreatmentService()
        
        # Get treatment twice
        treatment1 = treatment_service.get_treatment_suggestions(illness, severity)
        treatment2 = treatment_service.get_treatment_suggestions(illness, severity)
        
        # Verify consistency
        assert treatment1.medications == treatment2.medications, \
            f"Medications should be consistent for {illness} ({severity.value})"
        assert treatment1.non_medication == treatment2.non_medication, \
            f"Non-medication options should be consistent for {illness} ({severity.value})"
        assert treatment1.disclaimer == treatment2.disclaimer, \
            f"Disclaimer should be consistent for {illness} ({severity.value})"
        assert treatment1.seek_professional == treatment2.seek_professional, \
            f"seek_professional should be consistent for {illness} ({severity.value})"
    
    @given(
        predictions_list=st.lists(predictions(), min_size=1, max_size=5)
    )
    @settings(max_examples=10)
    def test_property_multiple_predictions_treatment(self, predictions_list):
        """
        Property: Treatment can be retrieved for multiple predictions.
        
        The get_treatment_for_multiple_predictions method should return
        treatment info for each prediction in the list.
        """
        # Create service instance
        treatment_service = TreatmentService()
        
        # Get treatments for all predictions
        treatments = treatment_service.get_treatment_for_multiple_predictions(predictions_list)
        
        # Verify we get the same number of treatments as predictions
        assert len(treatments) == len(predictions_list), \
            f"Should get {len(predictions_list)} treatments, got {len(treatments)}"
        
        # Verify each treatment is valid
        for i, (prediction, treatment) in enumerate(zip(predictions_list, treatments)):
            assert isinstance(treatment, TreatmentInfo), \
                f"Treatment {i} should be TreatmentInfo, got {type(treatment)}"
            
            # Verify severity-based filtering
            if prediction.severity in [Severity.HIGH, Severity.CRITICAL]:
                assert len(treatment.medications) == 0, \
                    f"Treatment {i} for {prediction.severity.value} should have no medications"
            
            # Verify non-medication options present
            assert len(treatment.non_medication) > 0, \
                f"Treatment {i} should have non-medication options"
    
    @given(
        illness=illness_names(),
        severity=severity_levels(),
    )
    @settings(max_examples=20)
    def test_property_disclaimer_always_present(self, illness, severity):
        """
        Property: Disclaimer is always present in treatment suggestions.
        
        For any illness and severity, the treatment should include a disclaimer.
        """
        # Create service instance
        treatment_service = TreatmentService()
        
        # Get treatment
        treatment = treatment_service.get_treatment_suggestions(illness, severity)
        
        # Verify disclaimer is present
        assert treatment.disclaimer is not None, \
            f"Disclaimer should not be None for {illness} ({severity.value})"
        assert len(treatment.disclaimer) > 0, \
            f"Disclaimer should not be empty for {illness} ({severity.value})"
        assert isinstance(treatment.disclaimer, str), \
            f"Disclaimer should be a string for {illness} ({severity.value})"
    
    @given(
        illness=illness_names(),
        severity=severity_levels(),
    )
    @settings(max_examples=20)
    def test_property_seek_professional_always_true(self, illness, severity):
        """
        Property: seek_professional is always True.
        
        For any illness and severity, the treatment should recommend
        seeking professional medical care.
        """
        # Create service instance
        treatment_service = TreatmentService()
        
        # Get treatment
        treatment = treatment_service.get_treatment_suggestions(illness, severity)
        
        # Verify seek_professional is always True
        assert treatment.seek_professional is True, \
            f"seek_professional should always be True for {illness} ({severity.value})"


class TestTreatmentServiceEdgeProperties:
    """Property-based tests for edge cases and boundary conditions."""
    
    @given(
        unknown_illness=st.text(min_size=1, max_size=50).filter(
            lambda x: x not in get_all_illnesses() and x.replace(" ", "_") not in get_all_illnesses()
        ),
        severity=severity_levels(),
    )
    @settings(max_examples=10)
    def test_property_unknown_illness_handling(self, unknown_illness, severity):
        """
        Property: Unknown illnesses return valid default treatment.
        
        For any unknown illness name, the service should return valid
        treatment information with default recommendations.
        """
        # Create service instance
        treatment_service = TreatmentService()
        
        # Get treatment for unknown illness
        treatment = treatment_service.get_treatment_suggestions(unknown_illness, severity)
        
        # Verify treatment info is returned
        assert isinstance(treatment, TreatmentInfo), \
            f"Treatment should be TreatmentInfo for unknown illness"
        
        # Verify basic structure is valid
        assert treatment.medications is not None
        assert treatment.non_medication is not None
        assert len(treatment.non_medication) > 0, \
            f"Unknown illness should have default non-medication options"
        assert treatment.disclaimer is not None
        assert len(treatment.disclaimer) > 0
        assert treatment.seek_professional is True
        
        # Verify severity-based filtering still applies
        if severity in [Severity.HIGH, Severity.CRITICAL]:
            assert len(treatment.medications) == 0, \
                f"High/Critical severity should have no medications even for unknown illness"
    
    @given(
        illness=illness_names(),
        severity=severity_levels(),
    )
    @settings(max_examples=20)
    def test_property_formatted_output_valid(self, illness, severity):
        """
        Property: Formatted treatment output is always valid.
        
        For any treatment, the formatted output should be a non-empty string.
        """
        # Create service instance
        treatment_service = TreatmentService()
        
        # Get treatment
        treatment = treatment_service.get_treatment_suggestions(illness, severity)
        
        # Format treatment
        formatted = treatment_service.format_treatment_info(treatment)
        
        # Verify formatted output is valid
        assert isinstance(formatted, str), \
            f"Formatted output should be a string"
        assert len(formatted) > 0, \
            f"Formatted output should not be empty"
        
        # Verify it contains some expected content
        assert any(keyword in formatted for keyword in [
            "Medications", "medications", "Self-Care", "Recommendations",
            "DISCLAIMER", "consult", "professional"
        ]), f"Formatted output should contain treatment information"
