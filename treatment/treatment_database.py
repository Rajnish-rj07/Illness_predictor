"""
Treatment Database for Illness Prediction System.

This module provides illness-to-treatment mappings including:
- Over-the-counter medication suggestions
- Non-medication treatment options
- Safety disclaimers
- Professional consultation recommendations
- Severity-based filtering rules

Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
"""

from typing import Dict, List
from src.models.data_models import Severity


# Standard disclaimers for medication suggestions
MEDICATION_DISCLAIMER = (
    "IMPORTANT: These are general over-the-counter medication suggestions for informational purposes only. "
    "This is NOT medical advice. Always read medication labels carefully, follow dosage instructions, "
    "and check for potential allergies or drug interactions. Consult a healthcare professional before "
    "taking any medication, especially if you have existing health conditions, are pregnant, or are "
    "taking other medications."
)

PROFESSIONAL_CONSULTATION_TEXT = (
    "We strongly recommend consulting a healthcare professional for proper diagnosis and treatment. "
    "This system provides general information only and should not replace professional medical advice."
)

EMERGENCY_CONSULTATION_TEXT = (
    "URGENT: Your symptoms may indicate a serious condition. Please seek immediate medical attention "
    "or call emergency services. Do not delay seeking professional care."
)

CRITICAL_CONSULTATION_TEXT = (
    "CRITICAL: Your symptoms require immediate emergency medical attention. "
    "Call emergency services (911 or your local emergency number) or go to the nearest emergency room immediately. "
    "Do not attempt self-treatment."
)


# Treatment database: illness -> treatment information
# Structure: {
#   "illness_name": {
#       "medications": [...],  # OTC medications (only for Low/Moderate severity)
#       "non_medication": [...],  # Non-medication options (all severities)
#       "base_severity": Severity,  # Base severity level
#   }
# }
TREATMENT_DATABASE: Dict[str, Dict] = {
    # Respiratory Infections
    "common_cold": {
        "medications": [
            "Acetaminophen (Tylenol) or Ibuprofen (Advil) for fever and pain relief",
            "Decongestants like pseudoephedrine (Sudafed) for nasal congestion",
            "Antihistamines like diphenhydramine (Benadryl) for runny nose",
            "Cough suppressants like dextromethorphan for dry cough",
            "Throat lozenges or sprays for sore throat"
        ],
        "non_medication": [
            "Get plenty of rest (7-9 hours of sleep)",
            "Stay well hydrated (drink 8-10 glasses of water daily)",
            "Use a humidifier to ease congestion",
            "Gargle with warm salt water for sore throat",
            "Drink warm liquids like tea with honey",
            "Avoid smoking and secondhand smoke"
        ],
        "base_severity": Severity.LOW
    },
    
    "influenza": {
        "medications": [
            "Acetaminophen (Tylenol) or Ibuprofen (Advil) for fever and body aches",
            "Decongestants for nasal congestion",
            "Cough suppressants for persistent cough"
        ],
        "non_medication": [
            "Get plenty of rest and sleep",
            "Stay well hydrated with water, broth, and electrolyte drinks",
            "Isolate yourself to prevent spreading the virus",
            "Use a humidifier to ease breathing",
            "Eat nutritious foods when appetite returns",
            "Monitor temperature regularly"
        ],
        "base_severity": Severity.MODERATE
    },
    
    "bronchitis": {
        "medications": [
            "Acetaminophen (Tylenol) or Ibuprofen (Advil) for pain and fever",
            "Cough suppressants for nighttime relief",
            "Expectorants like guaifenesin (Mucinex) to loosen mucus"
        ],
        "non_medication": [
            "Get plenty of rest",
            "Drink lots of fluids to thin mucus",
            "Use a humidifier or breathe steam",
            "Avoid lung irritants (smoke, dust, fumes)",
            "Practice deep breathing exercises",
            "Elevate your head while sleeping"
        ],
        "base_severity": Severity.MODERATE
    },
    
    "pneumonia": {
        "medications": [],  # Requires prescription antibiotics
        "non_medication": [
            "Get plenty of rest",
            "Stay well hydrated",
            "Use a humidifier",
            "Practice deep breathing exercises"
        ],
        "base_severity": Severity.HIGH
    },
    
    # Gastrointestinal Issues
    "gastroenteritis": {
        "medications": [
            "Oral rehydration solutions (Pedialyte, Gatorade)",
            "Anti-diarrheal medication like loperamide (Imodium) if no fever",
            "Bismuth subsalicylate (Pepto-Bismol) for nausea and diarrhea"
        ],
        "non_medication": [
            "Rest and avoid strenuous activity",
            "Drink clear fluids frequently (water, broth, clear soda)",
            "Follow the BRAT diet (Bananas, Rice, Applesauce, Toast)",
            "Avoid dairy, caffeine, alcohol, and fatty foods",
            "Gradually reintroduce normal foods",
            "Practice good hand hygiene to prevent spread"
        ],
        "base_severity": Severity.MODERATE
    },
    
    "food_poisoning": {
        "medications": [
            "Oral rehydration solutions to replace lost fluids",
            "Anti-diarrheal medication (only if no fever or bloody stool)"
        ],
        "non_medication": [
            "Rest and let your body recover",
            "Drink clear fluids in small, frequent sips",
            "Avoid solid foods until vomiting stops",
            "Gradually reintroduce bland foods (BRAT diet)",
            "Avoid dairy, caffeine, alcohol, and spicy foods",
            "Monitor for signs of dehydration"
        ],
        "base_severity": Severity.MODERATE
    },
    
    "acid_reflux": {
        "medications": [
            "Antacids like Tums or Rolaids for quick relief",
            "H2 blockers like famotidine (Pepcid) for longer relief",
            "Proton pump inhibitors like omeprazole (Prilosec) for frequent symptoms"
        ],
        "non_medication": [
            "Eat smaller, more frequent meals",
            "Avoid trigger foods (spicy, fatty, acidic foods)",
            "Don't lie down for 2-3 hours after eating",
            "Elevate the head of your bed 6-8 inches",
            "Maintain a healthy weight",
            "Avoid tight-fitting clothing around the abdomen",
            "Quit smoking and limit alcohol"
        ],
        "base_severity": Severity.LOW
    },
    
    # Headaches and Pain
    "tension_headache": {
        "medications": [
            "Acetaminophen (Tylenol) for pain relief",
            "Ibuprofen (Advil) or Naproxen (Aleve) for pain and inflammation",
            "Aspirin for pain relief (not for children)"
        ],
        "non_medication": [
            "Rest in a quiet, dark room",
            "Apply a cold or warm compress to your head or neck",
            "Practice relaxation techniques (deep breathing, meditation)",
            "Massage your neck, shoulders, and scalp",
            "Maintain good posture",
            "Stay hydrated",
            "Get regular sleep on a consistent schedule",
            "Manage stress through exercise or therapy"
        ],
        "base_severity": Severity.LOW
    },
    
    "migraine": {
        "medications": [
            "Acetaminophen (Tylenol) or Ibuprofen (Advil) for mild migraines",
            "Aspirin for pain relief",
            "Caffeine (in combination with pain relievers) may help"
        ],
        "non_medication": [
            "Rest in a quiet, dark room",
            "Apply a cold compress to your forehead",
            "Stay hydrated",
            "Avoid known triggers (certain foods, stress, lack of sleep)",
            "Practice relaxation techniques",
            "Maintain a regular sleep schedule",
            "Keep a headache diary to identify triggers"
        ],
        "base_severity": Severity.MODERATE
    },
    
    # Allergies
    "allergic_rhinitis": {
        "medications": [
            "Antihistamines like cetirizine (Zyrtec) or loratadine (Claritin)",
            "Nasal corticosteroid sprays like fluticasone (Flonase)",
            "Decongestants like pseudoephedrine (Sudafed)",
            "Eye drops for itchy, watery eyes"
        ],
        "non_medication": [
            "Avoid known allergens when possible",
            "Keep windows closed during high pollen seasons",
            "Use air conditioning with HEPA filters",
            "Shower and change clothes after being outdoors",
            "Use allergen-proof bedding covers",
            "Wash bedding in hot water weekly",
            "Keep indoor humidity low (30-50%)"
        ],
        "base_severity": Severity.LOW
    },
    
    # Skin Conditions
    "contact_dermatitis": {
        "medications": [
            "Hydrocortisone cream (1%) for itching and inflammation",
            "Antihistamines like diphenhydramine (Benadryl) for itching",
            "Calamine lotion for soothing relief"
        ],
        "non_medication": [
            "Identify and avoid the irritant or allergen",
            "Wash the affected area with mild soap and water",
            "Apply cool, wet compresses to reduce itching",
            "Moisturize with fragrance-free lotion",
            "Avoid scratching to prevent infection",
            "Wear loose, breathable clothing"
        ],
        "base_severity": Severity.LOW
    },
    
    # Urinary Issues
    "urinary_tract_infection": {
        "medications": [
            "Phenazopyridine (AZO) for pain relief (not a cure)",
            "Pain relievers like ibuprofen for discomfort"
        ],
        "non_medication": [
            "Drink plenty of water to flush bacteria",
            "Urinate frequently, don't hold it",
            "Avoid caffeine, alcohol, and spicy foods",
            "Apply a heating pad to your lower abdomen",
            "Practice good hygiene",
            "Drink cranberry juice (may help prevent recurrence)"
        ],
        "base_severity": Severity.MODERATE
    },
    
    # Musculoskeletal
    "muscle_strain": {
        "medications": [
            "Ibuprofen (Advil) or Naproxen (Aleve) for pain and inflammation",
            "Acetaminophen (Tylenol) for pain relief",
            "Topical pain relievers like menthol or capsaicin cream"
        ],
        "non_medication": [
            "Rest the injured muscle",
            "Apply ice for first 48 hours (20 minutes every 2-3 hours)",
            "After 48 hours, apply heat to relax the muscle",
            "Compress the area with an elastic bandage",
            "Elevate the injured area if possible",
            "Gentle stretching after initial pain subsides",
            "Gradually return to normal activity"
        ],
        "base_severity": Severity.LOW
    },
    
    "back_pain": {
        "medications": [
            "Ibuprofen (Advil) or Naproxen (Aleve) for pain and inflammation",
            "Acetaminophen (Tylenol) for pain relief",
            "Topical pain relievers"
        ],
        "non_medication": [
            "Stay active with gentle movement",
            "Apply ice for acute pain (first 48 hours)",
            "Apply heat for chronic pain or muscle tension",
            "Practice good posture",
            "Sleep on a firm mattress",
            "Do gentle stretching and strengthening exercises",
            "Maintain a healthy weight",
            "Use proper lifting techniques"
        ],
        "base_severity": Severity.LOW
    },
    
    # Serious Conditions (High/Critical Severity)
    "appendicitis": {
        "medications": [],
        "non_medication": [
            "Do not eat or drink anything",
            "Do not take laxatives or pain medication",
            "Do not apply heat to the abdomen"
        ],
        "base_severity": Severity.CRITICAL
    },
    
    "meningitis": {
        "medications": [],
        "non_medication": [
            "Isolate to prevent spread",
            "Rest in a quiet, dark room"
        ],
        "base_severity": Severity.CRITICAL
    },
    
    "heart_attack": {
        "medications": [],
        "non_medication": [
            "Sit down and rest immediately",
            "Loosen any tight clothing",
            "If prescribed, take nitroglycerin as directed",
            "Chew aspirin if not allergic (only if advised by emergency services)"
        ],
        "base_severity": Severity.CRITICAL
    },
    
    "stroke": {
        "medications": [],
        "non_medication": [
            "Sit or lie down immediately",
            "Do not eat or drink anything",
            "Note the time symptoms started"
        ],
        "base_severity": Severity.CRITICAL
    },
    
    "anaphylaxis": {
        "medications": [],
        "non_medication": [
            "Use epinephrine auto-injector (EpiPen) if available",
            "Lie down with legs elevated",
            "Loosen tight clothing"
        ],
        "base_severity": Severity.CRITICAL
    },
    
    # Additional Common Conditions
    "sinusitis": {
        "medications": [
            "Decongestants like pseudoephedrine (Sudafed)",
            "Nasal corticosteroid sprays like fluticasone (Flonase)",
            "Pain relievers like acetaminophen or ibuprofen",
            "Saline nasal spray or rinse"
        ],
        "non_medication": [
            "Use a humidifier or breathe steam",
            "Apply warm compresses to your face",
            "Stay well hydrated",
            "Sleep with your head elevated",
            "Avoid allergens and irritants",
            "Practice nasal irrigation with saline solution"
        ],
        "base_severity": Severity.LOW
    },
    
    "conjunctivitis": {
        "medications": [
            "Artificial tears for comfort",
            "Antihistamine eye drops for allergic conjunctivitis"
        ],
        "non_medication": [
            "Apply warm or cool compresses to eyes",
            "Avoid touching or rubbing your eyes",
            "Wash hands frequently",
            "Change pillowcases and towels daily",
            "Avoid wearing contact lenses until cleared",
            "Clean eye discharge with a clean, damp cloth"
        ],
        "base_severity": Severity.LOW
    },
    
    "insomnia": {
        "medications": [
            "Melatonin supplements (short-term use)",
            "Antihistamines like diphenhydramine (Benadryl) occasionally"
        ],
        "non_medication": [
            "Maintain a consistent sleep schedule",
            "Create a relaxing bedtime routine",
            "Keep your bedroom cool, dark, and quiet",
            "Avoid screens 1-2 hours before bed",
            "Limit caffeine and alcohol",
            "Exercise regularly, but not close to bedtime",
            "Avoid large meals before bed",
            "Practice relaxation techniques (meditation, deep breathing)"
        ],
        "base_severity": Severity.LOW
    },
    
    "anxiety": {
        "medications": [
            "Herbal supplements like chamomile tea or valerian root (consult first)"
        ],
        "non_medication": [
            "Practice deep breathing exercises",
            "Try progressive muscle relaxation",
            "Exercise regularly (30 minutes most days)",
            "Maintain a regular sleep schedule",
            "Limit caffeine and alcohol",
            "Practice mindfulness or meditation",
            "Talk to someone you trust",
            "Consider professional counseling or therapy",
            "Keep a journal to identify triggers"
        ],
        "base_severity": Severity.MODERATE
    },
    
    "depression": {
        "medications": [],
        "non_medication": [
            "Seek professional help from a therapist or counselor",
            "Exercise regularly",
            "Maintain a regular sleep schedule",
            "Eat a balanced, nutritious diet",
            "Stay connected with friends and family",
            "Set small, achievable goals",
            "Avoid alcohol and drugs",
            "Practice self-care activities",
            "Join a support group"
        ],
        "base_severity": Severity.HIGH
    },
    
    "asthma_attack": {
        "medications": [],
        "non_medication": [
            "Use your rescue inhaler as prescribed",
            "Sit upright and stay calm",
            "Take slow, steady breaths",
            "Remove yourself from triggers if possible"
        ],
        "base_severity": Severity.HIGH
    },
}


def get_treatment_info(illness: str, severity: Severity) -> Dict[str, any]:
    """
    Get treatment information for a specific illness and severity level.
    
    Args:
        illness: The predicted illness name
        severity: The severity level of the prediction
        
    Returns:
        Dictionary containing:
            - medications: List of OTC medication suggestions (empty for High/Critical)
            - non_medication: List of non-medication treatment options
            - disclaimer: Safety disclaimer text
            - seek_professional: Whether to seek professional care
            
    Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
    """
    # Get treatment data from database
    treatment_data = TREATMENT_DATABASE.get(illness.lower().replace(" ", "_"), None)
    
    # Default treatment info if illness not in database
    if treatment_data is None:
        return {
            "medications": [],
            "non_medication": [
                "Get adequate rest",
                "Stay well hydrated",
                "Monitor your symptoms",
                "Maintain a healthy diet"
            ],
            "disclaimer": MEDICATION_DISCLAIMER,
            "seek_professional": True
        }
    
    # Severity-based filtering (Requirement 18.4)
    # High and Critical severity: NO medication suggestions
    if severity in [Severity.HIGH, Severity.CRITICAL]:
        medications = []
        if severity == Severity.CRITICAL:
            disclaimer = CRITICAL_CONSULTATION_TEXT
        else:
            disclaimer = EMERGENCY_CONSULTATION_TEXT
        seek_professional = True
    else:
        # Low and Moderate severity: Include OTC medications with disclaimers
        medications = treatment_data.get("medications", [])
        disclaimer = MEDICATION_DISCLAIMER + "\n\n" + PROFESSIONAL_CONSULTATION_TEXT
        seek_professional = True
    
    # Non-medication options included for all severities (Requirement 18.5)
    non_medication = treatment_data.get("non_medication", [])
    
    return {
        "medications": medications,
        "non_medication": non_medication,
        "disclaimer": disclaimer,
        "seek_professional": seek_professional
    }


def get_base_severity(illness: str) -> Severity:
    """
    Get the base severity level for an illness from the database.
    
    Args:
        illness: The illness name
        
    Returns:
        Base severity level (defaults to MODERATE if not found)
    """
    treatment_data = TREATMENT_DATABASE.get(illness.lower().replace(" ", "_"), None)
    if treatment_data is None:
        return Severity.MODERATE
    return treatment_data.get("base_severity", Severity.MODERATE)


def get_all_illnesses() -> List[str]:
    """
    Get a list of all illnesses in the treatment database.
    
    Returns:
        List of illness names
    """
    return list(TREATMENT_DATABASE.keys())


def illness_exists(illness: str) -> bool:
    """
    Check if an illness exists in the treatment database.
    
    Args:
        illness: The illness name
        
    Returns:
        True if illness exists in database, False otherwise
    """
    return illness.lower().replace(" ", "_") in TREATMENT_DATABASE
