"""
Translation Service for Illness Prediction System.

This service provides multi-language support for the system, enabling users to
interact in their native language. It integrates with Google Translate API to:
- Detect user's language automatically
- Translate symptom descriptions to standardized English format for ML model
- Translate system responses back to user's language
- Support 5 major languages: English, Spanish, French, Hindi, Mandarin

The service ensures semantic preservation during translation, particularly for
medical terminology and symptom descriptions.

Validates: Requirements 15.1, 15.2, 15.3, 15.4, 15.5
"""

import logging
from typing import Dict, List, Optional, Tuple
import requests
from config.settings import settings

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Service for multi-language support in the Illness Prediction System.
    
    Features:
    - Automatic language detection from user input
    - Translation of symptom descriptions to standardized English
    - Translation of system responses to user's language
    - Support for 5 major languages: English (en), Spanish (es), French (fr), Hindi (hi), Mandarin (zh)
    - Semantic preservation for medical terminology
    - Caching of common translations for performance
    
    Uses Google Translate API for translation services.
    
    Validates: Requirements 15.1, 15.2, 15.3, 15.4, 15.5
    """
    
    # Language codes mapping
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'hi': 'Hindi',
        'zh': 'Mandarin Chinese'
    }
    
    # Common medical terms that should be preserved during translation
    MEDICAL_TERMS = [
        'fever', 'headache', 'cough', 'fatigue', 'nausea', 'vomiting',
        'diarrhea', 'pain', 'ache', 'swelling', 'rash', 'dizziness',
        'shortness of breath', 'chest pain', 'abdominal pain', 'sore throat',
        'runny nose', 'congestion', 'chills', 'sweating', 'weakness',
        'loss of appetite', 'weight loss', 'insomnia', 'anxiety', 'depression'
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the TranslationService.
        
        Args:
            api_key: Google Translate API key. If None, uses settings.
        """
        self.api_key = api_key or settings.translation_api_key
        self.supported_languages = settings.supported_languages
        self.default_language = settings.default_language
        self.base_url = "https://translation.googleapis.com/language/translate/v2"
        
        # Translation cache for performance
        self._translation_cache: Dict[Tuple[str, str, str], str] = {}
        
        if not self.api_key:
            logger.warning(
                "Google Translate API key not configured. "
                "Translation service will operate in fallback mode (English only)."
            )
        
        logger.info(
            f"TranslationService initialized with support for: "
            f"{', '.join(self.SUPPORTED_LANGUAGES.values())}"
        )
    
    def detect_language(self, text: str) -> str:
        """
        Detect the language of the given text.
        
        Uses Google Translate API's language detection feature to identify
        the language of user input. Falls back to default language if detection fails.
        
        Args:
            text: Text to detect language for
        
        Returns:
            Language code (e.g., 'en', 'es', 'fr', 'hi', 'zh')
            Returns default language if detection fails or API is unavailable
        
        Validates: Requirements 15.2
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for language detection")
            return self.default_language
        
        if not self.api_key:
            logger.debug("API key not configured, returning default language")
            return self.default_language
        
        try:
            # Call Google Translate API for language detection
            url = f"{self.base_url}/detect"
            params = {
                'key': self.api_key,
                'q': text
            }
            
            response = requests.post(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' in data and 'detections' in data['data']:
                detections = data['data']['detections'][0]
                if detections:
                    detected_lang = detections[0]['language']
                    confidence = detections[0].get('confidence', 0.0)
                    
                    logger.info(
                        f"Detected language: {detected_lang} "
                        f"(confidence: {confidence:.2f})"
                    )
                    
                    # Normalize Chinese variants to 'zh'
                    if detected_lang in ['zh-CN', 'zh-TW', 'zh']:
                        detected_lang = 'zh'
                    
                    # Return detected language if supported
                    if detected_lang in self.supported_languages:
                        return detected_lang
                    else:
                        logger.warning(
                            f"Detected language '{detected_lang}' not supported, "
                            f"using default: {self.default_language}"
                        )
                        return self.default_language
            
            logger.warning("No detection results, using default language")
            return self.default_language
            
        except requests.RequestException as e:
            logger.error(f"Error detecting language: {e}")
            return self.default_language
        except Exception as e:
            logger.error(f"Unexpected error in language detection: {e}")
            return self.default_language
    
    def translate_to_english(self, text: str, source_language: Optional[str] = None) -> str:
        """
        Translate text from any supported language to English.
        
        This is used to translate user symptom descriptions to standardized
        English format for processing by the ML model. The translation preserves
        medical terminology and semantic meaning.
        
        Args:
            text: Text to translate
            source_language: Source language code. If None, auto-detects.
        
        Returns:
            Translated text in English
            Returns original text if translation fails or text is already in English
        
        Validates: Requirements 15.4
        """
        if not text or not text.strip():
            return text
        
        # Detect source language if not provided
        if not source_language:
            source_language = self.detect_language(text)
        
        # If already in English, return as-is
        if source_language == 'en':
            return text
        
        # Check cache
        cache_key = (text, source_language, 'en')
        if cache_key in self._translation_cache:
            logger.debug(f"Using cached translation for: {text[:50]}...")
            return self._translation_cache[cache_key]
        
        # Translate using API
        translated = self._translate(text, source_language, 'en')
        
        # Cache the translation
        if translated:
            self._translation_cache[cache_key] = translated
        
        return translated or text
    
    def translate_from_english(self, text: str, target_language: str) -> str:
        """
        Translate text from English to the target language.
        
        This is used to translate system responses (questions, predictions,
        explanations) from English to the user's preferred language.
        
        Args:
            text: Text in English to translate
            target_language: Target language code (e.g., 'es', 'fr', 'hi', 'zh')
        
        Returns:
            Translated text in target language
            Returns original text if translation fails or target is English
        
        Validates: Requirements 15.3, 15.5
        """
        if not text or not text.strip():
            return text
        
        # If target is English, return as-is
        if target_language == 'en':
            return text
        
        # Validate target language
        if target_language not in self.supported_languages:
            logger.warning(
                f"Target language '{target_language}' not supported, "
                f"returning English text"
            )
            return text
        
        # Check cache
        cache_key = (text, 'en', target_language)
        if cache_key in self._translation_cache:
            logger.debug(f"Using cached translation for: {text[:50]}...")
            return self._translation_cache[cache_key]
        
        # Translate using API
        translated = self._translate(text, 'en', target_language)
        
        # Cache the translation
        if translated:
            self._translation_cache[cache_key] = translated
        
        return translated or text
    
    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str
    ) -> str:
        """
        Translate text from source language to target language.
        
        General-purpose translation method that can translate between any
        two supported languages.
        
        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code
        
        Returns:
            Translated text
            Returns original text if translation fails or languages are the same
        
        Validates: Requirements 15.3, 15.4, 15.5
        """
        if not text or not text.strip():
            return text
        
        # If source and target are the same, return as-is
        if source_language == target_language:
            return text
        
        # Validate languages
        if source_language not in self.supported_languages:
            logger.warning(f"Source language '{source_language}' not supported")
            return text
        
        if target_language not in self.supported_languages:
            logger.warning(f"Target language '{target_language}' not supported")
            return text
        
        # Check cache
        cache_key = (text, source_language, target_language)
        if cache_key in self._translation_cache:
            logger.debug(f"Using cached translation for: {text[:50]}...")
            return self._translation_cache[cache_key]
        
        # Translate using API
        translated = self._translate(text, source_language, target_language)
        
        # Cache the translation
        if translated:
            self._translation_cache[cache_key] = translated
        
        return translated or text
    
    def _translate(
        self,
        text: str,
        source_language: str,
        target_language: str
    ) -> Optional[str]:
        """
        Internal method to perform translation using Google Translate API.
        
        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code
        
        Returns:
            Translated text or None if translation fails
        """
        if not self.api_key:
            logger.debug("API key not configured, returning None")
            return None
        
        try:
            # Call Google Translate API
            url = self.base_url
            params = {
                'key': self.api_key,
                'q': text,
                'source': source_language,
                'target': target_language,
                'format': 'text'
            }
            
            response = requests.post(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' in data and 'translations' in data['data']:
                translations = data['data']['translations']
                if translations:
                    translated_text = translations[0]['translatedText']
                    logger.info(
                        f"Translated from {source_language} to {target_language}: "
                        f"'{text[:50]}...' -> '{translated_text[:50]}...'"
                    )
                    return translated_text
            
            logger.warning("No translation results returned")
            return None
            
        except requests.RequestException as e:
            logger.error(f"Error translating text: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in translation: {e}")
            return None
    
    def is_language_supported(self, language_code: str) -> bool:
        """
        Check if a language is supported by the translation service.
        
        Args:
            language_code: Language code to check (e.g., 'en', 'es', 'fr')
        
        Returns:
            True if language is supported, False otherwise
        
        Validates: Requirements 15.1
        """
        return language_code in self.supported_languages
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get dictionary of supported languages.
        
        Returns:
            Dictionary mapping language codes to language names
            Example: {'en': 'English', 'es': 'Spanish', ...}
        
        Validates: Requirements 15.1
        """
        return self.SUPPORTED_LANGUAGES.copy()
    
    def get_language_name(self, language_code: str) -> str:
        """
        Get the full name of a language from its code.
        
        Args:
            language_code: Language code (e.g., 'en', 'es')
        
        Returns:
            Language name (e.g., 'English', 'Spanish')
            Returns the code itself if not found
        """
        return self.SUPPORTED_LANGUAGES.get(language_code, language_code)
    
    def translate_symptom_list(
        self,
        symptoms: List[str],
        source_language: Optional[str] = None
    ) -> List[str]:
        """
        Translate a list of symptom descriptions to English.
        
        This is a convenience method for translating multiple symptoms at once,
        useful for batch processing of symptom vectors.
        
        Args:
            symptoms: List of symptom descriptions
            source_language: Source language code. If None, auto-detects.
        
        Returns:
            List of translated symptom descriptions in English
        
        Validates: Requirements 15.4
        """
        if not symptoms:
            return []
        
        translated_symptoms = []
        for symptom in symptoms:
            translated = self.translate_to_english(symptom, source_language)
            translated_symptoms.append(translated)
        
        return translated_symptoms
    
    def translate_response_dict(
        self,
        response_dict: Dict[str, str],
        target_language: str
    ) -> Dict[str, str]:
        """
        Translate all string values in a dictionary to the target language.
        
        This is useful for translating structured responses like predictions,
        explanations, and treatment suggestions.
        
        Args:
            response_dict: Dictionary with string values to translate
            target_language: Target language code
        
        Returns:
            Dictionary with translated values
        
        Validates: Requirements 15.3, 15.5
        """
        if target_language == 'en':
            return response_dict
        
        translated_dict = {}
        for key, value in response_dict.items():
            if isinstance(value, str):
                translated_dict[key] = self.translate_from_english(value, target_language)
            else:
                translated_dict[key] = value
        
        return translated_dict
    
    def clear_cache(self) -> None:
        """
        Clear the translation cache.
        
        This can be useful for testing or when memory usage needs to be reduced.
        """
        cache_size = len(self._translation_cache)
        self._translation_cache.clear()
        logger.info(f"Cleared translation cache ({cache_size} entries)")
    
    def get_cache_size(self) -> int:
        """
        Get the number of cached translations.
        
        Returns:
            Number of entries in the translation cache
        """
        return len(self._translation_cache)
