# TreatmentService Implementation

## Overview

The TreatmentService provides treatment suggestions based on illness predictions and severity levels. It integrates with the treatment database to deliver appropriate medical guidance while maintaining safety through severity-based filtering and comprehensive disclaimers.

**Implementation Date:** Task 11.2  
**Validates:** Requirements 18.1, 18.2, 18.3, 18.4, 18.5

## Architecture

### Component Structure

```
src/treatment/
├── treatment_database.py      # Treatment data and mappings
└── treatment_service.py        # Service implementation

tests/
├── test_treatment_service.py           # Unit tests (25 tests)
└── test_treatment_service_properties.py # Property-based tests (10 tests)
```

### Key Features

1. **Severity-Based Filtering**
   - Low/Moderate severity: Include OTC medication suggestions with disclaimers
   - High/Critical severity: No medication suggestions, recommend immediate care

2. **Comprehensive Treatment Information**
   - Over-the-counter medication suggestions
   - Non-medication treatment options (rest, hydration, diet)
   - Safety disclaimers
   - Professional consultation recommendations

3. **Integration with Treatment Database**
   - 30+ illnesses with detailed treatment information
   - Base severity levels for each illness
   - Medication and non-medication options

4. **Safety-First Approach**
   - Always recommend professional consultation
   - Emergency disclaimers for high/critical severity
   - Clear warnings about self-treatment limitations

## Implementation Details

### TreatmentService Class

```python
class TreatmentService:
    """
    Service for providing treatment suggestions based on illness predictions.
    
    Features:
    - Retrieves treatment information from the treatment database
    - Filters medication suggestions based on severity level
    - Provides non-medication treatment options for all severities
    - Includes appropriate disclaimers and professional consultation recommendations
    - Handles High/Critical severity with emergency recommendations
    """
```

### Core Methods

#### 1. get_treatment_suggestions(illness, severity)

Retrieves treatment suggestions for a specific illness and severity level.

**Parameters:**
- `illness` (str): Name of the predicted illness
- `severity` (Severity): Severity level (LOW, MODERATE, HIGH, CRITICAL)

**Returns:**
- `TreatmentInfo`: Object containing medications, non-medication options, disclaimer, and professional consultation flag

**Logic:**
```python
if severity in [HIGH, CRITICAL]:
    # No medication suggestions
    # Emergency disclaimer
    # Recommend immediate medical attention
else:
    # Include OTC medications
    # Standard disclaimer with safety information
    # Recommend professional consultation
```

**Validates:** Requirements 18.1, 18.2, 18.3, 18.4, 18.5

#### 2. get_treatment_for_prediction(prediction)

Convenience method that extracts illness and severity from a Prediction object.

**Parameters:**
- `prediction` (Prediction): Prediction object containing illness and severity

**Returns:**
- `TreatmentInfo`: Treatment suggestions for the prediction

#### 3. get_treatment_for_multiple_predictions(predictions)

Retrieves treatment suggestions for multiple predictions.

**Parameters:**
- `predictions` (List[Prediction]): List of prediction objects

**Returns:**
- `List[TreatmentInfo]`: Treatment suggestions for each prediction

#### 4. format_treatment_info(treatment_info, include_disclaimer)

Formats treatment information for user presentation.

**Parameters:**
- `treatment_info` (TreatmentInfo): Treatment information to format
- `include_disclaimer` (bool): Whether to include disclaimer (default: True)

**Returns:**
- `str`: Formatted string with medications, self-care recommendations, and disclaimers

### Utility Methods

- `check_illness_exists(illness)`: Check if illness exists in database
- `get_base_severity_for_illness(illness)`: Get base severity level for an illness
- `has_emergency_recommendations(treatment_info)`: Check if treatment contains emergency recommendations
- `get_severity_appropriate_message(severity)`: Get user-friendly message for severity level

## Integration with Treatment Database

The TreatmentService integrates with the treatment database module which provides:

### Treatment Database Structure

```python
TREATMENT_DATABASE = {
    "illness_name": {
        "medications": [...],      # OTC medications
        "non_medication": [...],   # Non-medication options
        "base_severity": Severity, # Base severity level
    }
}
```

### Database Coverage

- **30+ illnesses** with detailed treatment information
- **Respiratory infections:** common_cold, influenza, bronchitis, pneumonia, sinusitis
- **Gastrointestinal issues:** gastroenteritis, food_poisoning, acid_reflux
- **Headaches:** tension_headache, migraine
- **Allergies:** allergic_rhinitis, contact_dermatitis
- **Musculoskeletal:** muscle_strain, back_pain
- **Critical conditions:** appendicitis, meningitis, heart_attack, stroke, anaphylaxis
- **Mental health:** anxiety, depression, insomnia
- **Other conditions:** UTI, conjunctivitis, asthma

### Disclaimers

The database provides standardized disclaimers:

1. **MEDICATION_DISCLAIMER**: For Low/Moderate severity with OTC suggestions
2. **PROFESSIONAL_CONSULTATION_TEXT**: Standard recommendation to consult healthcare professional
3. **EMERGENCY_CONSULTATION_TEXT**: For High severity conditions
4. **CRITICAL_CONSULTATION_TEXT**: For Critical severity requiring immediate emergency care

## Testing

### Unit Tests (25 tests)

**Test Coverage:**
- Treatment retrieval for all severity levels
- Medication filtering based on severity
- Non-medication option inclusion
- Disclaimer and professional consultation recommendations
- Integration with Prediction objects
- Utility methods
- Edge cases (unknown illnesses, severity overrides)
- Specific illness categories

**Key Test Cases:**
```python
def test_get_treatment_for_low_severity()
def test_get_treatment_for_high_severity()
def test_non_medication_options_always_included()
def test_disclaimer_included_for_low_moderate()
def test_emergency_disclaimer_for_high_critical()
def test_seek_professional_always_true()
def test_severity_override_for_high_critical()
```

### Property-Based Tests (10 tests)

**Properties Tested:**

1. **Property 34: Medication suggestion safety** (Requirements 18.1, 18.2, 18.3)
   - Low/Moderate severity predictions include disclaimers
   - Professional consultation is recommended
   - Safety information is present

2. **Property 35: High severity medication blocking** (Requirement 18.4)
   - High/Critical severity predictions have NO medication suggestions
   - Emergency care is recommended

3. **Property 36: Non-medication option inclusion** (Requirement 18.5)
   - All predictions include at least one non-medication option
   - Options are valid strings

**Additional Properties:**
- Treatment consistency for same inputs
- Valid treatment for any Prediction object
- Disclaimer always present
- seek_professional always True
- Unknown illness handling
- Formatted output validity

**Configuration:**
- 20 examples per property test (main properties)
- 10 examples for edge case properties
- Custom strategies for illness names, severity levels, and predictions

## Usage Examples

### Basic Usage

```python
from src.treatment.treatment_service import TreatmentService
from src.models.data_models import Severity

# Create service
treatment_service = TreatmentService()

# Get treatment for an illness
treatment = treatment_service.get_treatment_suggestions(
    illness="common_cold",
    severity=Severity.LOW
)

print(f"Medications: {treatment.medications}")
print(f"Self-care: {treatment.non_medication}")
print(f"Disclaimer: {treatment.disclaimer}")
```

### Integration with Predictions

```python
# Get treatment for a prediction
prediction = Prediction(
    illness="influenza",
    confidence_score=0.85,
    severity=Severity.MODERATE,
    explanation=None,
    treatment_suggestions=None
)

treatment = treatment_service.get_treatment_for_prediction(prediction)
prediction.treatment_suggestions = treatment

# Format for user
formatted = treatment_service.format_treatment_info(treatment)
print(formatted)
```

### Multiple Predictions

```python
# Get treatments for multiple predictions
predictions = [pred1, pred2, pred3]
treatments = treatment_service.get_treatment_for_multiple_predictions(predictions)

# Update predictions with treatments
for prediction, treatment in zip(predictions, treatments):
    prediction.treatment_suggestions = treatment
```

### Emergency Handling

```python
# Check for emergency recommendations
treatment = treatment_service.get_treatment_suggestions(
    illness="heart_attack",
    severity=Severity.CRITICAL
)

if treatment_service.has_emergency_recommendations(treatment):
    # Display emergency message
    msg = treatment_service.get_severity_appropriate_message(Severity.CRITICAL)
    print(msg)
    # "🚨 CRITICAL: Your symptoms require immediate emergency medical attention..."
```

## Severity-Based Treatment Logic

### Low Severity
- **Medications:** Include OTC suggestions
- **Non-medication:** Rest, hydration, self-care
- **Disclaimer:** Standard safety information
- **Message:** "🟢 LOW SEVERITY: Your symptoms are generally mild..."

### Moderate Severity
- **Medications:** Include OTC suggestions
- **Non-medication:** Rest, hydration, self-care
- **Disclaimer:** Standard safety information
- **Message:** "🟡 MODERATE: Your symptoms should be evaluated by a healthcare professional..."

### High Severity
- **Medications:** NONE (blocked)
- **Non-medication:** Basic guidance only
- **Disclaimer:** Emergency consultation text
- **Message:** "⚠️ HIGH SEVERITY: Your symptoms may indicate a serious condition..."

### Critical Severity
- **Medications:** NONE (blocked)
- **Non-medication:** Emergency instructions only
- **Disclaimer:** Critical consultation text
- **Message:** "🚨 CRITICAL: Your symptoms require immediate emergency medical attention..."

## Safety Features

### 1. Medication Filtering
- Automatically blocks medication suggestions for High/Critical severity
- Prevents inappropriate self-treatment recommendations

### 2. Comprehensive Disclaimers
- All treatments include appropriate disclaimers
- Severity-specific warning levels
- Clear language about limitations

### 3. Professional Consultation
- Always recommend consulting healthcare professional
- Stronger recommendations for higher severity
- Emergency service guidance for critical conditions

### 4. Non-Medication Options
- Always included regardless of severity
- Provides safe self-care guidance
- Appropriate for severity level

## Integration Points

### With PredictionService
```python
# PredictionService can use TreatmentService to add treatment info
prediction_service = PredictionService(ml_model_service)
treatment_service = TreatmentService()

predictions = prediction_service.predict(symptom_vector)
for prediction in predictions:
    treatment = treatment_service.get_treatment_for_prediction(prediction)
    prediction.treatment_suggestions = treatment
```

### With ConversationManager
```python
# ConversationManager can format treatment info for user
treatment = treatment_service.get_treatment_for_prediction(prediction)
formatted = treatment_service.format_treatment_info(treatment)
response_message = f"Prediction: {prediction.illness}\n\n{formatted}"
```

### With ExplainabilityService
```python
# Combine treatment suggestions with explanations
explanation = explainability_service.explain_prediction(symptom_vector, prediction)
treatment = treatment_service.get_treatment_for_prediction(prediction)

# Present both to user
print(f"Why this prediction: {explanation.explanation_text}")
print(f"\nTreatment suggestions:\n{treatment_service.format_treatment_info(treatment)}")
```

## Performance Considerations

- **Database lookups:** O(1) dictionary access
- **No external API calls:** All data is local
- **Stateless service:** No session management overhead
- **Lightweight operations:** Simple data retrieval and formatting

## Future Enhancements

1. **Personalization**
   - Consider patient age, allergies, existing conditions
   - Customize recommendations based on user profile

2. **Localization**
   - Translate treatment suggestions to multiple languages
   - Region-specific medication names

3. **Evidence-Based Updates**
   - Regular updates based on medical research
   - Integration with medical databases

4. **Interaction Checking**
   - Check for drug interactions
   - Consider contraindications

5. **Dosage Information**
   - Provide specific dosage recommendations
   - Age and weight-based adjustments

## Compliance and Safety

### Medical Disclaimer
All treatment suggestions include clear disclaimers that:
- Information is for educational purposes only
- Not a substitute for professional medical advice
- Users should consult healthcare professionals
- Emergency services should be contacted for serious conditions

### Regulatory Compliance
- Follows healthcare information guidelines
- Appropriate warnings for self-treatment
- Clear scope limitations
- Emergency escalation protocols

## Conclusion

The TreatmentService successfully implements comprehensive treatment suggestion functionality with:
- ✅ 35/35 tests passing (25 unit + 10 property-based)
- ✅ Severity-based medication filtering
- ✅ Comprehensive safety disclaimers
- ✅ Integration with treatment database
- ✅ Professional consultation recommendations
- ✅ Emergency handling for critical conditions

The implementation validates all requirements (18.1-18.5) and provides a solid foundation for delivering safe, informative treatment suggestions to users.
