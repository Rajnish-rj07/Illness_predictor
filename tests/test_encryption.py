"""
Tests for encryption and anonymization utilities.

Validates: Requirements 9.1, 9.2, 9.3
"""

import pytest
from hypothesis import given, strategies as st
from src.utils.encryption import (
    EncryptionManager,
    detect_pii,
    remove_pii,
    anonymize_user_id,
    anonymize_conversation_log,
    hash_sensitive_field,
    generate_encryption_key,
    encrypt_symptom_data,
    decrypt_symptom_data,
)


class TestEncryptionManager:
    """Test suite for EncryptionManager class."""
    
    def test_encryption_manager_initialization(self):
        """Test that EncryptionManager can be initialized."""
        manager = EncryptionManager()
        assert manager is not None
    
    def test_encryption_manager_with_custom_key(self):
        """Test EncryptionManager with a custom key."""
        key = generate_encryption_key()
        manager = EncryptionManager(master_key=key)
        assert manager is not None
    
    def test_encrypt_decrypt_simple_string(self):
        """Test basic encryption and decryption."""
        manager = EncryptionManager()
        original = "Hello, World!"
        
        encrypted = manager.encrypt(original)
        assert encrypted != original
        assert len(encrypted) > 0
        
        decrypted = manager.decrypt(encrypted)
        assert decrypted == original
    
    def test_encrypt_empty_string(self):
        """Test encrypting an empty string."""
        manager = EncryptionManager()
        encrypted = manager.encrypt("")
        assert encrypted == ""
        
        decrypted = manager.decrypt("")
        assert decrypted == ""
    
    def test_encrypt_with_special_characters(self):
        """Test encryption with special characters."""
        manager = EncryptionManager()
        original = "Test with special chars: !@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        
        encrypted = manager.encrypt(original)
        decrypted = manager.decrypt(encrypted)
        assert decrypted == original
    
    def test_encrypt_with_unicode(self):
        """Test encryption with unicode characters."""
        manager = EncryptionManager()
        original = "Unicode test: 你好世界 🌍 Здравствуй мир"
        
        encrypted = manager.encrypt(original)
        decrypted = manager.decrypt(encrypted)
        assert decrypted == original
    
    def test_encrypt_dict_fields(self):
        """Test encrypting specific fields in a dictionary."""
        manager = EncryptionManager()
        data = {
            'public_field': 'public data',
            'secret_field': 'secret data',
            'another_secret': 'more secrets'
        }
        
        encrypted = manager.encrypt_dict(data, ['secret_field', 'another_secret'])
        
        # Public field should be unchanged
        assert encrypted['public_field'] == 'public data'
        
        # Secret fields should be encrypted
        assert encrypted['secret_field'] != 'secret data'
        assert encrypted['another_secret'] != 'more secrets'
        
        # Decrypt and verify
        decrypted = manager.decrypt_dict(encrypted, ['secret_field', 'another_secret'])
        assert decrypted['secret_field'] == 'secret data'
        assert decrypted['another_secret'] == 'more secrets'
    
    def test_encrypt_invalid_type(self):
        """Test that encrypting non-string raises TypeError."""
        manager = EncryptionManager()
        with pytest.raises(TypeError):
            manager.encrypt(12345)
    
    def test_decrypt_invalid_data(self):
        """Test that decrypting invalid data raises an exception."""
        manager = EncryptionManager()
        with pytest.raises(Exception):
            manager.decrypt("invalid_encrypted_data")


class TestPIIDetection:
    """Test suite for PII detection functions."""
    
    def test_detect_email(self):
        """Test email detection."""
        text = "Contact me at john.doe@example.com for more info."
        pii = detect_pii(text)
        assert 'email' in pii
        assert 'john.doe@example.com' in pii['email']
    
    def test_detect_phone(self):
        """Test phone number detection."""
        text = "Call me at 555-123-4567 or (555) 987-6543"
        pii = detect_pii(text)
        assert 'phone' in pii
        assert len(pii['phone']) >= 1
    
    def test_detect_ssn(self):
        """Test SSN detection."""
        text = "My SSN is 123-45-6789"
        pii = detect_pii(text)
        assert 'ssn' in pii
        assert '123-45-6789' in pii['ssn']
    
    def test_detect_credit_card(self):
        """Test credit card detection."""
        text = "Card number: 1234-5678-9012-3456"
        pii = detect_pii(text)
        assert 'credit_card' in pii
    
    def test_detect_ip_address(self):
        """Test IP address detection."""
        text = "Server IP: 192.168.1.1"
        pii = detect_pii(text)
        assert 'ip_address' in pii
        assert '192.168.1.1' in pii['ip_address']
    
    def test_detect_url(self):
        """Test URL detection."""
        text = "Visit https://www.example.com for details"
        pii = detect_pii(text)
        assert 'url' in pii
    
    def test_detect_name(self):
        """Test name detection."""
        text = "My name is John Smith and I have a fever."
        pii = detect_pii(text)
        assert 'name' in pii
        assert 'John Smith' in pii['name']
    
    def test_detect_no_pii(self):
        """Test text with no PII."""
        text = "I have a headache and fever for two days."
        pii = detect_pii(text)
        assert len(pii) == 0
    
    def test_detect_multiple_pii_types(self):
        """Test detection of multiple PII types."""
        text = "I'm John Doe, email john@example.com, phone 555-1234"
        pii = detect_pii(text)
        assert len(pii) >= 2  # Should detect name, email, and possibly phone


class TestPIIRemoval:
    """Test suite for PII removal functions."""
    
    def test_remove_email(self):
        """Test email removal."""
        text = "Contact me at john.doe@example.com for more info."
        sanitized = remove_pii(text)
        assert 'john.doe@example.com' not in sanitized
        assert '[REDACTED]' in sanitized
    
    def test_remove_phone(self):
        """Test phone number removal."""
        text = "Call me at 555-123-4567"
        sanitized = remove_pii(text)
        assert '555-123-4567' not in sanitized
        assert '[REDACTED]' in sanitized
    
    def test_remove_ssn(self):
        """Test SSN removal."""
        text = "My SSN is 123-45-6789"
        sanitized = remove_pii(text)
        assert '123-45-6789' not in sanitized
        assert '[REDACTED]' in sanitized
    
    def test_remove_custom_replacement(self):
        """Test PII removal with custom replacement."""
        text = "Email: test@example.com"
        sanitized = remove_pii(text, replacement="***")
        assert 'test@example.com' not in sanitized
        assert '***' in sanitized
    
    def test_remove_preserves_symptom_text(self):
        """Test that symptom descriptions are preserved."""
        text = "I have a severe headache and high fever."
        sanitized = remove_pii(text)
        assert 'headache' in sanitized
        assert 'fever' in sanitized
    
    def test_remove_multiple_pii(self):
        """Test removal of multiple PII instances."""
        text = "Contact john@example.com or jane@example.com"
        sanitized = remove_pii(text)
        assert 'john@example.com' not in sanitized
        assert 'jane@example.com' not in sanitized


class TestAnonymization:
    """Test suite for anonymization functions."""
    
    def test_anonymize_user_id(self):
        """Test user ID anonymization."""
        user_id = "user12345"
        anonymized = anonymize_user_id(user_id)
        
        assert anonymized != user_id
        assert anonymized.startswith('anon_')
        assert len(anonymized) > len('anon_')
    
    def test_anonymize_user_id_consistent(self):
        """Test that anonymization is consistent."""
        user_id = "user12345"
        anonymized1 = anonymize_user_id(user_id)
        anonymized2 = anonymize_user_id(user_id)
        
        assert anonymized1 == anonymized2
    
    def test_anonymize_user_id_different_for_different_ids(self):
        """Test that different IDs produce different anonymized values."""
        user_id1 = "user12345"
        user_id2 = "user67890"
        
        anonymized1 = anonymize_user_id(user_id1)
        anonymized2 = anonymize_user_id(user_id2)
        
        assert anonymized1 != anonymized2
    
    def test_anonymize_user_id_with_salt(self):
        """Test user ID anonymization with custom salt."""
        user_id = "user12345"
        anonymized1 = anonymize_user_id(user_id, salt="salt1")
        anonymized2 = anonymize_user_id(user_id, salt="salt2")
        
        assert anonymized1 != anonymized2
    
    def test_anonymize_user_id_empty_raises_error(self):
        """Test that empty user ID raises ValueError."""
        with pytest.raises(ValueError):
            anonymize_user_id("")
    
    def test_anonymize_conversation_log(self):
        """Test conversation log anonymization."""
        conversation = {
            'user_id': 'user12345',
            'messages': [
                {'role': 'user', 'content': 'My name is John and my email is john@example.com'},
                {'role': 'assistant', 'content': 'How can I help you?'}
            ]
        }
        
        anonymized = anonymize_conversation_log(conversation)
        
        # User ID should be anonymized
        assert anonymized['user_id'] != 'user12345'
        assert anonymized['user_id'].startswith('anon_')
        
        # PII should be removed from messages
        assert 'john@example.com' not in anonymized['messages'][0]['content']
        assert '[REDACTED]' in anonymized['messages'][0]['content']
    
    def test_anonymize_conversation_log_removes_contact_fields(self):
        """Test that contact fields are removed."""
        conversation = {
            'user_id': 'user12345',
            'email': 'user@example.com',
            'phone': '555-1234',
            'messages': []
        }
        
        anonymized = anonymize_conversation_log(conversation)
        
        assert 'email' not in anonymized
        assert 'phone' not in anonymized
        assert 'user_id' in anonymized  # Should be anonymized, not removed
    
    def test_hash_sensitive_field(self):
        """Test sensitive field hashing."""
        value = "sensitive_data"
        hashed = hash_sensitive_field(value)
        
        assert hashed != value
        assert len(hashed) == 64  # SHA-256 produces 64 hex characters
    
    def test_hash_sensitive_field_consistent(self):
        """Test that hashing is consistent."""
        value = "sensitive_data"
        hashed1 = hash_sensitive_field(value)
        hashed2 = hash_sensitive_field(value)
        
        assert hashed1 == hashed2
    
    def test_hash_sensitive_field_empty(self):
        """Test hashing empty string."""
        hashed = hash_sensitive_field("")
        assert hashed == ""


class TestSymptomDataEncryption:
    """Test suite for symptom data encryption."""
    
    def test_encrypt_symptom_data(self):
        """Test encrypting symptom data."""
        symptom_data = {
            'symptoms': {
                'fever': {
                    'present': True,
                    'severity': 8,
                    'description': 'High fever for 2 days'
                },
                'headache': {
                    'present': True,
                    'severity': 6,
                    'description': 'Persistent headache'
                }
            }
        }
        
        encrypted = encrypt_symptom_data(symptom_data)
        
        # Descriptions should be encrypted
        assert encrypted['symptoms']['fever']['description'] != 'High fever for 2 days'
        assert encrypted['symptoms']['headache']['description'] != 'Persistent headache'
        
        # Other fields should be unchanged
        assert encrypted['symptoms']['fever']['present'] == True
        assert encrypted['symptoms']['fever']['severity'] == 8
    
    def test_decrypt_symptom_data(self):
        """Test decrypting symptom data."""
        symptom_data = {
            'symptoms': {
                'fever': {
                    'present': True,
                    'severity': 8,
                    'description': 'High fever for 2 days'
                }
            }
        }
        
        encrypted = encrypt_symptom_data(symptom_data)
        decrypted = decrypt_symptom_data(encrypted)
        
        # Should match original
        assert decrypted['symptoms']['fever']['description'] == 'High fever for 2 days'
        assert decrypted['symptoms']['fever']['present'] == True
        assert decrypted['symptoms']['fever']['severity'] == 8
    
    def test_encrypt_decrypt_empty_description(self):
        """Test encrypting symptom with empty description."""
        symptom_data = {
            'symptoms': {
                'fever': {
                    'present': True,
                    'severity': 8,
                    'description': ''
                }
            }
        }
        
        encrypted = encrypt_symptom_data(symptom_data)
        decrypted = decrypt_symptom_data(encrypted)
        
        assert decrypted['symptoms']['fever']['description'] == ''


# Property-Based Tests

@given(st.text(min_size=1, max_size=1000))
def test_property_57_encryption_invariant(text):
    """
    Feature: illness-prediction-system, Property 57: Encryption invariant
    **Validates: Requirements 9.1**
    
    Test that any data encrypted then decrypted returns original value.
    
    For any text string, encrypting it and then decrypting the result
    should produce the exact original text. This ensures that encryption
    is lossless and reversible, which is critical for protecting sensitive
    health data while maintaining data integrity.
    """
    manager = EncryptionManager()
    
    # Encrypt the data
    encrypted = manager.encrypt(text)
    
    # Decrypt the encrypted data
    decrypted = manager.decrypt(encrypted)
    
    # Verify the round-trip preserves the original value
    assert decrypted == text, \
        f"Encryption round-trip failed: original length={len(text)}, decrypted length={len(decrypted)}"


@given(st.text(min_size=1, max_size=1000))
def test_property_encryption_round_trip(text):
    """
    Property test: Encryption round-trip preserves data.
    
    For any text, encrypting then decrypting should return the original text.
    Validates: Requirement 9.1
    """
    manager = EncryptionManager()
    
    encrypted = manager.encrypt(text)
    decrypted = manager.decrypt(encrypted)
    
    assert decrypted == text


@given(st.text(min_size=1, max_size=100))
def test_property_encryption_produces_different_output(text):
    """
    Property test: Encryption produces different output than input.
    
    For any non-empty text, the encrypted version should differ from the original.
    Validates: Requirement 9.1
    """
    manager = EncryptionManager()
    
    encrypted = manager.encrypt(text)
    
    # Encrypted text should be different from original
    assert encrypted != text


@given(st.text(min_size=1, max_size=100, alphabet=st.characters(min_codepoint=32, max_codepoint=126)))
def test_property_anonymize_user_id_consistency(user_id):
    """
    Property test: User ID anonymization is consistent.
    
    For any user ID, anonymizing it multiple times should produce the same result.
    Validates: Requirement 9.2, 9.3
    """
    anonymized1 = anonymize_user_id(user_id)
    anonymized2 = anonymize_user_id(user_id)
    
    assert anonymized1 == anonymized2
    assert anonymized1.startswith('anon_')


@given(st.text(min_size=1, max_size=100))
def test_property_hash_consistency(value):
    """
    Property test: Hashing is consistent.
    
    For any value, hashing it multiple times should produce the same result.
    Validates: Requirement 9.2
    """
    hashed1 = hash_sensitive_field(value)
    hashed2 = hash_sensitive_field(value)
    
    assert hashed1 == hashed2


@given(st.text(min_size=0, max_size=500))
def test_property_pii_removal_preserves_length_order(text):
    """
    Property test: PII removal doesn't drastically change text length.
    
    For any text, removing PII should produce text of similar or shorter length.
    Validates: Requirement 9.2
    """
    sanitized = remove_pii(text)
    
    # Sanitized text should not be drastically longer
    # (allowing for [REDACTED] replacements)
    assert len(sanitized) <= len(text) + 100


@given(
    st.dictionaries(
        keys=st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)),
        values=st.dictionaries(
            keys=st.sampled_from(['present', 'severity', 'description']),
            values=st.one_of(st.booleans(), st.integers(1, 10), st.text(max_size=100))
        ),
        min_size=1,
        max_size=5
    )
)
def test_property_symptom_encryption_round_trip(symptoms):
    """
    Property test: Symptom data encryption round-trip preserves data.
    
    For any symptom data, encrypting then decrypting should return the original.
    Validates: Requirement 9.1
    """
    symptom_data = {'symptoms': symptoms}
    
    encrypted = encrypt_symptom_data(symptom_data)
    decrypted = decrypt_symptom_data(encrypted)
    
    # Compare descriptions (which are encrypted)
    for symptom_name in symptoms:
        if 'description' in symptoms[symptom_name]:
            original_desc = symptoms[symptom_name]['description']
            decrypted_desc = decrypted['symptoms'][symptom_name]['description']
            
            # Convert to string for comparison (since encrypt converts to string)
            assert str(decrypted_desc) == str(original_desc)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
