"""
Unit tests for PrivacyService.

Validates: Requirements 9.1, 9.2, 9.3, 9.5
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from src.security.privacy_service import PrivacyService


class TestEncryption:
    """Test encryption and decryption functionality."""
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test that data can be encrypted and decrypted."""
        service = PrivacyService()
        
        original = "sensitive health data"
        encrypted = service.encrypt_data(original)
        decrypted = service.decrypt_data(encrypted)
        
        assert decrypted == original
        assert encrypted != original
    
    def test_encrypt_empty_string(self):
        """Test encrypting empty string."""
        service = PrivacyService()
        
        encrypted = service.encrypt_data("")
        assert encrypted == ""
    
    def test_decrypt_empty_string(self):
        """Test decrypting empty string."""
        service = PrivacyService()
        
        decrypted = service.decrypt_data("")
        assert decrypted == ""
    
    def test_encrypt_symptom_vector(self):
        """Test encrypting symptom vector."""
        service = PrivacyService()
        
        symptom_vector = {
            'fever': True,
            'cough': True,
            'headache': False
        }
        
        encrypted = service.encrypt_symptom_vector(symptom_vector)
        decrypted = service.decrypt_symptom_vector(encrypted)
        
        assert decrypted == symptom_vector


class TestPIIDetection:
    """Test PII detection and removal."""
    
    def test_sanitize_email(self):
        """Test that emails are detected and removed."""
        service = PrivacyService()
        
        text = "My email is john.doe@example.com"
        result = service.sanitize_input(text)
        
        assert result['has_pii'] is True
        assert 'email' in result['pii_detected']
        assert 'john.doe@example.com' not in result['sanitized_text']
    
    def test_sanitize_phone(self):
        """Test that phone numbers are detected and removed."""
        service = PrivacyService()
        
        text = "Call me at 555-123-4567"
        result = service.sanitize_input(text)
        
        assert result['has_pii'] is True
        assert 'phone' in result['pii_detected']
        assert '555-123-4567' not in result['sanitized_text']
    
    def test_sanitize_no_pii(self):
        """Test text without PII."""
        service = PrivacyService()
        
        text = "I have a fever and cough"
        result = service.sanitize_input(text)
        
        assert result['has_pii'] is False
        assert result['pii_detected'] == []
        assert result['sanitized_text'] == text
    
    def test_validate_no_pii_clean_data(self):
        """Test validation of clean data."""
        service = PrivacyService()
        
        data = {
            'symptoms': ['fever', 'cough'],
            'duration': '3 days'
        }
        
        assert service.validate_no_pii(data) is True
    
    def test_validate_no_pii_with_email(self):
        """Test validation detects email in data."""
        service = PrivacyService()
        
        data = {
            'symptoms': ['fever'],
            'contact': 'john@example.com'
        }
        
        assert service.validate_no_pii(data) is False
    
    def test_validate_no_pii_nested_dict(self):
        """Test validation of nested dictionaries."""
        service = PrivacyService()
        
        data = {
            'symptoms': ['fever'],
            'metadata': {
                'notes': 'Contact at 555-123-4567'
            }
        }
        
        assert service.validate_no_pii(data) is False
    
    def test_validate_no_pii_list_of_strings(self):
        """Test validation of lists containing PII."""
        service = PrivacyService()
        
        data = {
            'messages': [
                'I have a fever',
                'My email is test@example.com'
            ]
        }
        
        assert service.validate_no_pii(data) is False


class TestSessionAnonymization:
    """Test session anonymization functionality."""
    
    def test_anonymize_session_removes_user_id(self):
        """Test that user_id is removed and hashed."""
        service = PrivacyService()
        
        session_data = {
            'session_id': 'sess123',
            'user_id': 'user456',
            'symptoms': ['fever']
        }
        
        anonymized = service.anonymize_session(session_data)
        
        assert 'user_id' not in anonymized
        assert 'user_id_hash' in anonymized
        assert anonymized['user_id_hash'] != 'user456'
    
    def test_anonymize_session_removes_phone(self):
        """Test that phone number is removed and hashed."""
        service = PrivacyService()
        
        session_data = {
            'session_id': 'sess123',
            'phone_number': '+1234567890'
        }
        
        anonymized = service.anonymize_session(session_data)
        
        assert 'phone_number' not in anonymized
        assert 'phone_number_hash' in anonymized
    
    def test_anonymize_session_removes_email(self):
        """Test that email is removed and hashed."""
        service = PrivacyService()
        
        session_data = {
            'session_id': 'sess123',
            'email': 'user@example.com'
        }
        
        anonymized = service.anonymize_session(session_data)
        
        assert 'email' not in anonymized
        assert 'email_hash' in anonymized
    
    def test_anonymize_session_adds_timestamp(self):
        """Test that anonymization timestamp is added."""
        service = PrivacyService()
        
        session_data = {
            'session_id': 'sess123'
        }
        
        anonymized = service.anonymize_session(session_data)
        
        assert 'anonymized_at' in anonymized
        # Verify it's a valid ISO timestamp
        datetime.fromisoformat(anonymized['anonymized_at'])
    
    def test_anonymize_session_messages(self):
        """Test that messages are anonymized."""
        service = PrivacyService()
        
        session_data = {
            'session_id': 'sess123',
            'messages': [
                {
                    'content': 'I have a fever',
                    'sender_id': 'user123'
                },
                {
                    'content': 'My email is test@example.com',
                    'sender_id': 'user123'
                }
            ]
        }
        
        anonymized = service.anonymize_session(session_data)
        
        # Check messages are anonymized
        for msg in anonymized['messages']:
            assert 'sender_id' not in msg
            assert 'sender_id_hash' in msg
            # PII should be removed from content
            assert 'test@example.com' not in msg['content']
    
    def test_hash_identifier_consistency(self):
        """Test that same identifier produces same hash."""
        service = PrivacyService()
        
        identifier = "user123"
        hash1 = service._hash_identifier(identifier)
        hash2 = service._hash_identifier(identifier)
        
        assert hash1 == hash2
    
    def test_hash_identifier_uniqueness(self):
        """Test that different identifiers produce different hashes."""
        service = PrivacyService()
        
        hash1 = service._hash_identifier("user123")
        hash2 = service._hash_identifier("user456")
        
        assert hash1 != hash2


class TestDataDeletion:
    """Test data deletion functionality."""
    
    def test_delete_session_data_success(self):
        """Test successful session data deletion."""
        service = PrivacyService()
        
        # Mock database client
        mock_db = Mock()
        mock_db.delete = Mock(return_value=True)
        
        result = service.delete_session_data('sess123', mock_db)
        
        assert result is True
        # Verify all tables were called
        assert mock_db.delete.call_count == 4
    
    def test_delete_session_data_failure(self):
        """Test handling of deletion failure."""
        service = PrivacyService()
        
        # Mock database client that raises exception
        mock_db = Mock()
        mock_db.delete = Mock(side_effect=Exception("Database error"))
        
        result = service.delete_session_data('sess123', mock_db)
        
        assert result is False
    
    def test_delete_session_data_calls_all_tables(self):
        """Test that deletion targets all relevant tables."""
        service = PrivacyService()
        
        mock_db = Mock()
        mock_db.delete = Mock(return_value=True)
        
        service.delete_session_data('sess123', mock_db)
        
        # Verify calls to delete from all tables
        calls = [call[0] for call in mock_db.delete.call_args_list]
        table_names = [call[0] for call in calls]
        
        assert 'sessions' in table_names
        assert 'predictions' in table_names
        assert 'conversation_logs' in table_names
        assert 'feedback' in table_names


class TestIntegration:
    """Integration tests for privacy service."""
    
    def test_full_privacy_workflow(self):
        """Test complete privacy workflow."""
        service = PrivacyService()
        
        # 1. Sanitize user input
        user_input = "I have fever and my email is test@example.com"
        sanitized = service.sanitize_input(user_input)
        
        assert sanitized['has_pii'] is True
        assert 'test@example.com' not in sanitized['sanitized_text']
        
        # 2. Encrypt symptom data
        symptom_vector = {'fever': True, 'cough': False}
        encrypted = service.encrypt_symptom_vector(symptom_vector)
        
        assert encrypted != str(symptom_vector)
        
        # 3. Decrypt for processing
        decrypted = service.decrypt_symptom_vector(encrypted)
        
        assert decrypted == symptom_vector
        
        # 4. Anonymize session
        session_data = {
            'session_id': 'sess123',
            'user_id': 'user456',
            'symptoms': symptom_vector
        }
        
        anonymized = service.anonymize_session(session_data)
        
        assert 'user_id' not in anonymized
        assert 'user_id_hash' in anonymized
        assert 'anonymized_at' in anonymized
    
    def test_encryption_with_special_characters(self):
        """Test encryption handles special characters."""
        service = PrivacyService()
        
        data = "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
        encrypted = service.encrypt_data(data)
        decrypted = service.decrypt_data(encrypted)
        
        assert decrypted == data
    
    def test_encryption_with_unicode(self):
        """Test encryption handles unicode characters."""
        service = PrivacyService()
        
        data = "Unicode: 你好 مرحبا नमस्ते"
        encrypted = service.encrypt_data(data)
        decrypted = service.decrypt_data(encrypted)
        
        assert decrypted == data
