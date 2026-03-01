"""
Treatment Service for Illness Prediction System.

This service provides treatment suggestions based on illness predictions and severity levels.
It integrates with the treatment database to provide:
- Over-the-counter medication suggestions (for Low/Moderate severity)
- Non-medication treatment options (for all severities)
- Safety disclaimers and professional consultation recommendations
- Severity-based filtering (no medications for High/Critical severity)

Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
"""

import logging
from typing import Dict, List, Optional

from src.models.data_models import Severity, TreatmentInfo, Prediction
from src.treatment.treatment_database import (
    get_treatment_info,
    get_base_severity,
    illness_exists,
    MEDICATION_DISCLAIMER,
    PROFESSIONAL_CONSULTATION_TEXT,
    EMERGENCY_CONSULTATION_TEXT,
    CRITICAL_CONSULTATION_TEXT,
)

logger = logging.getLogger(__name__)


class TreatmentService:
    """
    Service for providing treatment suggestions based on illness predictions.
    
    Features:
    - Retrieves treatment information from the treatment database
    - Filters medication suggestions based on severity level
    - Provides non-medication treatment options for all severities
    - Includes appropriate disclaimers and professional consultation recommendations
    - Handles High/Critical severity with emergency recommendations
    
    Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
    """
    
    def __init__(self):
        """Initialize the Treatment Service."""
        logger.info("TreatmentService initialized")
    
    def get_treatment_suggestions(
        self,
        illness: str,
        severity: Severity,
    ) -> TreatmentInfo:
        """
        Get treatment suggestions for a specific illness and severity level.
        
        Treatment logic:
        - For LOW/MODERATE severity: Include OTC medications with disclaimers
        - For HIGH/CRITICAL severity: No medication suggestions, recommend immediate care
        - Always include non-medication treatment options
        - Always include appropriate disclaimers
        
        Args:
            illness: Name of the predicted illness
            severity: Severity level of the prediction
        
        Returns:
            TreatmentInfo object containing:
                - medications: List of OTC medication suggestions (empty for High/Critical)
                - non_medication: List of non-medication treatment options
                - disclaimer: Safety disclaimer text
                - seek_professional: Whether to seek professional care (always True)
        
        Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
        """
        logger.info(f"Getting treatment suggestions for illness='{illness}', severity={severity.value}")
        
        # Get treatment information from database
        treatment_data = get_treatment_info(illness, severity)
        
        # Create TreatmentInfo object
        treatment_info = TreatmentInfo(
            medications=treatment_data["medications"],
            non_medication=treatment_data["non_medication"],
            disclaimer=treatment_data["disclaimer"],
            seek_professional=treatment_data["seek_professional"],
        )
        
        # Log the treatment info
        logger.info(
            f"Treatment suggestions for {illness} ({severity.value}): "
            f"{len(treatment_info.medications)} medications, "
            f"{len(treatment_info.non_medication)} non-medication options"
        )
        
        return treatment_info
    
    def get_treatment_for_prediction(
        self,
        prediction: Prediction,
    ) -> TreatmentInfo:
        """
        Get treatment suggestions for a Prediction object.
        
        This is a convenience method that extracts illness and severity
        from a Prediction object and calls get_treatment_suggestions.
        
        Args:
            prediction: Prediction object containing illness and severity
        
        Returns:
            TreatmentInfo object with treatment suggestions
        
        Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
        """
        return self.get_treatment_suggestions(
            illness=prediction.illness,
            severity=prediction.severity,
        )
    
    def get_treatment_for_multiple_predictions(
        self,
        predictions: List[Prediction],
    ) -> List[TreatmentInfo]:
        """
        Get treatment suggestions for multiple predictions.
        
        Args:
            predictions: List of Prediction objects
        
        Returns:
            List of TreatmentInfo objects corresponding to each prediction
        
        Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
        """
        logger.info(f"Getting treatment suggestions for {len(predictions)} predictions")
        
        treatment_infos = []
        for prediction in predictions:
            treatment_info = self.get_treatment_for_prediction(prediction)
            treatment_infos.append(treatment_info)
        
        return treatment_infos
    
    def check_illness_exists(self, illness: str) -> bool:
        """
        Check if an illness exists in the treatment database.
        
        Args:
            illness: Name of the illness to check
        
        Returns:
            True if illness exists in database, False otherwise
        """
        return illness_exists(illness)
    
    def get_base_severity_for_illness(self, illness: str) -> Severity:
        """
        Get the base severity level for an illness from the database.
        
        This can be used by other services (e.g., PredictionService) to
        determine the initial severity level before applying symptom-based
        adjustments.
        
        Args:
            illness: Name of the illness
        
        Returns:
            Base severity level (defaults to MODERATE if not found)
        """
        return get_base_severity(illness)
    
    def format_treatment_info(
        self,
        treatment_info: TreatmentInfo,
        include_disclaimer: bool = True,
    ) -> str:
        """
        Format treatment information for user presentation.
        
        Args:
            treatment_info: TreatmentInfo object to format
            include_disclaimer: Whether to include the disclaimer (default: True)
        
        Returns:
            Formatted string for user presentation
        """
        lines = []
        
        # Add medications if present
        if treatment_info.medications:
            lines.append("💊 Suggested Over-the-Counter Medications:")
            for med in treatment_info.medications:
                lines.append(f"  • {med}")
            lines.append("")
        
        # Add non-medication options (always present)
        if treatment_info.non_medication:
            lines.append("🏥 Self-Care Recommendations:")
            for rec in treatment_info.non_medication:
                lines.append(f"  • {rec}")
            lines.append("")
        
        # Add disclaimer if requested
        if include_disclaimer and treatment_info.disclaimer:
            lines.append("⚠️  IMPORTANT DISCLAIMER:")
            lines.append(treatment_info.disclaimer)
            lines.append("")
        
        # Add professional consultation recommendation
        if treatment_info.seek_professional:
            lines.append("👨‍⚕️ Please consult a healthcare professional for proper diagnosis and treatment.")
        
        return "\n".join(lines)
    
    def has_emergency_recommendations(self, treatment_info: TreatmentInfo) -> bool:
        """
        Check if treatment info contains emergency recommendations.
        
        This is useful for determining if the user should be directed to
        emergency services or immediate medical attention.
        
        Args:
            treatment_info: TreatmentInfo object to check
        
        Returns:
            True if treatment contains emergency recommendations, False otherwise
        """
        # Check if disclaimer contains emergency keywords
        emergency_keywords = [
            "URGENT",
            "CRITICAL",
            "emergency",
            "immediate medical attention",
            "call emergency services",
            "911",
        ]
        
        disclaimer_lower = treatment_info.disclaimer.lower()
        return any(keyword.lower() in disclaimer_lower for keyword in emergency_keywords)
    
    def get_severity_appropriate_message(self, severity: Severity) -> str:
        """
        Get a severity-appropriate message for the user.
        
        Args:
            severity: Severity level
        
        Returns:
            User-friendly message appropriate for the severity level
        """
        if severity == Severity.CRITICAL:
            return (
                "🚨 CRITICAL: Your symptoms require immediate emergency medical attention. "
                "Call emergency services (911 or your local emergency number) or go to the "
                "nearest emergency room immediately. Do not delay seeking professional care."
            )
        elif severity == Severity.HIGH:
            return (
                "⚠️  HIGH SEVERITY: Your symptoms may indicate a serious condition. "
                "Please seek medical attention as soon as possible. If symptoms worsen, "
                "call emergency services."
            )
        elif severity == Severity.MODERATE:
            return (
                "🟡 MODERATE: Your symptoms should be evaluated by a healthcare professional. "
                "Schedule an appointment with your doctor, especially if symptoms persist or worsen."
            )
        else:  # LOW
            return (
                "🟢 LOW SEVERITY: Your symptoms are generally mild. However, if they persist "
                "or worsen, please consult a healthcare professional."
            )
