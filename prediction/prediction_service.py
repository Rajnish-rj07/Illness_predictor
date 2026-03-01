"""
Prediction Service for coordinating illness predictions and result formatting.

This service handles:
- Coordinating ML model inference
- Severity scoring based on illness and symptoms
- Prediction filtering (confidence threshold, top-3 limit)
- Treatment suggestion lookup
- Result formatting for user presentation

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 12.1, 12.2, 12.3, 12.4, 12.5
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

from src.models.data_models import (
    SymptomVector,
    Prediction,
    Severity,
    TreatmentInfo,
    Explanation,
)
from src.ml.ml_model_service import MLModelService

logger = logging.getLogger(__name__)


class PredictionService:
    """
    Service for generating illness predictions with severity scoring and treatment suggestions.
    
    Features:
    - Coordinates ML model inference using MLModelService
    - Assigns severity levels (Low, Moderate, High, Critical) to predictions
    - Filters predictions by confidence threshold (>= 30%)
    - Limits results to top 3 predictions
    - Provides treatment suggestions based on severity
    - Formats results for user presentation
    
    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 12.1, 12.2, 12.3, 12.4, 12.5
    """
    
    # Illness base severity mapping
    # In production, this would be loaded from a database or configuration file
    ILLNESS_SEVERITY_MAP: Dict[str, Severity] = {
        # Critical illnesses
        'meningitis': Severity.CRITICAL,
        'heart_attack': Severity.CRITICAL,
        'stroke': Severity.CRITICAL,
        'pulmonary_embolism': Severity.CRITICAL,
        'sepsis': Severity.CRITICAL,
        'anaphylaxis': Severity.CRITICAL,
        'appendicitis': Severity.CRITICAL,
        'aortic_aneurysm': Severity.CRITICAL,
        'brain_tumor': Severity.CRITICAL,
        'encephalitis': Severity.CRITICAL,
        
        # High severity illnesses
        'pneumonia': Severity.HIGH,
        'covid_19': Severity.HIGH,
        'tuberculosis': Severity.HIGH,
        'kidney_stones': Severity.HIGH,
        'pancreatitis': Severity.HIGH,
        'deep_vein_thrombosis': Severity.HIGH,
        'pyelonephritis': Severity.HIGH,
        'hepatitis_b': Severity.HIGH,
        'hepatitis_c': Severity.HIGH,
        'cirrhosis': Severity.HIGH,
        'heart_failure': Severity.HIGH,
        'arrhythmia': Severity.HIGH,
        'copd': Severity.HIGH,
        'asthma': Severity.HIGH,
        'diabetes_type_1': Severity.HIGH,
        'diabetes_type_2': Severity.HIGH,
        'leukemia': Severity.HIGH,
        'lymphoma': Severity.HIGH,
        'lung_cancer': Severity.HIGH,
        
        # Moderate severity illnesses
        'influenza': Severity.MODERATE,
        'bronchitis': Severity.MODERATE,
        'sinusitis': Severity.MODERATE,
        'strep_throat': Severity.MODERATE,
        'gastroenteritis': Severity.MODERATE,
        'uti': Severity.MODERATE,
        'gerd': Severity.MODERATE,
        'ibs': Severity.MODERATE,
        'migraine': Severity.MODERATE,
        'hypertension': Severity.MODERATE,
        'hypothyroidism': Severity.MODERATE,
        'hyperthyroidism': Severity.MODERATE,
        'osteoarthritis': Severity.MODERATE,
        'rheumatoid_arthritis': Severity.MODERATE,
        'gout': Severity.MODERATE,
        'eczema': Severity.MODERATE,
        'psoriasis': Severity.MODERATE,
        'anxiety_disorder': Severity.MODERATE,
        'depression': Severity.MODERATE,
        
        # Low severity illnesses
        'common_cold': Severity.LOW,
        'allergic_rhinitis': Severity.LOW,
        'hay_fever': Severity.LOW,
        'tension_headache': Severity.LOW,
        'acne': Severity.LOW,
        'athletes_foot': Severity.LOW,
        'ringworm': Severity.LOW,
        'contact_dermatitis': Severity.LOW,
        'insomnia': Severity.LOW,
    }
    
    # Critical symptoms that escalate severity
    CRITICAL_SYMPTOMS = [
        'chest_pain',
        'shortness_of_breath',
        'confusion',
        'seizures',
        'severe_headache',
        'loss_of_consciousness',
        'difficulty_breathing',
        'severe_abdominal_pain',
        'blood_in_stool',
        'blood_in_urine',
        'severe_bleeding',
        'paralysis',
        'slurred_speech',
        'sudden_vision_loss',
        'severe_allergic_reaction',
    ]
    
    # Treatment database: illness -> TreatmentInfo
    # In production, this would be loaded from a database
    TREATMENT_DATABASE: Dict[str, Dict] = {
        'common_cold': {
            'medications': ['Acetaminophen (Tylenol)', 'Ibuprofen (Advil)', 'Decongestants'],
            'non_medication': ['Rest', 'Stay hydrated', 'Use humidifier', 'Gargle with salt water'],
        },
        'influenza': {
            'medications': ['Acetaminophen (Tylenol)', 'Ibuprofen (Advil)', 'Antiviral medications (if prescribed)'],
            'non_medication': ['Rest', 'Stay hydrated', 'Isolate from others', 'Monitor symptoms'],
        },
        'headache': {
            'medications': ['Acetaminophen (Tylenol)', 'Ibuprofen (Advil)', 'Aspirin'],
            'non_medication': ['Rest in quiet, dark room', 'Apply cold compress', 'Stay hydrated', 'Reduce stress'],
        },
        'migraine': {
            'medications': ['Ibuprofen (Advil)', 'Acetaminophen (Tylenol)', 'Caffeine'],
            'non_medication': ['Rest in dark, quiet room', 'Apply cold compress', 'Avoid triggers', 'Practice relaxation'],
        },
        'gastroenteritis': {
            'medications': ['Oral rehydration solutions', 'Anti-diarrheal medications (if appropriate)'],
            'non_medication': ['Stay hydrated', 'Eat bland foods (BRAT diet)', 'Rest', 'Avoid dairy temporarily'],
        },
        'uti': {
            'medications': ['Antibiotics (prescription required)', 'Pain relievers'],
            'non_medication': ['Drink plenty of water', 'Urinate frequently', 'Avoid irritants', 'Use heating pad'],
        },
        'allergic_rhinitis': {
            'medications': ['Antihistamines', 'Nasal corticosteroid sprays', 'Decongestants'],
            'non_medication': ['Avoid allergens', 'Use air purifier', 'Keep windows closed', 'Shower after outdoor activities'],
        },
        'bronchitis': {
            'medications': ['Cough suppressants', 'Expectorants', 'Pain relievers'],
            'non_medication': ['Rest', 'Stay hydrated', 'Use humidifier', 'Avoid smoke and irritants'],
        },
        'sinusitis': {
            'medications': ['Decongestants', 'Nasal corticosteroid sprays', 'Pain relievers'],
            'non_medication': ['Use saline nasal rinse', 'Apply warm compress', 'Stay hydrated', 'Use humidifier'],
        },
        'strep_throat': {
            'medications': ['Antibiotics (prescription required)', 'Pain relievers'],
            'non_medication': ['Rest', 'Stay hydrated', 'Gargle with salt water', 'Use throat lozenges'],
        },
    }
    
    # Default treatment for illnesses not in database
    DEFAULT_TREATMENT = {
        'medications': [],
        'non_medication': ['Rest', 'Stay hydrated', 'Monitor symptoms', 'Maintain good hygiene'],
    }
    
    def __init__(self, ml_model_service: MLModelService):
        """
        Initialize the Prediction Service.
        
        Args:
            ml_model_service: MLModelService instance for model inference
        """
        self.ml_model_service = ml_model_service
        logger.info("PredictionService initialized")
    
    def predict(
        self,
        symptom_vector: SymptomVector,
        model_version: Optional[str] = None,
        language: str = 'en',
    ) -> List[Prediction]:
        """
        Generate illness predictions from a symptom vector.
        
        This method:
        1. Uses MLModelService to get raw predictions
        2. Assigns severity levels to each prediction
        3. Filters by confidence threshold (>= 30%)
        4. Limits to top 3 predictions
        5. Adds treatment suggestions
        6. Formats results for user presentation
        
        Args:
            symptom_vector: SymptomVector containing user-reported symptoms
            model_version: Model version to use (optional)
            language: Language for result formatting (default: 'en')
        
        Returns:
            List of Prediction objects with severity, treatment suggestions, and explanations
            - Filtered by confidence >= 30%
            - Sorted by confidence descending
            - Limited to top 3 predictions
        
        Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 12.1, 12.2, 12.3, 12.4, 12.5
        """
        logger.info(f"Generating predictions for symptom_vector with {len(symptom_vector.symptoms)} symptoms")
        
        # Step 1: Get raw predictions from ML model
        # MLModelService already handles confidence filtering (>= 30%) and top-k limiting
        raw_predictions = self.ml_model_service.predict(
            symptom_vector=symptom_vector,
            model_version=model_version,
            top_k=3,  # Requirement 3.2: Top 3 predictions
            confidence_threshold=0.30,  # Requirement 3.3: 30% threshold
        )
        
        # If no predictions meet the threshold
        if not raw_predictions:
            logger.warning("No predictions met the confidence threshold")
            return []
        
        # Step 2: Build full Prediction objects with severity and treatment
        predictions = []
        for illness, confidence_score in raw_predictions:
            # Calculate severity (Requirement 12.1)
            severity = self.calculate_severity(illness, symptom_vector)
            
            # Get treatment suggestions (Requirements 18.1-18.5)
            treatment = self.get_treatment_suggestions(illness, severity)
            
            # Create Prediction object
            prediction = Prediction(
                illness=illness,
                confidence_score=confidence_score,
                severity=severity,
                explanation=None,  # Will be added by ExplainabilityService later
                treatment_suggestions=treatment,
            )
            
            predictions.append(prediction)
        
        # Step 3: Apply severity-based ranking if needed (Requirement 12.3)
        # When confidence scores are similar, rank by severity
        predictions = self._rank_by_severity_if_needed(predictions)
        
        # Step 4: Check for multiple high/critical severity predictions (Requirement 12.5)
        high_critical_count = sum(
            1 for p in predictions
            if p.severity in [Severity.HIGH, Severity.CRITICAL]
        )
        
        if high_critical_count >= 2:
            logger.warning(f"Multiple high/critical predictions detected: {high_critical_count}")
            # This information can be used by the caller to recommend emergency services
        
        logger.info(f"Generated {len(predictions)} predictions")
        return predictions
    
    def calculate_severity(
        self,
        illness: str,
        symptom_vector: SymptomVector,
    ) -> Severity:
        """
        Calculate severity level for an illness based on base severity and symptoms.
        
        Severity calculation logic:
        1. Start with base severity from ILLNESS_SEVERITY_MAP
        2. Check for critical symptoms - if present, escalate to CRITICAL
        3. If base severity is HIGH and many symptoms (>5), keep HIGH
        4. Otherwise, use base severity
        
        Args:
            illness: Name of the predicted illness
            symptom_vector: SymptomVector containing user-reported symptoms
        
        Returns:
            Severity level (LOW, MODERATE, HIGH, or CRITICAL)
        
        Validates: Requirements 12.1, 12.2, 12.3
        """
        # Get base severity from mapping (default to MODERATE if not found)
        base_severity = self.ILLNESS_SEVERITY_MAP.get(illness, Severity.MODERATE)
        
        # Check for critical symptoms
        symptom_names = [
            name.lower().replace(' ', '_')
            for name in symptom_vector.symptoms.keys()
        ]
        
        critical_symptoms_present = [
            symptom for symptom in self.CRITICAL_SYMPTOMS
            if symptom in symptom_names
        ]
        
        # If critical symptoms present, escalate to CRITICAL (Requirement 12.2)
        if critical_symptoms_present:
            logger.info(
                f"Critical symptoms detected for {illness}: {critical_symptoms_present}. "
                f"Escalating severity to CRITICAL"
            )
            return Severity.CRITICAL
        
        # If base severity is HIGH and many symptoms, keep HIGH
        if base_severity == Severity.HIGH and len(symptom_vector.symptoms) > 5:
            logger.info(f"High severity illness {illness} with {len(symptom_vector.symptoms)} symptoms")
            return Severity.HIGH
        
        # Otherwise, use base severity
        return base_severity
    
    def get_treatment_suggestions(
        self,
        illness: str,
        severity: Severity,
    ) -> TreatmentInfo:
        """
        Get treatment suggestions for an illness based on severity.
        
        Treatment suggestion logic:
        - For LOW/MODERATE severity: Include OTC medications and non-medication options
        - For HIGH/CRITICAL severity: No medication suggestions, recommend immediate care
        - Always include appropriate disclaimers
        
        Args:
            illness: Name of the predicted illness
            severity: Severity level of the prediction
        
        Returns:
            TreatmentInfo with medications, non-medication options, and disclaimers
        
        Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
        """
        # For HIGH or CRITICAL severity, do not provide medication suggestions (Requirement 18.4)
        if severity in [Severity.HIGH, Severity.CRITICAL]:
            return TreatmentInfo(
                medications=[],
                non_medication=[
                    'Seek immediate medical attention',
                    'Call emergency services if symptoms worsen',
                    'Do not delay professional care',
                ],
                disclaimer=(
                    "⚠️ IMPORTANT: Your symptoms may indicate a serious condition. "
                    "Please seek immediate medical attention or call emergency services. "
                    "Do not attempt self-treatment."
                ),
                seek_professional=True,
            )
        
        # For LOW/MODERATE severity, provide treatment suggestions
        treatment_data = self.TREATMENT_DATABASE.get(illness, self.DEFAULT_TREATMENT)
        
        # Build disclaimer (Requirements 18.2, 18.3)
        disclaimer = (
            "⚠️ DISCLAIMER: These suggestions are for informational purposes only and "
            "do not constitute medical advice. Please consult a healthcare professional "
            "before taking any medication or starting any treatment. If symptoms persist "
            "or worsen, seek medical attention immediately."
        )
        
        return TreatmentInfo(
            medications=treatment_data.get('medications', []),
            non_medication=treatment_data.get('non_medication', []),
            disclaimer=disclaimer,
            seek_professional=True,  # Always recommend professional consultation
        )
    
    def _rank_by_severity_if_needed(self, predictions: List[Prediction]) -> List[Prediction]:
        """
        Re-rank predictions by severity when confidence scores are similar.
        
        If the top predictions have confidence scores within 10% of each other,
        prioritize by severity (CRITICAL > HIGH > MODERATE > LOW).
        
        Args:
            predictions: List of predictions sorted by confidence
        
        Returns:
            Re-ranked list of predictions
        
        Validates: Requirement 12.3
        """
        if len(predictions) <= 1:
            return predictions
        
        # Check if top predictions have similar confidence scores (within 10%)
        top_confidence = predictions[0].confidence_score
        similar_predictions = []
        other_predictions = []
        
        for pred in predictions:
            if abs(pred.confidence_score - top_confidence) <= 0.10:
                similar_predictions.append(pred)
            else:
                other_predictions.append(pred)
        
        # If we have multiple predictions with similar confidence, rank by severity
        if len(similar_predictions) > 1:
            severity_order = {
                Severity.CRITICAL: 0,
                Severity.HIGH: 1,
                Severity.MODERATE: 2,
                Severity.LOW: 3,
            }
            
            similar_predictions.sort(
                key=lambda p: (severity_order[p.severity], -p.confidence_score)
            )
            
            logger.info(
                f"Re-ranked {len(similar_predictions)} predictions by severity "
                f"(confidence scores within 10%)"
            )
        
        return similar_predictions + other_predictions
    
    def format_results(
        self,
        predictions: List[Prediction],
        language: str = 'en',
    ) -> str:
        """
        Format prediction results for user presentation.
        
        Args:
            predictions: List of Prediction objects
            language: Language for formatting (default: 'en')
        
        Returns:
            Formatted string for user presentation
        
        Validates: Requirement 3.5
        """
        if not predictions:
            return (
                "We were unable to generate confident predictions based on your symptoms. "
                "This could mean:\n"
                "- More information is needed\n"
                "- Your symptoms don't match common illness patterns\n"
                "- You should consult a healthcare professional for proper evaluation\n\n"
                "Please seek medical attention if your symptoms are concerning or persistent."
            )
        
        result_lines = ["Based on your symptoms, here are the most likely conditions:\n"]
        
        for i, prediction in enumerate(predictions, 1):
            # Format confidence as percentage
            confidence_pct = prediction.confidence_score * 100
            
            # Add severity indicator
            severity_emoji = {
                Severity.LOW: "🟢",
                Severity.MODERATE: "🟡",
                Severity.HIGH: "🟠",
                Severity.CRITICAL: "🔴",
            }
            
            result_lines.append(
                f"\n{i}. {prediction.illness.replace('_', ' ').title()} "
                f"{severity_emoji[prediction.severity]} ({prediction.severity.value.upper()})"
            )
            result_lines.append(f"   Confidence: {confidence_pct:.1f}%")
            
            # Add treatment suggestions if available
            if prediction.treatment_suggestions:
                treatment = prediction.treatment_suggestions
                
                if treatment.medications:
                    result_lines.append(f"\n   Suggested OTC Medications:")
                    for med in treatment.medications:
                        result_lines.append(f"   - {med}")
                
                if treatment.non_medication:
                    result_lines.append(f"\n   Self-Care Recommendations:")
                    for rec in treatment.non_medication:
                        result_lines.append(f"   - {rec}")
        
        # Add general disclaimer
        result_lines.append(
            "\n\n⚠️ IMPORTANT: These predictions are for informational purposes only. "
            "Please consult a healthcare professional for proper diagnosis and treatment."
        )
        
        # Add emergency warning if any critical predictions
        if any(p.severity == Severity.CRITICAL for p in predictions):
            result_lines.append(
                "\n\n🚨 URGENT: One or more predictions indicate a potentially serious condition. "
                "Please seek immediate medical attention or call emergency services."
            )
        
        return "\n".join(result_lines)
