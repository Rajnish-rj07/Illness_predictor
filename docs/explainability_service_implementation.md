# ExplainabilityService Implementation

## Overview

The ExplainabilityService provides interpretable explanations for illness predictions using SHAP (SHapley Additive exPlanations) values. This service integrates with the XGBoost model to compute feature importance and generate user-friendly explanations.

## Implementation Details

### Location
- **Service**: `src/explainability/explainability_service.py`
- **Tests**: `tests/test_explainability_service.py`

### Key Features

1. **SHAP Integration**
   - Uses `shap.TreeExplainer` for XGBoost models
   - Computes SHAP values for each prediction
   - Caches explainers for performance

2. **Top Contributor Identification**
   - Identifies top 3 symptoms by absolute SHAP value
   - Aggregates SHAP values across presence, severity, and duration features
   - Filters to only include symptoms present in the symptom vector

3. **User-Friendly Explanations**
   - Generates natural language explanation text
   - Formats illness names and symptom names for readability
   - Indicates whether symptoms support or reduce likelihood of diagnosis
   - Provides confidence percentage

4. **Visualization**
   - Creates horizontal bar charts showing feature importance
   - Color-codes positive (green) and negative (red) contributions
   - Supports base64 encoding for embedding or file output
   - Uses matplotlib with non-interactive backend

5. **Feature Importance**
   - Retrieves global feature importance from XGBoost model
   - Returns top-k most important features
   - Sorted by importance in descending order

## API Reference

### ExplainabilityService

```python
class ExplainabilityService:
    def __init__(self, ml_model_service: MLModelService)
    
    def explain_prediction(
        self,
        symptom_vector: SymptomVector,
        prediction: Prediction,
        model_version: Optional[str] = None
    ) -> Explanation
    
    def visualize_explanation(
        self,
        explanation: Explanation,
        symptom_vector: SymptomVector,
        prediction: Prediction,
        output_format: str = 'base64'
    ) -> Optional[str]
    
    def get_feature_importance(
        self,
        model_version: Optional[str] = None,
        top_k: int = 20
    ) -> List[Tuple[str, float]]
    
    def clear_cache(self) -> None
```

### Key Methods

#### explain_prediction()
Generates a complete explanation for a prediction including:
- Top 3 contributing symptoms with SHAP values
- User-friendly explanation text
- Full SHAP value array for all features

**Validates**: Requirements 14.1, 14.2, 14.3

#### visualize_explanation()
Creates a visualization of feature importance:
- Horizontal bar chart with color-coded contributions
- Base64-encoded image or file output
- Includes legend and formatted labels

**Validates**: Requirements 14.4

#### get_feature_importance()
Retrieves global feature importance from the model:
- Returns top-k features by importance
- Sorted in descending order
- Useful for understanding overall model behavior

**Validates**: Requirements 14.1

## Example Usage

```python
from src.explainability.explainability_service import ExplainabilityService
from src.ml.ml_model_service import MLModelService
from src.models.data_models import SymptomVector, SymptomInfo, Prediction, Severity

# Initialize services
ml_service = MLModelService()
explainability_service = ExplainabilityService(ml_service)

# Create symptom vector
symptom_vector = SymptomVector(
    symptoms={
        'fever': SymptomInfo(present=True, severity=8, duration='1-3d'),
        'cough': SymptomInfo(present=True, severity=6, duration='3-7d'),
        'headache': SymptomInfo(present=True, severity=5, duration='<1d'),
    }
)

# Create prediction
prediction = Prediction(
    illness='influenza',
    confidence_score=0.75,
    severity=Severity.MODERATE
)

# Generate explanation
explanation = explainability_service.explain_prediction(
    symptom_vector,
    prediction
)

print(explanation.explanation_text)
# Output:
# Based on your symptoms, there is a 75% likelihood of Influenza.
# 
# The main symptoms contributing to this prediction are:
# 1. Fever - This symptom significantly supports this diagnosis.
# 2. Cough - This symptom moderately supports this diagnosis.
# 3. Headache - This symptom slightly supports this diagnosis.

# Create visualization
image_base64 = explainability_service.visualize_explanation(
    explanation,
    symptom_vector,
    prediction,
    output_format='base64'
)

# Get global feature importance
top_features = explainability_service.get_feature_importance(top_k=10)
for feature, importance in top_features:
    print(f"{feature}: {importance:.4f}")
```

## Testing

### Test Coverage
- 23 unit tests covering all major functionality
- Tests for initialization, caching, explanation generation, visualization, and error handling
- Edge cases: empty symptom vectors, single symptoms, errors

### Test Results
All 23 tests pass successfully:
- ✅ Service initialization
- ✅ Explainer caching
- ✅ SHAP value computation
- ✅ Top contributor identification (exactly 3)
- ✅ Explanation text generation
- ✅ Visualization creation (base64 and file)
- ✅ Feature importance retrieval
- ✅ Error handling
- ✅ Edge cases

## Requirements Validation

### Requirement 14.1: SHAP Value Computation
✅ **Implemented**: `explain_prediction()` computes SHAP values using TreeExplainer

### Requirement 14.2: Top 3 Contributors
✅ **Implemented**: Identifies exactly 3 symptoms with highest absolute SHAP values

### Requirement 14.3: User-Friendly Explanation
✅ **Implemented**: Generates natural language explanation text with formatted names and confidence

### Requirement 14.4: Feature Importance Visualization
✅ **Implemented**: Creates bar chart visualization with color-coded contributions

## Technical Details

### SHAP Value Aggregation
For each symptom, SHAP values are computed for three features:
1. **Presence**: Binary indicator (0 or 1)
2. **Severity**: Normalized value (0-1 scale)
3. **Duration**: Encoded value (0-1 scale)

The total SHAP contribution for a symptom is the sum of these three values.

### Caching Strategy
- Explainers are cached by model version
- Reduces overhead of creating new explainers for repeated predictions
- Cache can be cleared manually if needed

### Error Handling
- Gracefully handles SHAP computation errors
- Returns basic explanation on failure
- Logs errors for debugging

## Dependencies

- **shap**: 0.50.0 (SHAP library for model explainability)
- **matplotlib**: For visualization
- **numpy**: For numerical operations
- **xgboost**: Model must be XGBoost for TreeExplainer

## Performance Considerations

1. **First Prediction**: Slower due to explainer creation
2. **Subsequent Predictions**: Fast due to caching
3. **Visualization**: Moderate overhead for image generation
4. **Memory**: Explainers are cached in memory

## Future Enhancements

1. **Interactive Visualizations**: Use plotly for interactive charts
2. **Batch Explanations**: Explain multiple predictions at once
3. **Explanation Templates**: Customizable explanation text templates
4. **Multi-Language Support**: Generate explanations in different languages
5. **Explanation History**: Track and compare explanations over time

## References

- SHAP Documentation: https://shap.readthedocs.io/
- TreeExplainer: https://shap.readthedocs.io/en/latest/generated/shap.TreeExplainer.html
- Requirements: See `.kiro/specs/illness-prediction-system/requirements.md` (Requirements 14.1-14.4)
- Design: See `.kiro/specs/illness-prediction-system/design.md` (Section 5: Explainability Service)
