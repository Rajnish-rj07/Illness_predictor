"""
Treatment module for the Illness Prediction System.

This module provides treatment suggestions including medications,
non-medication options, and safety disclaimers.
"""

from src.treatment.treatment_database import (
    get_treatment_info,
    get_base_severity,
    get_all_illnesses,
    illness_exists,
    MEDICATION_DISCLAIMER,
    PROFESSIONAL_CONSULTATION_TEXT,
    EMERGENCY_CONSULTATION_TEXT,
    CRITICAL_CONSULTATION_TEXT,
    TREATMENT_DATABASE
)

__all__ = [
    'get_treatment_info',
    'get_base_severity',
    'get_all_illnesses',
    'illness_exists',
    'MEDICATION_DISCLAIMER',
    'PROFESSIONAL_CONSULTATION_TEXT',
    'EMERGENCY_CONSULTATION_TEXT',
    'CRITICAL_CONSULTATION_TEXT',
    'TREATMENT_DATABASE'
]
