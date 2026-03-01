"""
Privacy and Security Service for the Illness Prediction System.

This module provides:
- Encryption layer for data at rest and in transit
- PII detection and removal
- Session anonymization
- Data deletion capabilities

Validates: Requirements 9.1, 9.2, 9.3, 9.5
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib

from src.utils.encryption import (
    EncryptionManager, 
    detect_pii, 
    remove_pii, 
    anonymize_conversation_log,
    hash_sensitive_field
)

logger = logging.getLogger(__name__)


class PrivacyService:
    """
    Service for managing data privacy and security.
    
    Validates: Requirements 9.1, 9.2, 9.3, 9.5
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize privacy service.
        
        Args:
            encryption_key: Master encryption key (optional)
        """
        self.encryption_manager = EncryptionManager(encryption_key)
        logger.info("PrivacyService initialized")
    
    def encrypt_data(self, data: str) -> str:
        """
        Encrypt sensitive data for storage.
        
        Validates: Requirement 9.1
        
        Args:
            data: Plain text data to encrypt
            
        Returns:
            Encrypted data as base64 string
        """
        if not data:
            return ""
        
        try:
            encrypted = self.encryption_manager.encrypt(data)
            logger.debug(f"Data encrypted successfully (length: {len(data)})")
            return encrypted
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt data for use.
        
        Validates: Requirement 9.1
        
        Args:
            encrypted_data: Encrypted data as base64 string
            
        Returns:
            Decrypted plain text data
        """
        if not encrypted_data:
            return ""
        
        try:
            decrypted = self.encryption_manager.decrypt(encrypted_data)
            logger.debug(f"Data decrypted successfully")
            return decrypted
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def sanitize_input(self, text: str) -> Dict[str, Any]:
        """
        Detect and remove PII from user input.
        
        Validates: Requirement 9.2
        
        Args:
            text: User input text
            
        Returns:
            Dictionary with:
                - sanitized_text: Text with PII removed
                - pii_detected: List of PII types detected
                - has_pii: Boolean indicating if PII was found
        """
        # Detect PII
        pii_found = detect_pii(text)
        
        # Remove PII
        sanitized = remove_pii(text)
        
        result = {
            'sanitized_text': sanitized,
            'pii_detected': list(pii_found.keys()) if pii_found else [],
            'has_pii': bool(pii_found)
        }
        
        if result['has_pii']:
            logger.warning(f"PII detected and removed: {result['pii_detected']}")
        
        return result
    
    def anonymize_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize session data before storage.
        
        Validates: Requirement 9.3
        
        Args:
            session_data: Session data dictionary
            
        Returns:
            Anonymized session data
        """
        anonymized = session_data.copy()
        
        # Remove or hash user identifiers
        if 'user_id' in anonymized:
            # Hash user_id for analytics while removing direct identifier
            anonymized['user_id_hash'] = self._hash_identifier(anonymized['user_id'])
            del anonymized['user_id']
        
        if 'phone_number' in anonymized:
            anonymized['phone_number_hash'] = self._hash_identifier(anonymized['phone_number'])
            del anonymized['phone_number']
        
        if 'email' in anonymized:
            anonymized['email_hash'] = self._hash_identifier(anonymized['email'])
            del anonymized['email']
        
        # Anonymize conversation messages
        if 'messages' in anonymized:
            anonymized['messages'] = [
                self._anonymize_message(msg) for msg in anonymized['messages']
            ]
        
        # Add anonymization timestamp
        anonymized['anonymized_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Session anonymized: {anonymized.get('session_id', 'unknown')}")
        
        return anonymized
    
    def _anonymize_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize a single message.
        
        Args:
            message: Message dictionary
            
        Returns:
            Anonymized message
        """
        anonymized_msg = message.copy()
        
        # Anonymize message content - remove PII
        if 'content' in anonymized_msg:
            anonymized_msg['content'] = remove_pii(anonymized_msg['content'])
        
        # Remove sender identifiers if present
        if 'sender_id' in anonymized_msg:
            anonymized_msg['sender_id_hash'] = self._hash_identifier(anonymized_msg['sender_id'])
            del anonymized_msg['sender_id']
        
        return anonymized_msg
    
    def _hash_identifier(self, identifier: str) -> str:
        """
        Create a one-way hash of an identifier.
        
        Args:
            identifier: Identifier to hash
            
        Returns:
            SHA-256 hash of identifier
        """
        return hashlib.sha256(identifier.encode('utf-8')).hexdigest()
    
    def validate_no_pii(self, data: Dict[str, Any]) -> bool:
        """
        Validate that data contains no PII.
        
        Validates: Requirement 9.2
        
        Args:
            data: Data dictionary to validate
            
        Returns:
            True if no PII detected, False otherwise
        """
        # Check all string values in the dictionary
        for key, value in data.items():
            if isinstance(value, str):
                pii_found = detect_pii(value)
                if pii_found:
                    logger.warning(f"PII found in field '{key}': {list(pii_found.keys())}")
                    return False
            elif isinstance(value, dict):
                if not self.validate_no_pii(value):
                    return False
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        pii_found = detect_pii(item)
                        if pii_found:
                            logger.warning(f"PII found in list field '{key}': {list(pii_found.keys())}")
                            return False
                    elif isinstance(item, dict):
                        if not self.validate_no_pii(item):
                            return False
        
        return True
    
    def delete_session_data(
        self,
        session_id: str,
        database_client: Any
    ) -> bool:
        """
        Delete all data associated with a session.
        
        Validates: Requirement 9.5
        
        Args:
            session_id: Session identifier
            database_client: Database client for data deletion
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            # Delete session record
            database_client.delete('sessions', {'session_id': session_id})
            
            # Delete associated predictions
            database_client.delete('predictions', {'session_id': session_id})
            
            # Delete conversation logs
            database_client.delete('conversation_logs', {'session_id': session_id})
            
            # Delete feedback
            database_client.delete('feedback', {'session_id': session_id})
            
            logger.info(f"All data deleted for session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session data: {e}")
            return False
    
    def encrypt_symptom_vector(self, symptom_vector: Dict[str, Any]) -> str:
        """
        Encrypt symptom vector for storage.
        
        Validates: Requirement 9.1
        
        Args:
            symptom_vector: Symptom vector dictionary
            
        Returns:
            Encrypted symptom vector as string
        """
        import json
        
        # Convert to JSON string
        json_str = json.dumps(symptom_vector)
        
        # Encrypt
        encrypted = self.encrypt_data(json_str)
        
        return encrypted
    
    def decrypt_symptom_vector(self, encrypted_vector: str) -> Dict[str, Any]:
        """
        Decrypt symptom vector from storage.
        
        Validates: Requirement 9.1
        
        Args:
            encrypted_vector: Encrypted symptom vector string
            
        Returns:
            Decrypted symptom vector dictionary
        """
        import json
        
        # Decrypt
        json_str = self.decrypt_data(encrypted_vector)
        
        # Parse JSON
        symptom_vector = json.loads(json_str)
        
        return symptom_vector
