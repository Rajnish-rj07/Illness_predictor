"""
Unit tests for the treatment database.

Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
"""

import pytest
from src.treatment.treatment_database import (
    get_treatment_info,
    get_base_severity,
    get_all_illnesses,
    illness_exists,
    MEDICATION_DISCLAIMER,
    PROFESSIONAL_CONSULTATION_TEXT,
    EMERGENCY_CONSULTATION_TEXT,
    CRITICAL_CONSULTATION_TEXT,
)
from src.models.data_models import Severity


class TestTreatmentDatabase:
    """Test suite for treatment database functionality."""
    
    def test_get_treatment_info_low_severity(self):
        """Test that low severity illnesses include medications with disclaimers."""
        # Validates: Requirements 18.1, 18.2, 18.3
        treatment = get_treatment_info("common_cold", Severity.LOW)
        
        # Should have medications for low severity
        assert len(treatment["medications"]) > 0
        assert any("Acetaminophen" in med or "Ibuprofen" in med for med in treatment["medications"])
        
        # Should have non-medication options
        assert len(treatment["non_medication"]) > 0
        assert any("rest" in opt.lower() for opt in treatment["non_medication"])
        
        # Should have disclaimer
        assert MEDICATION_DISCLAIMER in treatment["disclaimer"]
        assert PROFESSIONAL_CONSULTATION_TEXT in treatment["disclaimer"]
        
        # Should recommend professional consultation
        assert treatment["seek_professional"] is True
    
    def test_get_treatment_info_moderate_severity(self):
        """Test that moderate severity illnesses include medications with disclaimers."""
        # Validates: Requirements 18.1, 18.2, 18.3
        treatment = get_treatment_info("influenza", Severity.MODERATE)
        
        # Should have medications for moderate severity
        assert len(treatment["medications"]) > 0
        
        # Should have non-medication options
        assert len(treatment["non_medication"]) > 0
        
        # Should have disclaimer
        assert MEDICATION_DISCLAIMER in treatment["disclaimer"]
        assert treatment["seek_professional"] is True
    
    def test_get_treatment_info_high_severity_no_medications(self):
        """Test that high severity illnesses do NOT include medication suggestions."""
        # Validates: Requirement 18.4
        treatment = get_treatment_info("pneumonia", Severity.HIGH)
        
        # Should NOT have medications for high severity
        assert len(treatment["medications"]) == 0
        
        # Should still have non-medication options
        assert len(treatment["non_medication"]) > 0
        
        # Should have emergency consultation text
        assert EMERGENCY_CONSULTATION_TEXT in treatment["disclaimer"]
        assert treatment["seek_professional"] is True
    
    def test_get_treatment_info_critical_severity_no_medications(self):
        """Test that critical severity illnesses do NOT include medication suggestions."""
        # Validates: Requirement 18.4
        treatment = get_treatment_info("meningitis", Severity.CRITICAL)
        
        # Should NOT have medications for critical severity
        assert len(treatment["medications"]) == 0
        
        # Should still have non-medication options
        assert len(treatment["non_medication"]) > 0
        
        # Should have critical consultation text
        assert CRITICAL_CONSULTATION_TEXT in treatment["disclaimer"]
        assert treatment["seek_professional"] is True
    
    def test_non_medication_options_always_included(self):
        """Test that non-medication options are included for all severity levels."""
        # Validates: Requirement 18.5
        severities = [Severity.LOW, Severity.MODERATE, Severity.HIGH, Severity.CRITICAL]
        illnesses = ["common_cold", "influenza", "pneumonia", "meningitis"]
        
        for illness, severity in zip(illnesses, severities):
            treatment = get_treatment_info(illness, severity)
            assert len(treatment["non_medication"]) > 0, \
                f"Non-medication options missing for {illness} at {severity}"
    
    def test_severity_based_filtering(self):
        """Test that severity-based filtering works correctly."""
        # Validates: Requirement 18.4
        
        # Low severity should have medications
        low_treatment = get_treatment_info("tension_headache", Severity.LOW)
        assert len(low_treatment["medications"]) > 0
        
        # Same illness at high severity should NOT have medications
        high_treatment = get_treatment_info("tension_headache", Severity.HIGH)
        assert len(high_treatment["medications"]) == 0
    
    def test_unknown_illness_default_treatment(self):
        """Test that unknown illnesses return safe default treatment info."""
        treatment = get_treatment_info("unknown_illness_xyz", Severity.MODERATE)
        
        # Should have no medications (safe default)
        assert len(treatment["medications"]) == 0
        
        # Should have generic non-medication options
        assert len(treatment["non_medication"]) > 0
        assert any("rest" in opt.lower() for opt in treatment["non_medication"])
        
        # Should recommend professional consultation
        assert treatment["seek_professional"] is True
    
    def test_get_base_severity(self):
        """Test getting base severity for illnesses."""
        assert get_base_severity("common_cold") == Severity.LOW
        assert get_base_severity("influenza") == Severity.MODERATE
        assert get_base_severity("pneumonia") == Severity.HIGH
        assert get_base_severity("meningitis") == Severity.CRITICAL
        
        # Unknown illness should default to MODERATE
        assert get_base_severity("unknown_illness") == Severity.MODERATE
    
    def test_get_all_illnesses(self):
        """Test getting list of all illnesses in database."""
        illnesses = get_all_illnesses()
        
        assert len(illnesses) > 0
        assert "common_cold" in illnesses
        assert "influenza" in illnesses
        assert "meningitis" in illnesses
    
    def test_illness_exists(self):
        """Test checking if illness exists in database."""
        assert illness_exists("common_cold") is True
        assert illness_exists("influenza") is True
        assert illness_exists("unknown_illness_xyz") is False
    
    def test_disclaimer_content(self):
        """Test that disclaimers contain required safety information."""
        # Validates: Requirements 18.2, 18.3
        
        # Check medication disclaimer
        assert "NOT medical advice" in MEDICATION_DISCLAIMER
        assert "healthcare professional" in MEDICATION_DISCLAIMER
        assert "allergies" in MEDICATION_DISCLAIMER.lower()
        
        # Check professional consultation text
        assert "healthcare professional" in PROFESSIONAL_CONSULTATION_TEXT
        assert "medical advice" in PROFESSIONAL_CONSULTATION_TEXT
    
    def test_critical_conditions_have_emergency_guidance(self):
        """Test that critical conditions have appropriate emergency guidance."""
        critical_illnesses = ["appendicitis", "meningitis", "heart_attack", "stroke", "anaphylaxis"]
        
        for illness in critical_illnesses:
            treatment = get_treatment_info(illness, Severity.CRITICAL)
            
            # Should have no medications
            assert len(treatment["medications"]) == 0
            
            # Should have critical consultation text
            assert "CRITICAL" in treatment["disclaimer"] or "URGENT" in treatment["disclaimer"]
            
            # Should seek professional care
            assert treatment["seek_professional"] is True
    
    def test_respiratory_infections_coverage(self):
        """Test that common respiratory infections are covered."""
        respiratory = ["common_cold", "influenza", "bronchitis", "pneumonia", "sinusitis"]
        
        for illness in respiratory:
            assert illness_exists(illness), f"{illness} not in database"
            treatment = get_treatment_info(illness, Severity.LOW)
            assert len(treatment["non_medication"]) > 0
    
    def test_gastrointestinal_issues_coverage(self):
        """Test that common GI issues are covered."""
        gi_issues = ["gastroenteritis", "food_poisoning", "acid_reflux"]
        
        for illness in gi_issues:
            assert illness_exists(illness), f"{illness} not in database"
            treatment = get_treatment_info(illness, Severity.LOW)
            assert len(treatment["non_medication"]) > 0
    
    def test_pain_conditions_coverage(self):
        """Test that common pain conditions are covered."""
        pain_conditions = ["tension_headache", "migraine", "muscle_strain", "back_pain"]
        
        for illness in pain_conditions:
            assert illness_exists(illness), f"{illness} not in database"
            treatment = get_treatment_info(illness, Severity.LOW)
            # Pain conditions should have pain relievers
            assert len(treatment["medications"]) > 0
            assert any("pain" in med.lower() for med in treatment["medications"])


class TestTreatmentDatabaseEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_case_insensitive_illness_lookup(self):
        """Test that illness lookup is case-insensitive."""
        treatment1 = get_treatment_info("common_cold", Severity.LOW)
        treatment2 = get_treatment_info("Common_Cold", Severity.LOW)
        treatment3 = get_treatment_info("COMMON_COLD", Severity.LOW)
        
        # All should return the same treatment
        assert treatment1["medications"] == treatment2["medications"]
        assert treatment1["medications"] == treatment3["medications"]
    
    def test_illness_name_with_spaces(self):
        """Test that illness names with spaces are handled correctly."""
        # Database uses underscores, but function should handle spaces
        treatment = get_treatment_info("common cold", Severity.LOW)
        assert len(treatment["medications"]) > 0
    
    def test_all_severities_seek_professional(self):
        """Test that all severity levels recommend seeking professional care."""
        severities = [Severity.LOW, Severity.MODERATE, Severity.HIGH, Severity.CRITICAL]
        
        for severity in severities:
            treatment = get_treatment_info("common_cold", severity)
            assert treatment["seek_professional"] is True
    
    def test_treatment_info_structure(self):
        """Test that treatment info has the correct structure."""
        treatment = get_treatment_info("common_cold", Severity.LOW)
        
        # Check all required keys are present
        assert "medications" in treatment
        assert "non_medication" in treatment
        assert "disclaimer" in treatment
        assert "seek_professional" in treatment
        
        # Check types
        assert isinstance(treatment["medications"], list)
        assert isinstance(treatment["non_medication"], list)
        assert isinstance(treatment["disclaimer"], str)
        assert isinstance(treatment["seek_professional"], bool)
