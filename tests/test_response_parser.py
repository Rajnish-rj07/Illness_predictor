"""
Unit tests for LLM response parser and validator.
"""

import pytest
import json

from src.llm.response_parser import (
    ResponseParser,
    ParsedSymptomResponse,
    ValidationResult,
)
from src.models.data_models import SymptomInfo


class TestResponseParser:
    """Test response parser functionality."""
    
    def test_parse_valid_symptom_extraction(self):
        """Should parse valid symptom extraction response."""
        parser = ResponseParser()
        
        response_json = json.dumps({
            "symptoms": [
                {
                    "name": "fever",
                    "present": True,
                    "severity": 8,
                    "duration": "1-3d",
                    "description": "High temperature",
                    "confidence": "high"
                },
                {
                    "name": "headache",
                    "present": True,
                    "severity": 6,
                    "duration": "3-7d",
                    "description": "Dull pain",
                    "confidence": "medium"
                }
            ],
            "needs_clarification": [],
            "is_health_related": True
        })
        
        result = parser.parse_symptom_extraction(response_json)
        
        assert isinstance(result, ParsedSymptomResponse)
        assert len(result.symptoms) == 2
        assert "fever" in result.symptoms
        assert "headache" in result.symptoms
        assert result.symptoms["fever"].severity == 8
        assert result.symptoms["fever"].duration == "1-3d"
        assert result.is_health_related is True
    
    def test_parse_symptom_with_clarification_needs(self):
        """Should parse symptoms with clarification needs."""
        parser = ResponseParser()
        
        response_json = json.dumps({
            "symptoms": [
                {
                    "name": "cough",
                    "present": True,
                    "severity": None,
                    "duration": None,
                    "description": "Patient mentioned cough",
                    "confidence": "low"
                }
            ],
            "needs_clarification": [
                {
                    "symptom": "cough",
                    "question": "How severe is your cough on a scale of 1-10?"
                }
            ],
            "is_health_related": True
        })
        
        result = parser.parse_symptom_extraction(response_json)
        
        assert len(result.symptoms) == 1
        assert result.symptoms["cough"].severity is None
        assert len(result.needs_clarification) == 1
        assert result.needs_clarification[0]["symptom"] == "cough"
    
    def test_parse_off_topic_message(self):
        """Should identify off-topic messages."""
        parser = ResponseParser()
        
        response_json = json.dumps({
            "symptoms": [],
            "needs_clarification": [],
            "is_health_related": False
        })
        
        result = parser.parse_symptom_extraction(response_json)
        
        assert len(result.symptoms) == 0
        assert result.is_health_related is False
    
    def test_parse_invalid_json(self):
        """Should raise ValueError for invalid JSON."""
        parser = ResponseParser()
        
        with pytest.raises(ValueError, match="Invalid JSON"):
            parser.parse_symptom_extraction("Not valid JSON")
    
    def test_parse_missing_required_fields(self):
        """Should raise ValueError for missing required fields."""
        parser = ResponseParser()
        
        # Missing 'symptoms' field
        response_json = json.dumps({
            "is_health_related": True
        })
        
        with pytest.raises(ValueError, match="Invalid response"):
            parser.parse_symptom_extraction(response_json)
    
    def test_validate_symptom_response_valid(self):
        """Should validate correct symptom response."""
        parser = ResponseParser()
        
        data = {
            "symptoms": [
                {
                    "name": "fever",
                    "present": True,
                    "severity": 8,
                    "duration": "1-3d"
                }
            ],
            "needs_clarification": [],
            "is_health_related": True
        }
        
        result = parser.validate_symptom_response(data)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_symptom_response_invalid_severity(self):
        """Should detect invalid severity values."""
        parser = ResponseParser()
        
        data = {
            "symptoms": [
                {
                    "name": "fever",
                    "present": True,
                    "severity": 15,  # Invalid: > 10
                    "duration": "1-3d"
                }
            ],
            "is_health_related": True
        }
        
        result = parser.validate_symptom_response(data)
        
        assert result.is_valid is False
        assert any("severity" in error.lower() for error in result.errors)
    
    def test_validate_symptom_response_invalid_duration(self):
        """Should detect invalid duration values."""
        parser = ResponseParser()
        
        data = {
            "symptoms": [
                {
                    "name": "fever",
                    "present": True,
                    "severity": 8,
                    "duration": "invalid"  # Invalid duration
                }
            ],
            "is_health_related": True
        }
        
        result = parser.validate_symptom_response(data)
        
        assert result.is_valid is False
        assert any("duration" in error.lower() for error in result.errors)
    
    def test_sanitize_symptom_name(self):
        """Should normalize symptom names."""
        parser = ResponseParser()
        
        # Test lowercase conversion
        assert parser.sanitize_symptom_name("FEVER") == "fever"
        
        # Test whitespace removal
        assert parser.sanitize_symptom_name("  fever  ") == "fever"
        
        # Test common mappings
        assert parser.sanitize_symptom_name("tummy ache") == "abdominal pain"
        assert parser.sanitize_symptom_name("stomach ache") == "abdominal pain"
        assert parser.sanitize_symptom_name("runny nose") == "nasal congestion"
    
    def test_merge_symptoms_new(self):
        """Should add new symptoms when merging."""
        parser = ResponseParser()
        
        existing = {}
        new = [
            SymptomInfo(
                present=True,
                severity=8,
                duration="1-3d",
                description="High fever"
            )
        ]
        
        # Manually set name for test
        new[0].name = "fever"
        
        merged = parser.merge_symptoms(existing, new)
        
        assert "fever" in merged
        assert merged["fever"].severity == 8
    
    def test_merge_symptoms_update_existing(self):
        """Should update existing symptoms when merging."""
        parser = ResponseParser()
        
        existing = {
            "fever": SymptomInfo(
                present=True,
                severity=None,
                duration=None,
                description="Patient has fever"
            )
        }
        
        new = [
            SymptomInfo(
                present=True,
                severity=8,
                duration="1-3d",
                description="High temperature"
            )
        ]
        new[0].name = "fever"
        
        merged = parser.merge_symptoms(existing, new)
        
        assert merged["fever"].severity == 8
        assert merged["fever"].duration == "1-3d"
        assert "High temperature" in merged["fever"].description
    
    def test_extract_clarification_needs(self):
        """Should identify symptoms needing clarification."""
        parser = ResponseParser()
        
        symptoms = {
            "fever": SymptomInfo(
                present=True,
                severity=None,  # Missing
                duration="1-3d",
                description="Has fever"
            ),
            "headache": SymptomInfo(
                present=True,
                severity=7,
                duration=None,  # Missing
                description="Head hurts"
            ),
            "cough": SymptomInfo(
                present=True,
                severity=5,
                duration="3-7d",
                description="Dry cough"
            )
        }
        
        needs = parser.extract_clarification_needs(symptoms)
        
        assert len(needs) == 2
        symptom_names = [n["symptom"] for n in needs]
        assert "fever" in symptom_names
        assert "headache" in symptom_names
        assert "cough" not in symptom_names
    
    def test_parse_language_detection(self):
        """Should parse language detection response."""
        parser = ResponseParser()
        
        response_json = json.dumps({
            "language_code": "es",
            "language_name": "Spanish",
            "confidence": 0.95
        })
        
        code, name, confidence = parser.parse_language_detection(response_json)
        
        assert code == "es"
        assert name == "Spanish"
        assert confidence == 0.95
    
    def test_parse_validation_response(self):
        """Should parse validation response."""
        parser = ResponseParser()
        
        response_json = json.dumps({
            "is_valid": False,
            "issues": ["Severity out of range"],
            "suggestions": ["Use values 1-10 for severity"]
        })
        
        result = parser.parse_validation_response(response_json)
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1


class TestValidationResult:
    """Test ValidationResult dataclass."""
    
    def test_validation_result_creation(self):
        """Should create ValidationResult with all fields."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Minor issue"]
        )
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 1


class TestParsedSymptomResponse:
    """Test ParsedSymptomResponse dataclass."""
    
    def test_parsed_symptom_response_creation(self):
        """Should create ParsedSymptomResponse with all fields."""
        symptoms = {
            "fever": SymptomInfo(
                present=True,
                severity=8,
                duration="1-3d",
                description="High fever"
            )
        }
        
        response = ParsedSymptomResponse(
            symptoms=symptoms,
            needs_clarification=[],
            is_health_related=True,
            raw_response={"test": "data"}
        )
        
        assert len(response.symptoms) == 1
        assert response.is_health_related is True
        assert "test" in response.raw_response
