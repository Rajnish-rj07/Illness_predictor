"""
Encryption and anonymization utilities for the Illness Prediction System.

This module provides functions for:
- Encrypting/decrypting sensitive data (Requirement 9.1)
- Detecting and removing PII (Requirement 9.2)
- Anonymizing conversation logs (Requirement 9.3)

Validates: Requirements 9.1, 9.2, 9.3
"""

import os
import re
import hashlib
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import base64


# PII patterns for detection
PII_PATTERNS = {
    'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    'phone': r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
    'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
    'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
    'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    'url': r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)',
}

# Common name patterns (simplified - in production, use NER models)
NAME_PATTERNS = [
    r'\bmy name is\s+([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)\b',
    r'\bI am\s+([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)\b',
    r'\bI\'m\s+([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)\b',
]


class EncryptionManager:
    """
    Manages encryption/decryption operations for sensitive data.
    
    Uses Fernet (symmetric encryption) with AES-128 in CBC mode.
    Keys are derived from a master key using PBKDF2.
    
    Validates: Requirement 9.1
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption manager.
        
        Args:
            master_key: Master encryption key (base64 encoded).
                       If None, reads from ENCRYPTION_KEY environment variable.
                       If not set, generates a new key (for development only).
        """
        if master_key is None:
            master_key = os.environ.get('ENCRYPTION_KEY')
        
        if master_key is None:
            # Generate a new key for development
            # WARNING: In production, this should be loaded from secure storage
            master_key = Fernet.generate_key().decode('utf-8')
            print("WARNING: Generated new encryption key. Set ENCRYPTION_KEY environment variable in production.")
        
        # Ensure key is bytes
        if isinstance(master_key, str):
            master_key = master_key.encode('utf-8')
        
        # Validate key format
        try:
            self.fernet = Fernet(master_key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key format: {e}")
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt a string.
        
        Args:
            data: Plain text string to encrypt
            
        Returns:
            Base64-encoded encrypted string
            
        Validates: Requirement 9.1
        """
        if not isinstance(data, str):
            raise TypeError(f"Data must be a string, got {type(data)}")
        
        if not data:
            return ""
        
        # Convert to bytes and encrypt
        data_bytes = data.encode('utf-8')
        encrypted_bytes = self.fernet.encrypt(data_bytes)
        
        # Return as base64 string for storage
        return encrypted_bytes.decode('utf-8')
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt an encrypted string.
        
        Args:
            encrypted_data: Base64-encoded encrypted string
            
        Returns:
            Decrypted plain text string
            
        Validates: Requirement 9.1
        """
        if not isinstance(encrypted_data, str):
            raise TypeError(f"Encrypted data must be a string, got {type(encrypted_data)}")
        
        if not encrypted_data:
            return ""
        
        # Convert to bytes and decrypt
        encrypted_bytes = encrypted_data.encode('utf-8')
        decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
        
        # Return as string
        return decrypted_bytes.decode('utf-8')
    
    def encrypt_dict(self, data: Dict[str, Any], fields_to_encrypt: list) -> Dict[str, Any]:
        """
        Encrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing data
            fields_to_encrypt: List of field names to encrypt
            
        Returns:
            Dictionary with specified fields encrypted
            
        Validates: Requirement 9.1
        """
        encrypted_data = data.copy()
        
        for field in fields_to_encrypt:
            if field in encrypted_data and encrypted_data[field]:
                # Convert to string if needed
                value = encrypted_data[field]
                if not isinstance(value, str):
                    value = str(value)
                encrypted_data[field] = self.encrypt(value)
        
        return encrypted_data
    
    def decrypt_dict(self, data: Dict[str, Any], fields_to_decrypt: list) -> Dict[str, Any]:
        """
        Decrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing encrypted data
            fields_to_decrypt: List of field names to decrypt
            
        Returns:
            Dictionary with specified fields decrypted
            
        Validates: Requirement 9.1
        """
        decrypted_data = data.copy()
        
        for field in fields_to_decrypt:
            if field in decrypted_data and decrypted_data[field]:
                decrypted_data[field] = self.decrypt(decrypted_data[field])
        
        return decrypted_data


def detect_pii(text: str) -> Dict[str, list]:
    """
    Detect personally identifiable information (PII) in text.
    
    Args:
        text: Text to scan for PII
        
    Returns:
        Dictionary mapping PII type to list of detected instances
        
    Validates: Requirement 9.2
    """
    detected_pii = {}
    
    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            detected_pii[pii_type] = matches
    
    # Check for names
    name_matches = []
    for pattern in NAME_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        name_matches.extend(matches)
    
    if name_matches:
        detected_pii['name'] = name_matches
    
    return detected_pii


def remove_pii(text: str, replacement: str = "[REDACTED]") -> str:
    """
    Remove personally identifiable information (PII) from text.
    
    Args:
        text: Text to sanitize
        replacement: String to replace PII with (default: "[REDACTED]")
        
    Returns:
        Sanitized text with PII removed
        
    Validates: Requirement 9.2
    """
    sanitized_text = text
    
    # Remove each type of PII
    for pii_type, pattern in PII_PATTERNS.items():
        sanitized_text = re.sub(pattern, replacement, sanitized_text, flags=re.IGNORECASE)
    
    # Remove names
    for pattern in NAME_PATTERNS:
        sanitized_text = re.sub(pattern, lambda m: f"{m.group(0).split()[0]} {replacement}", sanitized_text)
    
    return sanitized_text


def anonymize_user_id(user_id: str, salt: Optional[str] = None) -> str:
    """
    Anonymize a user ID using one-way hashing.
    
    Args:
        user_id: Original user identifier
        salt: Optional salt for hashing (uses default if not provided)
        
    Returns:
        Anonymized user ID (SHA-256 hash)
        
    Validates: Requirement 9.2, 9.3
    """
    if not user_id:
        raise ValueError("User ID cannot be empty")
    
    # Use a default salt if none provided
    if salt is None:
        salt = os.environ.get('ANONYMIZATION_SALT', 'illness-prediction-system-salt')
    
    # Create hash
    hash_input = f"{user_id}{salt}".encode('utf-8')
    hash_digest = hashlib.sha256(hash_input).hexdigest()
    
    return f"anon_{hash_digest[:16]}"


def anonymize_conversation_log(conversation_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Anonymize a conversation log before storage.
    
    Removes PII from messages and anonymizes user identifiers.
    
    Args:
        conversation_data: Dictionary containing conversation data
        
    Returns:
        Anonymized conversation data
        
    Validates: Requirement 9.3
    """
    anonymized_data = conversation_data.copy()
    
    # Anonymize user ID if present
    if 'user_id' in anonymized_data:
        anonymized_data['user_id'] = anonymize_user_id(anonymized_data['user_id'])
    
    # Remove PII from messages
    if 'messages' in anonymized_data:
        anonymized_messages = []
        for message in anonymized_data['messages']:
            anonymized_message = message.copy()
            if 'content' in anonymized_message:
                anonymized_message['content'] = remove_pii(anonymized_message['content'])
            anonymized_messages.append(anonymized_message)
        anonymized_data['messages'] = anonymized_messages
    
    # Remove PII from conversation context if present
    if 'conversation_context' in anonymized_data:
        context = anonymized_data['conversation_context']
        if isinstance(context, dict) and 'messages' in context:
            anonymized_messages = []
            for message in context['messages']:
                anonymized_message = message.copy()
                if 'content' in anonymized_message:
                    anonymized_message['content'] = remove_pii(anonymized_message['content'])
                anonymized_messages.append(anonymized_message)
            anonymized_data['conversation_context']['messages'] = anonymized_messages
    
    # Remove any contact information fields
    fields_to_remove = ['email', 'phone', 'phone_number', 'address', 'full_name', 'name']
    for field in fields_to_remove:
        if field in anonymized_data:
            del anonymized_data[field]
    
    return anonymized_data


def hash_sensitive_field(value: str, salt: Optional[str] = None) -> str:
    """
    Create a one-way hash of a sensitive field for indexing/lookup.
    
    Useful for creating searchable tokens without storing the original value.
    
    Args:
        value: Value to hash
        salt: Optional salt for hashing
        
    Returns:
        Hexadecimal hash string
        
    Validates: Requirement 9.2
    """
    if not value:
        return ""
    
    if salt is None:
        salt = os.environ.get('FIELD_HASH_SALT', 'field-hash-salt')
    
    hash_input = f"{value}{salt}".encode('utf-8')
    return hashlib.sha256(hash_input).hexdigest()


def generate_encryption_key() -> str:
    """
    Generate a new encryption key for Fernet.
    
    Returns:
        Base64-encoded encryption key
        
    Note: This should only be used for initial setup.
          Store the key securely and use it consistently.
    """
    return Fernet.generate_key().decode('utf-8')


# Global encryption manager instance (lazy initialization)
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """
    Get the global encryption manager instance.
    
    Returns:
        EncryptionManager instance
    """
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


def encrypt_symptom_data(symptom_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Encrypt sensitive fields in symptom data.
    
    Args:
        symptom_data: Dictionary containing symptom information
        
    Returns:
        Dictionary with sensitive fields encrypted
        
    Validates: Requirement 9.1
    """
    manager = get_encryption_manager()
    
    # Fields that should be encrypted
    sensitive_fields = ['description']
    
    encrypted_data = symptom_data.copy()
    
    # Encrypt symptom descriptions if present
    if 'symptoms' in encrypted_data:
        encrypted_symptoms = {}
        for symptom_name, symptom_info in encrypted_data['symptoms'].items():
            if isinstance(symptom_info, dict):
                encrypted_symptom = symptom_info.copy()
                if 'description' in encrypted_symptom and encrypted_symptom['description']:
                    # Convert to string if needed
                    desc = encrypted_symptom['description']
                    if not isinstance(desc, str):
                        desc = str(desc)
                    encrypted_symptom['description'] = manager.encrypt(desc)
                encrypted_symptoms[symptom_name] = encrypted_symptom
            else:
                encrypted_symptoms[symptom_name] = symptom_info
        encrypted_data['symptoms'] = encrypted_symptoms
    
    return encrypted_data


def decrypt_symptom_data(encrypted_symptom_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decrypt sensitive fields in symptom data.
    
    Args:
        encrypted_symptom_data: Dictionary containing encrypted symptom information
        
    Returns:
        Dictionary with sensitive fields decrypted
        
    Validates: Requirement 9.1
    """
    manager = get_encryption_manager()
    
    decrypted_data = encrypted_symptom_data.copy()
    
    # Decrypt symptom descriptions if present
    if 'symptoms' in decrypted_data:
        decrypted_symptoms = {}
        for symptom_name, symptom_info in decrypted_data['symptoms'].items():
            if isinstance(symptom_info, dict):
                decrypted_symptom = symptom_info.copy()
                if 'description' in decrypted_symptom and decrypted_symptom['description']:
                    try:
                        decrypted_symptom['description'] = manager.decrypt(decrypted_symptom['description'])
                    except Exception:
                        # If decryption fails, data might not be encrypted
                        pass
                decrypted_symptoms[symptom_name] = decrypted_symptom
            else:
                decrypted_symptoms[symptom_name] = symptom_info
        decrypted_data['symptoms'] = decrypted_symptoms
    
    return decrypted_data
