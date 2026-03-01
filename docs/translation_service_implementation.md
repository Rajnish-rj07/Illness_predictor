# TranslationService Implementation Guide

## Overview

The TranslationService provides multi-language support for the Illness Prediction System, enabling users to interact in their native language. This guide explains how to integrate the service with other system components.

## Supported Languages

- **English (en)** - Default language
- **Spanish (es)** - Español
- **French (fr)** - Français
- **Hindi (hi)** - हिन्दी
- **Mandarin Chinese (zh)** - 中文

## Quick Start

### Basic Usage

```python
from src.translation.translation_service import TranslationService

# Initialize service (uses API key from settings)
translator = TranslationService()

# Detect user's language
user_message = "Tengo dolor de cabeza"
language = translator.detect_language(user_message)  # Returns 'es'

# Translate user input to English (for ML model)
english_text = translator.translate_to_english(user_message, language)
# Returns: "I have a headache"

# Translate system response to user's language
system_response = "Do you have a fever?"
translated_response = translator.translate_from_english(system_response, language)
# Returns: "¿Tiene fiebre?"
```

## Integration with System Components

### 1. ConversationManager Integration

```python
class ConversationManager:
    def __init__(self):
        self.translator = TranslationService()
        # ... other initialization
    
    def process_message(self, session_id: str, message: str) -> Response:
        session = self.get_session(session_id)
        
        # Translate user message to English for processing
        english_message = self.translator.translate_to_english(
            message, 
            session.language
        )
        
        # Process message (extract symptoms, generate questions, etc.)
        response = self._process_english_message(english_message, session)
        
        # Translate response back to user's language
        if session.language != 'en':
            response.message = self.translator.translate_from_english(
                response.message,
                session.language
            )
        
        return response
```

### 2. Session Initialization with Language Detection

```python
def start_session(self, channel: str, user_id: str, initial_message: str) -> Session:
    # Detect language from initial message
    detected_language = self.translator.detect_language(initial_message)
    
    # Create session with detected language
    session = Session(
        session_id=generate_uuid(),
        user_id=user_id,
        channel=channel,
        language=detected_language,
        created_at=datetime.utcnow(),
        last_active=datetime.utcnow(),
        status=SessionStatus.ACTIVE,
        conversation_context=ConversationContext(),
        symptom_vector=SymptomVector()
    )
    
    return session
```

### 3. PredictionService Integration

```python
class PredictionService:
    def __init__(self):
        self.translator = TranslationService()
        # ... other initialization
    
    def format_predictions(
        self, 
        predictions: List[Prediction], 
        language: str
    ) -> List[Dict[str, Any]]:
        formatted = []
        
        for prediction in predictions:
            pred_dict = {
                'illness': prediction.illness,
                'confidence': prediction.confidence_score,
                'severity': prediction.severity.value,
                'explanation': prediction.explanation.explanation_text
            }
            
            # Translate to user's language
            if language != 'en':
                pred_dict = self.translator.translate_response_dict(
                    pred_dict,
                    language
                )
            
            formatted.append(pred_dict)
        
        return formatted
```

### 4. QuestionEngine Integration

```python
class QuestionEngine:
    def __init__(self):
        self.translator = TranslationService()
        # ... other initialization
    
    def generate_next_question(
        self, 
        symptom_vector: SymptomVector,
        language: str
    ) -> str:
        # Generate question in English
        english_question = self._generate_english_question(symptom_vector)
        
        # Translate to user's language
        if language != 'en':
            return self.translator.translate_from_english(
                english_question,
                language
            )
        
        return english_question
```

### 5. TreatmentService Integration

```python
class TreatmentService:
    def __init__(self):
        self.translator = TranslationService()
        # ... other initialization
    
    def get_treatment_suggestions(
        self,
        illness: str,
        severity: Severity,
        language: str
    ) -> TreatmentInfo:
        # Get treatment info in English
        treatment = self._get_english_treatment(illness, severity)
        
        # Translate to user's language
        if language != 'en':
            treatment.medications = [
                self.translator.translate_from_english(med, language)
                for med in treatment.medications
            ]
            treatment.non_medication = [
                self.translator.translate_from_english(rec, language)
                for rec in treatment.non_medication
            ]
            treatment.disclaimer = self.translator.translate_from_english(
                treatment.disclaimer,
                language
            )
        
        return treatment
```

## Best Practices

### 1. Language Detection
- Always detect language from the first user message
- Store detected language in session
- Allow users to manually override language if needed

### 2. Translation Flow
- **User Input:** Always translate to English before processing
- **System Output:** Always translate from English to user's language
- **ML Model:** Always use English (standardized format)

### 3. Error Handling
```python
try:
    translated = translator.translate_to_english(text, language)
except Exception as e:
    logger.error(f"Translation failed: {e}")
    # Fallback: use original text or default language
    translated = text
```

### 4. Caching
- The service automatically caches translations
- No need to implement additional caching
- Clear cache periodically if memory is a concern:
  ```python
  translator.clear_cache()
  ```

### 5. Performance Optimization
- Batch translations when possible:
  ```python
  symptoms = ["symptom1", "symptom2", "symptom3"]
  translated = translator.translate_symptom_list(symptoms, language)
  ```

- Use dictionary translation for structured data:
  ```python
  response = {'field1': 'text1', 'field2': 'text2'}
  translated = translator.translate_response_dict(response, language)
  ```

## Configuration

### Environment Variables

Add to `.env`:
```bash
# Google Cloud Translation API key
TRANSLATION_API_KEY=your-api-key-here

# Supported languages (comma-separated)
SUPPORTED_LANGUAGES=["en", "es", "fr", "hi", "zh"]

# Default language
DEFAULT_LANGUAGE=en
```

### Settings

The service uses `config.settings`:
```python
from config.settings import settings

# Access translation settings
api_key = settings.translation_api_key
languages = settings.supported_languages
default_lang = settings.default_language
```

## Testing

### Unit Testing with Mocks

```python
from unittest.mock import Mock, patch
from src.translation.translation_service import TranslationService

@patch('src.translation.translation_service.requests.post')
def test_translation(mock_post):
    # Mock API response
    mock_response = Mock()
    mock_response.json.return_value = {
        'data': {
            'translations': [{
                'translatedText': 'translated text'
            }]
        }
    }
    mock_response.raise_for_status = Mock()
    mock_post.return_value = mock_response
    
    # Test translation
    service = TranslationService(api_key="test-key")
    result = service.translate_to_english("texto", 'es')
    
    assert result == 'translated text'
```

### Integration Testing

```python
def test_end_to_end_translation():
    """Test with real API (requires valid API key)."""
    service = TranslationService()
    
    # Skip if no API key
    if not service.api_key:
        pytest.skip("API key not configured")
    
    # Test translation
    result = service.translate_to_english("Hola", 'es')
    assert "hello" in result.lower()
```

## Common Patterns

### Pattern 1: Session-Based Translation

```python
def handle_user_message(session: Session, message: str) -> str:
    translator = TranslationService()
    
    # Translate input
    english_input = translator.translate_to_english(
        message,
        session.language
    )
    
    # Process (your logic here)
    english_response = process_message(english_input)
    
    # Translate output
    response = translator.translate_from_english(
        english_response,
        session.language
    )
    
    return response
```

### Pattern 2: Conditional Translation

```python
def translate_if_needed(text: str, language: str) -> str:
    if language == 'en':
        return text  # No translation needed
    
    translator = TranslationService()
    return translator.translate_from_english(text, language)
```

### Pattern 3: Batch Processing

```python
def translate_multiple_fields(data: Dict[str, str], language: str) -> Dict[str, str]:
    if language == 'en':
        return data
    
    translator = TranslationService()
    return translator.translate_response_dict(data, language)
```

## Troubleshooting

### Issue: Translation Returns Original Text

**Cause:** API key not configured or API error

**Solution:**
1. Check API key in `.env` file
2. Verify API key is valid
3. Check API quota and billing
4. Review logs for error messages

### Issue: Wrong Language Detected

**Cause:** Ambiguous or short text

**Solution:**
1. Use longer text for detection (>10 words recommended)
2. Allow manual language selection
3. Use language from previous session if available

### Issue: Slow Translation

**Cause:** API latency or no caching

**Solution:**
1. Check cache hit rate: `translator.get_cache_size()`
2. Pre-cache common phrases
3. Use batch translation for multiple items
4. Consider implementing Redis cache for distributed systems

### Issue: Medical Terms Mistranslated

**Cause:** Generic translation may not preserve medical terminology

**Solution:**
1. Build custom medical term dictionary
2. Pre-translate and cache medical terms
3. Use glossary feature of Google Translate API (advanced)
4. Validate critical translations manually

## API Costs

### Google Cloud Translation API Pricing
- **Free Tier:** 500,000 characters/month
- **Paid Tier:** $20 per 1 million characters
- **Detection:** Counts as translation

### Cost Optimization
1. **Caching:** Reduces API calls by ~80%
2. **Batch Operations:** More efficient than individual calls
3. **Smart Detection:** Only detect once per session
4. **Pre-translation:** Cache common phrases at startup

### Monitoring Usage
```python
# Track API calls
import logging

logger = logging.getLogger(__name__)

# Log each translation
logger.info(f"Translated {len(text)} characters from {source} to {target}")
```

## Security Considerations

### API Key Protection
- Never commit API keys to version control
- Use environment variables or secret management
- Rotate keys regularly
- Monitor for unauthorized usage

### Data Privacy
- Translation API processes text on Google servers
- Consider data residency requirements
- Review Google Cloud privacy policies
- Implement data anonymization if needed

### Rate Limiting
- Implement application-level rate limiting
- Monitor API quota usage
- Handle rate limit errors gracefully
- Consider fallback to default language

## Future Enhancements

### Planned Features
1. **Offline Translation:** For common phrases
2. **Custom Medical Dictionary:** Domain-specific translations
3. **Translation Quality Scoring:** Validate translation accuracy
4. **More Languages:** Expand beyond current 5
5. **Voice Support:** Integrate with speech-to-text

### Extensibility
The service is designed to be extended:
```python
class CustomTranslationService(TranslationService):
    def translate_medical_term(self, term: str, language: str) -> str:
        # Custom logic for medical terms
        pass
```

## Support

### Documentation
- API Documentation: [Google Cloud Translation](https://cloud.google.com/translate/docs)
- Service Code: `src/translation/translation_service.py`
- Tests: `tests/test_translation_service*.py`

### Contact
For issues or questions:
1. Check logs for error messages
2. Review this documentation
3. Consult API documentation
4. Contact development team

---

**Last Updated:** 2024
**Version:** 1.0.0
**Status:** Production Ready
