"""
Response parsing and validation for LLM outputs.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from src.models.data_models import SymptomInfo

logger = logging.getLogger(__name__)


@dataclass
class ParsedSymptomResponse:
    """Parsed symptom extraction response."""
    symptoms: Dict[str, SymptomInfo]  # Changed from List to Dict
    needs_clarification: List[Dict[str, str]]
    is_health_related: bool
    raw_response: Dict[str, Any]


@dataclass
class ValidationResult:
    """Result of response validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class ResponseParser:
    """Parser for LLM responses with validation."""
    
    # Valid duration values
    VALID_DURATIONS = ["<1d", "1-3d", "3-7d", ">7d"]
    
    # Valid confidence levels
    VALID_CONFIDENCE = ["high", "medium", "low"]
    
    def parse_symptom_extraction(
        self,
        response: str
    ) -> ParsedSymptomResponse:
        """
        Parse symptom extraction response from LLM.
        
        Args:
            response: JSON string from LLM
            
        Returns:
            ParsedSymptomResponse with extracted data
            
        Raises:
            ValueError: If response format is invalid
        """
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response: {e}") from e
        
        # Validate response structure
        validation = self.validate_symptom_response(data)
        if not validation.is_valid:
            logger.error(f"Invalid response structure: {validation.errors}")
            raise ValueError(f"Invalid response: {', '.join(validation.errors)}")
        
        # Parse symptoms
        symptoms = {}
        for symptom_data in data.get("symptoms", []):
            try:
                name, symptom_info = self._parse_symptom_info(symptom_data)
                symptoms[name] = symptom_info
            except Exception as e:
                logger.warning(f"Failed to parse symptom: {e}")
                continue
        
        # Parse clarification needs
        needs_clarification = data.get("needs_clarification", [])
        
        # Check if health-related
        is_health_related = data.get("is_health_related", True)
        
        return ParsedSymptomResponse(
            symptoms=symptoms,
            needs_clarification=needs_clarification,
            is_health_related=is_health_related,
            raw_response=data
        )
    
    def _parse_symptom_info(self, data: Dict[str, Any]) -> Tuple[str, SymptomInfo]:
        """
        Parse symptom info from dict.
        
        Args:
            data: Symptom data dict
            
        Returns:
            Tuple of (symptom_name, SymptomInfo object)
            
        Raises:
            ValueError: If required fields are missing
        """
        if "name" not in data:
            raise ValueError("Symptom name is required")
        
        # Normalize symptom name (lowercase, strip whitespace)
        name = data["name"].strip().lower()
        
        # Parse severity (1-10 or None)
        severity = data.get("severity")
        if severity is not None:
            severity = int(severity)
            if not 1 <= severity <= 10:
                logger.warning(f"Severity {severity} out of range, setting to None")
                severity = None
        
        # Parse duration
        duration = data.get("duration")
        if duration and duration not in self.VALID_DURATIONS:
            logger.warning(f"Invalid duration '{duration}', setting to None")
            duration = None
        
        # Parse description
        description = data.get("description", "")
        
        # Parse present flag
        present = data.get("present", True)
        
        symptom_info = SymptomInfo(
            present=present,
            severity=severity,
            duration=duration,
            description=description
        )
        
        return name, symptom_info
    
    def validate_symptom_response(
        self,
        data: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate symptom extraction response structure.
        
        Args:
            data: Response data to validate
            
        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []
        
        # Check required fields
        if "symptoms" not in data:
            errors.append("Missing 'symptoms' field")
        elif not isinstance(data["symptoms"], list):
            errors.append("'symptoms' must be a list")
        
        if "is_health_related" not in data:
            warnings.append("Missing 'is_health_related' field, assuming True")
        
        # Validate symptoms
        if "symptoms" in data and isinstance(data["symptoms"], list):
            for i, symptom in enumerate(data["symptoms"]):
                symptom_errors = self._validate_symptom(symptom, i)
                errors.extend(symptom_errors)
        
        # Validate clarification needs
        if "needs_clarification" in data:
            if not isinstance(data["needs_clarification"], list):
                errors.append("'needs_clarification' must be a list")
            else:
                for i, clarification in enumerate(data["needs_clarification"]):
                    if not isinstance(clarification, dict):
                        errors.append(f"Clarification {i} must be a dict")
                    elif "symptom" not in clarification or "question" not in clarification:
                        errors.append(f"Clarification {i} missing required fields")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_symptom(
        self,
        symptom: Dict[str, Any],
        index: int
    ) -> List[str]:
        """
        Validate individual symptom data.
        
        Args:
            symptom: Symptom data dict
            index: Index in symptoms list
            
        Returns:
            List of error messages
        """
        errors = []
        
        if not isinstance(symptom, dict):
            errors.append(f"Symptom {index} must be a dict")
            return errors
        
        # Check required fields
        if "name" not in symptom:
            errors.append(f"Symptom {index} missing 'name' field")
        elif not isinstance(symptom["name"], str) or not symptom["name"].strip():
            errors.append(f"Symptom {index} has invalid name")
        
        # Validate severity if present
        if "severity" in symptom and symptom["severity"] is not None:
            try:
                severity = int(symptom["severity"])
                if not 1 <= severity <= 10:
                    errors.append(f"Symptom {index} severity must be 1-10")
            except (ValueError, TypeError):
                errors.append(f"Symptom {index} severity must be an integer")
        
        # Validate duration if present
        if "duration" in symptom and symptom["duration"] is not None:
            if symptom["duration"] not in self.VALID_DURATIONS:
                errors.append(
                    f"Symptom {index} duration must be one of {self.VALID_DURATIONS}"
                )
        
        # Validate confidence if present
        if "confidence" in symptom and symptom["confidence"] is not None:
            if symptom["confidence"] not in self.VALID_CONFIDENCE:
                errors.append(
                    f"Symptom {index} confidence must be one of {self.VALID_CONFIDENCE}"
                )
        
        return errors
    
    def parse_language_detection(
        self,
        response: str
    ) -> Tuple[str, str, float]:
        """
        Parse language detection response.
        
        Args:
            response: JSON string from LLM
            
        Returns:
            Tuple of (language_code, language_name, confidence)
            
        Raises:
            ValueError: If response format is invalid
        """
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}") from e
        
        if "language_code" not in data:
            raise ValueError("Missing 'language_code' field")
        
        language_code = data["language_code"]
        language_name = data.get("language_name", "Unknown")
        confidence = data.get("confidence", 0.0)
        
        return language_code, language_name, confidence
    
    def parse_validation_response(
        self,
        response: str
    ) -> ValidationResult:
        """
        Parse validation response from LLM.
        
        Args:
            response: JSON string from LLM
            
        Returns:
            ValidationResult
            
        Raises:
            ValueError: If response format is invalid
        """
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}") from e
        
        is_valid = data.get("is_valid", False)
        issues = data.get("issues", [])
        suggestions = data.get("suggestions", [])
        
        return ValidationResult(
            is_valid=is_valid,
            errors=issues,
            warnings=suggestions
        )
    
    def sanitize_symptom_name(self, name: str) -> str:
        """
        Sanitize and normalize symptom name.
        
        Args:
            name: Raw symptom name
            
        Returns:
            Normalized symptom name
        """
        # Convert to lowercase
        name = name.lower().strip()
        
        # Remove extra whitespace
        name = " ".join(name.split())
        
        # Common mappings
        mappings = {
            "tummy ache": "abdominal pain",
            "stomach ache": "abdominal pain",
            "belly ache": "abdominal pain",
            "runny nose": "nasal congestion",
            "stuffy nose": "nasal congestion",
            "throwing up": "vomiting",
            "feeling sick": "nausea",
            "temperature": "fever",
            "high temperature": "fever",
        }
        
        return mappings.get(name, name)
    
    def merge_symptoms(
        self,
        existing: Dict[str, SymptomInfo],
        new: List[SymptomInfo]
    ) -> Dict[str, SymptomInfo]:
        """
        Merge new symptoms with existing ones.
        
        Args:
            existing: Existing symptom dict
            new: New symptoms to merge
            
        Returns:
            Merged symptom dict
        """
        merged = existing.copy()
        
        for symptom in new:
            name = self.sanitize_symptom_name(symptom.name)
            
            if name in merged:
                # Update existing symptom with new information
                existing_symptom = merged[name]
                
                # Update severity if new value provided
                if symptom.severity is not None:
                    existing_symptom.severity = symptom.severity
                
                # Update duration if new value provided
                if symptom.duration is not None:
                    existing_symptom.duration = symptom.duration
                
                # Append to description
                if symptom.description and symptom.description not in existing_symptom.description:
                    existing_symptom.description += f" | {symptom.description}"
                
                # Update present flag
                existing_symptom.present = symptom.present
            else:
                # Add new symptom
                symptom.name = name
                merged[name] = symptom
        
        return merged
    
    def extract_clarification_needs(
        self,
        symptoms: Dict[str, SymptomInfo]
    ) -> List[Dict[str, str]]:
        """
        Identify symptoms that need clarification.
        
        Args:
            symptoms: Current symptom dict
            
        Returns:
            List of clarification needs
        """
        needs_clarification = []
        
        for name, info in symptoms.items():
            if info.severity is None or info.duration is None:
                missing = []
                if info.severity is None:
                    missing.append("severity")
                if info.duration is None:
                    missing.append("duration")
                
                needs_clarification.append({
                    "symptom": name,
                    "missing": missing,
                    "question": f"Can you tell me more about your {name}?"
                })
        
        return needs_clarification


# Global parser instance
response_parser = ResponseParser()
