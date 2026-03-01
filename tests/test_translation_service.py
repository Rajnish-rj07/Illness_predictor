"""
Unit tests for TranslationService.

Tests the translation service functionality including:
- Language detection
- Translation to/from English
- Support for 5 languages (English, Spanish, French, Hindi, Mandarin)
- Caching behavior
- Error handling

Validates: Requirements 15.1, 15.2, 15.3, 15.4, 15.5
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.translation.translation_service import TranslationService


class TestTranslationServiceInitialization:
    """Test TranslationService initialization."""
    
    def test_initialization_with_api_key(self):
        """Test service initializes with API key."""
        service = TranslationService(api_key="test-api-key")
        assert service.api_key == "test-api-key"
        assert len(service.supported_languages) == 5
        assert service.default_language == "en"
    
    def test_initialization_without_api_key(self):
        """Test service initializes without API key (fallback mode)."""
        with patch('src.translation.translation_service.settings') as mock_settings:
            mock_settings.translation_api_key = None
            mock_settings.supported_languages = ["en", "es", "fr", "hi", "zh"]
            mock_settings.default_language = "en"
            
            service = TranslationService()
            assert service.api_key is None
    
    def test_supported_languages(self):
        """Test that all 5 required languages are supported."""
        service = TranslationService(api_key="test-key")
        supported = service.get_supported_languages()
        
        assert 'en' in supported  # English
        assert 'es' in supported  # Spanish
        assert 'fr' in supported  # French
        assert 'hi' in supported  # Hindi
        assert 'zh' in supported  # Mandarin
        assert len(supported) == 5


class TestLanguageDetection:
    """Test language detection functionality."""
    
    @patch('src.translation.translation_service.requests.post')
    def test_detect_english(self, mock_post):
        """Test detecting English text."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {
                'detections': [[{
                    'language': 'en',
                    'confidence': 0.99
                }]]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        service = TranslationService(api_key="test-key")
        detected = service.detect_language("I have a headache")
        
        assert detected == 'en'
    
    @patch('src.translation.translation_service.requests.post')
    def test_detect_spanish(self, mock_post):
        """Test detecting Spanish text."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {
                'detections': [[{
                    'language': 'es',
                    'confidence': 0.95
                }]]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        service = TranslationService(api_key="test-key")
        detected = service.detect_language("Tengo dolor de cabeza")
        
        assert detected == 'es'
    
    @patch('src.translation.translation_service.requests.post')
    def test_detect_french(self, mock_post):
        """Test detecting French text."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {
                'detections': [[{
                    'language': 'fr',
                    'confidence': 0.97
                }]]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        service = TranslationService(api_key="test-key")
        detected = service.detect_language("J'ai mal à la tête")
        
        assert detected == 'fr'
    
    def test_detect_empty_text(self):
        """Test language detection with empty text returns default."""
        service = TranslationService(api_key="test-key")
        detected = service.detect_language("")
        
        assert detected == service.default_language
    
    @patch('src.translation.translation_service.requests.post')
    def test_detect_unsupported_language(self, mock_post):
        """Test detecting unsupported language returns default."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {
                'detections': [[{
                    'language': 'de',  # German - not supported
                    'confidence': 0.95
                }]]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        service = TranslationService(api_key="test-key")
        detected = service.detect_language("Ich habe Kopfschmerzen")
        
        assert detected == service.default_language
    
    def test_detect_without_api_key(self):
        """Test language detection without API key returns default."""
        service = TranslationService(api_key=None)
        detected = service.detect_language("Some text")
        
        assert detected == service.default_language
    
    @patch('src.translation.translation_service.requests.post')
    def test_detect_api_error(self, mock_post):
        """Test language detection handles API errors gracefully."""
        mock_post.side_effect = Exception("API Error")
        
        service = TranslationService(api_key="test-key")
        detected = service.detect_language("Some text")
        
        assert detected == service.default_language


class TestTranslationToEnglish:
    """Test translation to English functionality."""
    
    @patch('src.translation.translation_service.requests.post')
    def test_translate_spanish_to_english(self, mock_post):
        """Test translating Spanish symptom to English."""
        # Mock detection response
        detect_response = Mock()
        detect_response.json.return_value = {
            'data': {
                'detections': [[{
                    'language': 'es',
                    'confidence': 0.95
                }]]
            }
        }
        detect_response.raise_for_status = Mock()
        
        # Mock translation response
        translate_response = Mock()
        translate_response.json.return_value = {
            'data': {
                'translations': [{
                    'translatedText': 'I have a headache'
                }]
            }
        }
        translate_response.raise_for_status = Mock()
        
        mock_post.side_effect = [detect_response, translate_response]
        
        service = TranslationService(api_key="test-key")
        translated = service.translate_to_english("Tengo dolor de cabeza")
        
        assert translated == 'I have a headache'
    
    def test_translate_english_to_english(self):
        """Test translating English text returns original."""
        service = TranslationService(api_key="test-key")
        text = "I have a headache"
        translated = service.translate_to_english(text, source_language='en')
        
        assert translated == text
    
    @patch('src.translation.translation_service.requests.post')
    def test_translate_french_to_english(self, mock_post):
        """Test translating French symptom to English."""
        translate_response = Mock()
        translate_response.json.return_value = {
            'data': {
                'translations': [{
                    'translatedText': 'I have a fever'
                }]
            }
        }
        translate_response.raise_for_status = Mock()
        mock_post.return_value = translate_response
        
        service = TranslationService(api_key="test-key")
        translated = service.translate_to_english("J'ai de la fièvre", source_language='fr')
        
        assert translated == 'I have a fever'
    
    def test_translate_empty_text(self):
        """Test translating empty text returns empty."""
        service = TranslationService(api_key="test-key")
        translated = service.translate_to_english("")
        
        assert translated == ""
    
    @patch('src.translation.translation_service.requests.post')
    def test_translate_api_error_returns_original(self, mock_post):
        """Test translation API error returns original text."""
        mock_post.side_effect = Exception("API Error")
        
        service = TranslationService(api_key="test-key")
        text = "Tengo fiebre"
        translated = service.translate_to_english(text, source_language='es')
        
        assert translated == text


class TestTranslationFromEnglish:
    """Test translation from English functionality."""
    
    @patch('src.translation.translation_service.requests.post')
    def test_translate_english_to_spanish(self, mock_post):
        """Test translating English response to Spanish."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {
                'translations': [{
                    'translatedText': '¿Tiene fiebre?'
                }]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        service = TranslationService(api_key="test-key")
        translated = service.translate_from_english("Do you have a fever?", 'es')
        
        assert translated == '¿Tiene fiebre?'
    
    @patch('src.translation.translation_service.requests.post')
    def test_translate_english_to_french(self, mock_post):
        """Test translating English response to French."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {
                'translations': [{
                    'translatedText': 'Avez-vous de la fièvre?'
                }]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        service = TranslationService(api_key="test-key")
        translated = service.translate_from_english("Do you have a fever?", 'fr')
        
        assert translated == 'Avez-vous de la fièvre?'
    
    @patch('src.translation.translation_service.requests.post')
    def test_translate_english_to_hindi(self, mock_post):
        """Test translating English response to Hindi."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {
                'translations': [{
                    'translatedText': 'क्या आपको बुखार है?'
                }]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        service = TranslationService(api_key="test-key")
        translated = service.translate_from_english("Do you have a fever?", 'hi')
        
        assert translated == 'क्या आपको बुखार है?'
    
    @patch('src.translation.translation_service.requests.post')
    def test_translate_english_to_mandarin(self, mock_post):
        """Test translating English response to Mandarin."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {
                'translations': [{
                    'translatedText': '你发烧吗？'
                }]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        service = TranslationService(api_key="test-key")
        translated = service.translate_from_english("Do you have a fever?", 'zh')
        
        assert translated == '你发烧吗？'
    
    def test_translate_to_english_returns_original(self):
        """Test translating to English returns original text."""
        service = TranslationService(api_key="test-key")
        text = "Do you have a fever?"
        translated = service.translate_from_english(text, 'en')
        
        assert translated == text
    
    def test_translate_to_unsupported_language(self):
        """Test translating to unsupported language returns original."""
        service = TranslationService(api_key="test-key")
        text = "Do you have a fever?"
        translated = service.translate_from_english(text, 'de')  # German not supported
        
        assert translated == text


class TestGeneralTranslation:
    """Test general translation functionality."""
    
    @patch('src.translation.translation_service.requests.post')
    def test_translate_between_languages(self, mock_post):
        """Test translating between two non-English languages."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {
                'translations': [{
                    'translatedText': 'J\'ai mal à la tête'
                }]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        service = TranslationService(api_key="test-key")
        translated = service.translate("Tengo dolor de cabeza", 'es', 'fr')
        
        assert translated == 'J\'ai mal à la tête'
    
    def test_translate_same_language(self):
        """Test translating to same language returns original."""
        service = TranslationService(api_key="test-key")
        text = "I have a headache"
        translated = service.translate(text, 'en', 'en')
        
        assert translated == text
    
    def test_translate_unsupported_source(self):
        """Test translating from unsupported language returns original."""
        service = TranslationService(api_key="test-key")
        text = "Ich habe Kopfschmerzen"
        translated = service.translate(text, 'de', 'en')  # German not supported
        
        assert translated == text
    
    def test_translate_unsupported_target(self):
        """Test translating to unsupported language returns original."""
        service = TranslationService(api_key="test-key")
        text = "I have a headache"
        translated = service.translate(text, 'en', 'de')  # German not supported
        
        assert translated == text


class TestCaching:
    """Test translation caching functionality."""
    
    @patch('src.translation.translation_service.requests.post')
    def test_caching_reduces_api_calls(self, mock_post):
        """Test that caching reduces API calls for repeated translations."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {
                'translations': [{
                    'translatedText': 'I have a headache'
                }]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        service = TranslationService(api_key="test-key")
        
        # First translation - should call API
        text = "Tengo dolor de cabeza"
        result1 = service.translate_to_english(text, source_language='es')
        
        # Second translation - should use cache
        result2 = service.translate_to_english(text, source_language='es')
        
        assert result1 == result2
        assert mock_post.call_count == 1  # Only called once
    
    def test_cache_size(self):
        """Test getting cache size."""
        service = TranslationService(api_key="test-key")
        initial_size = service.get_cache_size()
        
        # Add to cache manually
        service._translation_cache[("test", "en", "es")] = "prueba"
        
        assert service.get_cache_size() == initial_size + 1
    
    def test_clear_cache(self):
        """Test clearing the cache."""
        service = TranslationService(api_key="test-key")
        
        # Add to cache
        service._translation_cache[("test", "en", "es")] = "prueba"
        assert service.get_cache_size() > 0
        
        # Clear cache
        service.clear_cache()
        assert service.get_cache_size() == 0


class TestUtilityMethods:
    """Test utility methods."""
    
    def test_is_language_supported(self):
        """Test checking if language is supported."""
        service = TranslationService(api_key="test-key")
        
        assert service.is_language_supported('en') is True
        assert service.is_language_supported('es') is True
        assert service.is_language_supported('fr') is True
        assert service.is_language_supported('hi') is True
        assert service.is_language_supported('zh') is True
        assert service.is_language_supported('de') is False
    
    def test_get_language_name(self):
        """Test getting language name from code."""
        service = TranslationService(api_key="test-key")
        
        assert service.get_language_name('en') == 'English'
        assert service.get_language_name('es') == 'Spanish'
        assert service.get_language_name('fr') == 'French'
        assert service.get_language_name('hi') == 'Hindi'
        assert service.get_language_name('zh') == 'Mandarin Chinese'
        assert service.get_language_name('de') == 'de'  # Unknown returns code
    
    @patch('src.translation.translation_service.requests.post')
    def test_translate_symptom_list(self, mock_post):
        """Test translating a list of symptoms."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {
                'translations': [{
                    'translatedText': 'headache'
                }]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        service = TranslationService(api_key="test-key")
        symptoms = ["dolor de cabeza", "fiebre", "tos"]
        translated = service.translate_symptom_list(symptoms, source_language='es')
        
        assert len(translated) == 3
        assert all(isinstance(s, str) for s in translated)
    
    def test_translate_empty_symptom_list(self):
        """Test translating empty symptom list."""
        service = TranslationService(api_key="test-key")
        translated = service.translate_symptom_list([])
        
        assert translated == []
    
    @patch('src.translation.translation_service.requests.post')
    def test_translate_response_dict(self, mock_post):
        """Test translating a response dictionary."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': {
                'translations': [{
                    'translatedText': 'Gripe'
                }]
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        service = TranslationService(api_key="test-key")
        response = {
            'illness': 'Influenza',
            'confidence': 0.85,
            'message': 'You may have the flu'
        }
        
        translated = service.translate_response_dict(response, 'es')
        
        # String values should be translated, numbers preserved
        assert isinstance(translated['illness'], str)
        assert translated['confidence'] == 0.85
    
    def test_translate_response_dict_to_english(self):
        """Test translating response dict to English returns original."""
        service = TranslationService(api_key="test-key")
        response = {'illness': 'Influenza', 'confidence': 0.85}
        
        translated = service.translate_response_dict(response, 'en')
        
        assert translated == response


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_none_text(self):
        """Test handling None as text input."""
        service = TranslationService(api_key="test-key")
        
        # Should handle None gracefully
        assert service.translate_to_english(None) is None
        assert service.translate_from_english(None, 'es') is None
    
    def test_whitespace_only_text(self):
        """Test handling whitespace-only text."""
        service = TranslationService(api_key="test-key")
        
        result = service.translate_to_english("   ")
        assert result == "   "
    
    @patch('src.translation.translation_service.requests.post')
    def test_api_timeout(self, mock_post):
        """Test handling API timeout."""
        mock_post.side_effect = Exception("Timeout")
        
        service = TranslationService(api_key="test-key")
        text = "Tengo fiebre"
        result = service.translate_to_english(text, source_language='es')
        
        # Should return original text on error
        assert result == text
    
    @patch('src.translation.translation_service.requests.post')
    def test_malformed_api_response(self, mock_post):
        """Test handling malformed API response."""
        mock_response = Mock()
        mock_response.json.return_value = {'error': 'Invalid request'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        service = TranslationService(api_key="test-key")
        text = "Tengo fiebre"
        result = service.translate_to_english(text, source_language='es')
        
        # Should return original text when translation fails
        assert result == text
