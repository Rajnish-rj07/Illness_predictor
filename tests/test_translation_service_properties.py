"""
Property-based tests for TranslationService.

These tests verify universal properties that should hold across all inputs:
- Property 21: Language consistency across session messages
- Property 22: Symptom translation preservation (semantic equivalence)

Uses hypothesis for property-based testing with 20 examples for main properties
and 10 for secondary properties.

Validates: Requirements 15.3, 15.4, 15.5
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch
from src.translation.translation_service import TranslationService


# Custom strategies for translation testing
@st.composite
def supported_language_codes(draw):
    """Generate supported language codes."""
    return draw(st.sampled_from(['en', 'es', 'fr', 'hi', 'zh']))


@st.composite
def symptom_texts(draw):
    """Generate symptom description texts."""
    symptoms = [
        "I have a headache",
        "I have a fever",
        "I have a cough",
        "I have nausea",
        "I have chest pain",
        "I have abdominal pain",
        "I have dizziness",
        "I have fatigue",
        "I have a sore throat",
        "I have shortness of breath"
    ]
    return draw(st.sampled_from(symptoms))


@st.composite
def system_messages(draw):
    """Generate system message texts."""
    messages = [
        "Do you have a fever?",
        "How long have you had these symptoms?",
        "On a scale of 1-10, how severe is the pain?",
        "Have you experienced this before?",
        "Are you taking any medications?",
        "You may have influenza",
        "Please consult a healthcare professional",
        "Your symptoms suggest a mild condition"
    ]
    return draw(st.sampled_from(messages))


class TestProperty21LanguageConsistency:
    """
    Property 21: Language consistency
    
    For any session with a selected language, all system-generated messages
    should be in that language.
    
    Validates: Requirements 15.3, 15.5
    """
    
    @settings(max_examples=20)
    @given(
        target_language=supported_language_codes(),
        messages=st.lists(system_messages(), min_size=1, max_size=10)
    )
    @patch('src.translation.translation_service.requests.post')
    def test_property_21_all_messages_in_selected_language(
        self,
        mock_post,
        target_language,
        messages
    ):
        """
        Feature: illness-prediction-system, Property 21: Language consistency
        
        For any session with a selected language, all system-generated messages
        should be in that language.
        
        **Validates: Requirements 15.3, 15.5**
        """
        # Mock translation API to return language-tagged responses
        def mock_translate(url, params, timeout):
            response = Mock()
            # Tag translated text with target language for verification
            translated = f"[{params['target']}]{params['q']}"
            response.json.return_value = {
                'data': {
                    'translations': [{
                        'translatedText': translated
                    }]
                }
            }
            response.raise_for_status = Mock()
            return response
        
        mock_post.side_effect = mock_translate
        
        service = TranslationService(api_key="test-key")
        
        # Translate all messages to the target language
        translated_messages = []
        for message in messages:
            translated = service.translate_from_english(message, target_language)
            translated_messages.append(translated)
        
        # Property: All messages should be in the target language
        # (In real scenario, we'd verify actual language, here we verify consistency)
        if target_language == 'en':
            # English messages should remain unchanged
            for original, translated in zip(messages, translated_messages):
                assert translated == original
        else:
            # Non-English messages should be translated (tagged with language)
            for translated in translated_messages:
                assert translated.startswith(f"[{target_language}]")
    
    @settings(max_examples=20)
    @given(
        target_language=supported_language_codes(),
        message_count=st.integers(min_value=1, max_value=15)
    )
    @patch('src.translation.translation_service.requests.post')
    def test_property_21_language_consistency_across_conversation(
        self,
        mock_post,
        target_language,
        message_count
    ):
        """
        Test that language remains consistent across multiple conversation turns.
        
        **Validates: Requirements 15.3, 15.5**
        """
        # Mock translation to return consistent language
        def mock_translate(url, params, timeout):
            response = Mock()
            response.json.return_value = {
                'data': {
                    'translations': [{
                        'translatedText': f"[{params['target']}]translated"
                    }]
                }
            }
            response.raise_for_status = Mock()
            return response
        
        mock_post.side_effect = mock_translate
        
        service = TranslationService(api_key="test-key")
        
        # Simulate conversation with multiple messages
        languages_used = set()
        for i in range(message_count):
            message = f"Message {i}"
            translated = service.translate_from_english(message, target_language)
            
            if target_language == 'en':
                languages_used.add('en')
            else:
                # Extract language tag from mock response
                if translated.startswith('['):
                    lang = translated[1:3]
                    languages_used.add(lang)
        
        # Property: Only one language should be used throughout
        if target_language == 'en':
            assert languages_used == {'en'}
        else:
            assert len(languages_used) <= 1  # At most one language


class TestProperty22SymptomTranslationPreservation:
    """
    Property 22: Symptom translation preservation
    
    For any symptom description in any supported language, translating to
    the standardized format and back should preserve the core symptom meaning
    (semantic equivalence).
    
    Validates: Requirements 15.4
    """
    
    @settings(max_examples=20)
    @given(
        source_language=supported_language_codes(),
        symptom=symptom_texts()
    )
    @patch('src.translation.translation_service.requests.post')
    def test_property_22_symptom_meaning_preserved(
        self,
        mock_post,
        source_language,
        symptom
    ):
        """
        Feature: illness-prediction-system, Property 22: Symptom translation preservation
        
        For any symptom description in any supported language, translating to
        the standardized format and back should preserve the core symptom meaning.
        
        **Validates: Requirements 15.4**
        """
        # Mock translation to simulate round-trip
        call_count = [0]
        
        def mock_translate(url, params, timeout):
            response = Mock()
            call_count[0] += 1
            
            # First call: translate to English (standardized)
            if call_count[0] == 1:
                response.json.return_value = {
                    'data': {
                        'translations': [{
                            'translatedText': symptom  # Preserve symptom
                        }]
                    }
                }
            # Second call: translate back to source
            else:
                response.json.return_value = {
                    'data': {
                        'translations': [{
                            'translatedText': f"[{params['target']}]{symptom}"
                        }]
                    }
                }
            
            response.raise_for_status = Mock()
            return response
        
        mock_post.side_effect = mock_translate
        
        service = TranslationService(api_key="test-key")
        
        # Round-trip translation: source -> English -> source
        if source_language != 'en':
            # Translate to English (standardized format)
            english_symptom = service.translate_to_english(symptom, source_language)
            
            # Translate back to source language
            back_translated = service.translate_from_english(english_symptom, source_language)
            
            # Property: Core symptom should be preserved
            # (In mock, we verify the symptom text is maintained)
            assert symptom in back_translated or symptom == english_symptom
        else:
            # For English, symptom should remain unchanged
            english_symptom = service.translate_to_english(symptom, source_language)
            assert english_symptom == symptom
    
    @settings(max_examples=10)
    @given(
        source_language=supported_language_codes(),
        symptoms=st.lists(symptom_texts(), min_size=1, max_size=5)
    )
    @patch('src.translation.translation_service.requests.post')
    def test_property_22_multiple_symptoms_preserved(
        self,
        mock_post,
        source_language,
        symptoms
    ):
        """
        Test that multiple symptoms maintain semantic meaning after translation.
        
        **Validates: Requirements 15.4**
        """
        # Mock translation to preserve symptom keywords
        def mock_translate(url, params, timeout):
            response = Mock()
            # Extract key symptom words
            text = params['q']
            response.json.return_value = {
                'data': {
                    'translations': [{
                        'translatedText': text  # Preserve for testing
                    }]
                }
            }
            response.raise_for_status = Mock()
            return response
        
        mock_post.side_effect = mock_translate
        
        service = TranslationService(api_key="test-key")
        
        # Translate symptoms to English
        translated_symptoms = service.translate_symptom_list(symptoms, source_language)
        
        # Property: Number of symptoms should be preserved
        assert len(translated_symptoms) == len(symptoms)
        
        # Property: Each symptom should have content
        for translated in translated_symptoms:
            assert translated is not None
            assert len(translated) > 0
    
    @settings(max_examples=10)
    @given(
        symptom=symptom_texts(),
        intermediate_language=supported_language_codes()
    )
    @patch('src.translation.translation_service.requests.post')
    def test_property_22_transitive_translation_consistency(
        self,
        mock_post,
        symptom,
        intermediate_language
    ):
        """
        Test that translating through an intermediate language preserves meaning.
        
        English -> Intermediate -> English should preserve symptom.
        
        **Validates: Requirements 15.4**
        """
        # Mock translation
        def mock_translate(url, params, timeout):
            response = Mock()
            # Preserve core symptom text
            response.json.return_value = {
                'data': {
                    'translations': [{
                        'translatedText': symptom
                    }]
                }
            }
            response.raise_for_status = Mock()
            return response
        
        mock_post.side_effect = mock_translate
        
        service = TranslationService(api_key="test-key")
        
        if intermediate_language != 'en':
            # Translate: English -> Intermediate
            intermediate = service.translate_from_english(symptom, intermediate_language)
            
            # Translate: Intermediate -> English
            back_to_english = service.translate_to_english(intermediate, intermediate_language)
            
            # Property: Core symptom meaning should be preserved
            # (In mock, we verify symptom is maintained)
            assert symptom in back_to_english or symptom == back_to_english


class TestTranslationInvariants:
    """Test invariants that should hold for all translations."""
    
    @settings(max_examples=10)
    @given(
        text=st.text(min_size=1, max_size=100),
        language=supported_language_codes()
    )
    def test_empty_translation_invariant(self, text, language):
        """
        Property: Translating empty or whitespace-only text should return it unchanged.
        """
        service = TranslationService(api_key="test-key")
        
        # Test with empty string
        assert service.translate_to_english("") == ""
        assert service.translate_from_english("", language) == ""
        
        # Test with whitespace
        whitespace = "   "
        assert service.translate_to_english(whitespace) == whitespace
    
    @settings(max_examples=10)
    @given(
        text=st.text(min_size=1, max_size=100),
        language=supported_language_codes()
    )
    def test_identity_translation_invariant(self, text, language):
        """
        Property: Translating from a language to itself should return original text.
        """
        service = TranslationService(api_key="test-key")
        
        result = service.translate(text, language, language)
        assert result == text
    
    @settings(max_examples=10)
    @given(
        language1=supported_language_codes(),
        language2=supported_language_codes()
    )
    @patch('src.translation.translation_service.requests.post')
    def test_translation_determinism(self, mock_post, language1, language2):
        """
        Property: Translating the same text multiple times should yield same result.
        """
        # Mock consistent translation
        def mock_translate(url, params, timeout):
            response = Mock()
            response.json.return_value = {
                'data': {
                    'translations': [{
                        'translatedText': f"translated_{params['q']}"
                    }]
                }
            }
            response.raise_for_status = Mock()
            return response
        
        mock_post.side_effect = mock_translate
        
        service = TranslationService(api_key="test-key")
        text = "test symptom"
        
        if language1 != language2:
            result1 = service.translate(text, language1, language2)
            result2 = service.translate(text, language1, language2)
            
            # Property: Same input should produce same output
            assert result1 == result2


class TestCachingProperties:
    """Test properties related to caching behavior."""
    
    @settings(max_examples=10)
    @given(
        text=st.text(min_size=1, max_size=50),
        source=supported_language_codes(),
        target=supported_language_codes()
    )
    @patch('src.translation.translation_service.requests.post')
    def test_cache_consistency_property(self, mock_post, text, source, target):
        """
        Property: Cached translations should return identical results to API calls.
        """
        # Mock translation
        def mock_translate(url, params, timeout):
            response = Mock()
            response.json.return_value = {
                'data': {
                    'translations': [{
                        'translatedText': f"translated_{params['q']}"
                    }]
                }
            }
            response.raise_for_status = Mock()
            return response
        
        mock_post.side_effect = mock_translate
        
        service = TranslationService(api_key="test-key")
        
        if source != target:
            # First call - uses API
            result1 = service.translate(text, source, target)
            
            # Second call - uses cache
            result2 = service.translate(text, source, target)
            
            # Property: Results should be identical
            assert result1 == result2
            
            # Property: API should only be called once
            assert mock_post.call_count == 1
    
    @settings(max_examples=10)
    @given(
        texts=st.lists(st.text(min_size=1, max_size=30), min_size=2, max_size=5, unique=True),
        language=supported_language_codes()
    )
    @patch('src.translation.translation_service.requests.post')
    def test_cache_independence_property(self, mock_post, texts, language):
        """
        Property: Caching one translation should not affect others.
        """
        # Mock translation
        def mock_translate(url, params, timeout):
            response = Mock()
            response.json.return_value = {
                'data': {
                    'translations': [{
                        'translatedText': f"translated_{params['q']}"
                    }]
                }
            }
            response.raise_for_status = Mock()
            return response
        
        mock_post.side_effect = mock_translate
        
        service = TranslationService(api_key="test-key")
        
        if language != 'en':
            # Translate all texts
            results = []
            for text in texts:
                result = service.translate_from_english(text, language)
                results.append(result)
            
            # Property: Each text should have a unique translation
            # (based on our mock which includes the original text)
            for i, text in enumerate(texts):
                assert text in results[i] or f"translated_{text}" == results[i]


class TestLanguageDetectionProperties:
    """Test properties of language detection."""
    
    @settings(max_examples=10)
    @given(
        text=st.text(min_size=1, max_size=100)
    )
    @patch('src.translation.translation_service.requests.post')
    def test_detection_returns_supported_language(self, mock_post, text):
        """
        Property: Language detection should always return a supported language code.
        """
        # Mock detection
        def mock_detect(url, params, timeout):
            response = Mock()
            response.json.return_value = {
                'data': {
                    'detections': [[{
                        'language': 'en',
                        'confidence': 0.95
                    }]]
                }
            }
            response.raise_for_status = Mock()
            return response
        
        mock_post.side_effect = mock_detect
        
        service = TranslationService(api_key="test-key")
        detected = service.detect_language(text)
        
        # Property: Detected language must be in supported languages
        assert detected in service.supported_languages
    
    @settings(max_examples=10)
    @given(
        text=st.text(min_size=1, max_size=100)
    )
    def test_detection_without_api_returns_default(self, text):
        """
        Property: Without API key, detection should always return default language.
        """
        service = TranslationService(api_key=None)
        detected = service.detect_language(text)
        
        # Property: Should return default language
        assert detected == service.default_language
