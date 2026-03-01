# Treatment Database Implementation

## Overview

The treatment database provides illness-to-treatment mappings for the Illness Prediction System. It includes over-the-counter medication suggestions, non-medication treatment options, safety disclaimers, and professional consultation recommendations with severity-based filtering rules.

**Validates**: Requirements 18.1, 18.2, 18.3, 18.4, 18.5

## Location

- **Module**: `src/treatment/treatment_database.py`
- **Tests**: `tests/test_treatment_database.py`

## Key Features

### 1. Comprehensive Treatment Mappings

The database includes treatment information for 25+ common illnesses across multiple categories:

- **Respiratory Infections**: Common cold, influenza, bronchitis, pneumonia, sinusitis
- **Gastrointestinal Issues**: Gastroenteritis, food poisoning, acid reflux
- **Headaches and Pain**: Tension headache, migraine, muscle strain, back pain
- **Allergies**: Allergic rhinitis, contact dermatitis
- **Urinary Issues**: Urinary tract infection
- **Serious Conditions**: Appendicitis, meningitis, heart attack, stroke, anaphylaxis
- **Other Conditions**: Conjunctivitis, insomnia, anxiety, depression, asthma attack

### 2. Severity-Based Filtering (Requirement 18.4)

The system implements strict severity-based filtering rules:

- **Low/Moderate Severity**: Includes OTC medication suggestions with comprehensive disclaimers
- **High/Critical Severity**: NO medication suggestions, only professional consultation recommendations

This ensures patient safety by preventing self-medication for serious conditions.

### 3. Safety Disclaimers (Requirements 18.2, 18.3)

Four types of disclaimers are provided:

1. **MEDICATION_DISCLAIMER**: Standard disclaimer for OTC medications
   - States information is not medical advice
   - Warns about allergies and drug interactions
   - Recommends consulting healthcare professionals

2. **PROFESSIONAL_CONSULTATION_TEXT**: General recommendation for all predictions
   - Emphasizes need for professional diagnosis
   - Clarifies system limitations

3. **EMERGENCY_CONSULTATION_TEXT**: For high severity conditions
   - Urgent language
   - Recommends immediate medical attention

4. **CRITICAL_CONSULTATION_TEXT**: For critical conditions
   - Emergency language
   - Directs to call emergency services immediately

### 4. Non-Medication Options (Requirement 18.5)

All illnesses include non-medication treatment options such as:
- Rest and sleep recommendations
- Hydration guidelines
- Dietary suggestions
- Home remedies (compresses, humidifiers, etc.)
- Lifestyle modifications
- Self-care practices

These are included for ALL severity levels, including critical conditions.

## Data Structure

Each illness entry in the database contains:

```python
{
    "illness_name": {
        "medications": [
            "OTC medication 1 with dosage info",
            "OTC medication 2 with dosage info",
            ...
        ],
        "non_medication": [
            "Non-medication option 1",
            "Non-medication option 2",
            ...
        ],
        "base_severity": Severity.LOW | MODERATE | HIGH | CRITICAL
    }
}
```

## API Functions

### `get_treatment_info(illness: str, severity: Severity) -> Dict`

Main function to retrieve treatment information for an illness at a specific severity level.

**Parameters**:
- `illness`: The predicted illness name
- `severity`: The severity level (LOW, MODERATE, HIGH, CRITICAL)

**Returns**: Dictionary with:
- `medications`: List of OTC medication suggestions (empty for High/Critical)
- `non_medication`: List of non-medication treatment options
- `disclaimer`: Appropriate safety disclaimer text
- `seek_professional`: Boolean (always True)

**Behavior**:
- For Low/Moderate severity: Returns medications with standard disclaimer
- For High severity: Returns empty medications list with emergency disclaimer
- For Critical severity: Returns empty medications list with critical disclaimer
- Unknown illnesses: Returns safe default (no medications, generic advice)

### `get_base_severity(illness: str) -> Severity`

Returns the base severity level for an illness from the database.

**Parameters**:
- `illness`: The illness name

**Returns**: Base severity level (defaults to MODERATE if not found)

### `get_all_illnesses() -> List[str]`

Returns a list of all illnesses in the treatment database.

### `illness_exists(illness: str) -> bool`

Checks if an illness exists in the treatment database.

## Usage Example

```python
from src.treatment.treatment_database import get_treatment_info
from src.models.data_models import Severity

# Get treatment for low severity common cold
treatment = get_treatment_info("common_cold", Severity.LOW)
print(f"Medications: {treatment['medications']}")
print(f"Non-medication: {treatment['non_medication']}")
print(f"Disclaimer: {treatment['disclaimer']}")

# Get treatment for critical severity meningitis
critical_treatment = get_treatment_info("meningitis", Severity.CRITICAL)
print(f"Medications: {critical_treatment['medications']}")  # Empty list
print(f"Disclaimer: {critical_treatment['disclaimer']}")  # Critical warning
```

## Integration with TreatmentService

The treatment database is designed to be used by the TreatmentService (Task 11.2):

```python
from src.treatment.treatment_database import get_treatment_info
from src.models.data_models import TreatmentInfo

def get_treatment_suggestions(prediction: Prediction) -> TreatmentInfo:
    """Get treatment suggestions for a prediction."""
    treatment_data = get_treatment_info(
        prediction.illness,
        prediction.severity
    )
    
    return TreatmentInfo(
        medications=treatment_data["medications"],
        non_medication=treatment_data["non_medication"],
        disclaimer=treatment_data["disclaimer"],
        seek_professional=treatment_data["seek_professional"]
    )
```

## Safety Features

1. **Conservative Defaults**: Unknown illnesses return no medications and recommend professional care
2. **Always Recommend Professional Care**: All treatments include professional consultation recommendation
3. **Severity-Based Blocking**: High/Critical severity automatically blocks medication suggestions
4. **Comprehensive Disclaimers**: All medication suggestions include detailed safety warnings
5. **Case-Insensitive Lookup**: Handles various illness name formats
6. **Space Handling**: Converts spaces to underscores for database lookup

## Testing

The implementation includes comprehensive unit tests covering:

- ✅ Low/Moderate severity includes medications with disclaimers
- ✅ High/Critical severity excludes medications
- ✅ Non-medication options always included
- ✅ Severity-based filtering works correctly
- ✅ Unknown illnesses return safe defaults
- ✅ Base severity retrieval
- ✅ Illness existence checking
- ✅ Disclaimer content validation
- ✅ Critical conditions have emergency guidance
- ✅ Coverage of major illness categories
- ✅ Case-insensitive lookup
- ✅ Space handling in illness names
- ✅ Treatment info structure validation

All 19 tests pass successfully.

## Future Enhancements

Potential improvements for future iterations:

1. **Database Expansion**: Add more illnesses and conditions
2. **Localization**: Translate treatment suggestions to multiple languages
3. **Personalization**: Consider age, pregnancy, existing conditions
4. **Drug Interactions**: Add warnings for common drug interactions
5. **Dosage Information**: Include more specific dosage guidelines
6. **External Database**: Move to external database (PostgreSQL) for easier updates
7. **Version Control**: Track changes to treatment recommendations over time
8. **Evidence-Based Updates**: Regular updates based on medical guidelines

## Compliance and Disclaimers

**IMPORTANT**: This treatment database provides general information only and is NOT a substitute for professional medical advice, diagnosis, or treatment. All users should:

- Consult healthcare professionals before taking any medication
- Seek immediate medical attention for serious symptoms
- Follow medication labels and dosage instructions
- Be aware of allergies and drug interactions
- Not rely solely on this system for medical decisions

The system is designed with safety as the top priority, always erring on the side of caution by recommending professional consultation.

## Requirements Validation

This implementation validates the following requirements:

- **18.1**: ✅ Provides OTC medication suggestions for appropriate illnesses
- **18.2**: ✅ Includes clear disclaimers that suggestions are informational only
- **18.3**: ✅ Recommends consulting healthcare professionals before taking medication
- **18.4**: ✅ Does NOT provide medication suggestions for High/Critical severity
- **18.5**: ✅ Includes non-medication treatment options for all predictions

## Conclusion

The treatment database provides a comprehensive, safe, and well-tested foundation for the TreatmentService. It implements all required features with appropriate safety measures and is ready for integration with the prediction pipeline.
