"""
SMS Channel Adapter using Twilio.
Validates: Requirements 11.1, 11.4, 11.5
"""

import os
import logging
from typing import Dict, Any, Optional, List
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from src.channel.channel_adapter import ChannelAdapter, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class SMSAdapter(ChannelAdapter):
    """
    SMS channel adapter using Twilio API.
    
    Handles:
    - SMS message reception via Twilio webhooks
    - Character limit enforcement (1600 chars for concatenated SMS)
    - Message splitting for long content
    - SMS delivery via Twilio API
    
    Validates: Requirements 11.1, 11.4, 11.5
    """
    
    # SMS character limits
    SINGLE_SMS_LIMIT = 160
    CONCATENATED_SMS_LIMIT = 1600  # ~10 concatenated messages
    
    def __init__(self, account_sid: Optional[str] = None, 
                 auth_token: Optional[str] = None,
                 from_number: Optional[str] = None):
        """
        Initialize SMS adapter with Twilio credentials.
        
        Args:
            account_sid: Twilio account SID (defaults to env var TWILIO_ACCOUNT_SID)
            auth_token: Twilio auth token (defaults to env var TWILIO_AUTH_TOKEN)
            from_number: Twilio phone number to send from (defaults to env var TWILIO_PHONE_NUMBER)
        """
        super().__init__('sms')
        
        self.account_sid = account_sid or os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = auth_token or os.getenv('TWILIO_AUTH_TOKEN')
        self.from_number = from_number or os.getenv('TWILIO_PHONE_NUMBER')
        
        # Initialize Twilio client if credentials are available
        self.client = None
        if self.account_sid and self.auth_token:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("SMS adapter initialized with Twilio client")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
        else:
            logger.warning("SMS adapter initialized without Twilio credentials (test mode)")
    
    def parse_incoming_message(self, raw_message: Dict[str, Any]) -> IncomingMessage:
        """
        Parse incoming SMS from Twilio webhook payload.
        
        Twilio webhook sends:
        - From: Sender's phone number
        - Body: Message content
        - MessageSid: Unique message identifier
        
        Args:
            raw_message: Twilio webhook payload
        
        Returns:
            IncomingMessage: Standardized incoming message
        
        Validates: Requirements 11.1, 11.3
        """
        sender_phone = raw_message.get('From', '')
        content = raw_message.get('Body', '')
        message_sid = raw_message.get('MessageSid', '')
        
        # Extract session ID if present in message (format: [SESSION:session_id])
        session_id = None
        if '[SESSION:' in content:
            try:
                start = content.index('[SESSION:') + 9
                end = content.index(']', start)
                session_id = content[start:end]
                # Remove session marker from content
                content = content.replace(f'[SESSION:{session_id}]', '').strip()
            except (ValueError, IndexError):
                pass
        
        return IncomingMessage(
            content=content,
            sender_id=sender_phone,
            channel='sms',
            session_id=session_id,
            metadata={
                'message_sid': message_sid,
                'from_number': sender_phone,
            }
        )
    
    def format_outgoing_message(self, content: str, recipient_id: str, 
                               session_id: str, **kwargs) -> OutgoingMessage:
        """
        Format message for SMS with character limit enforcement.
        
        SMS constraints:
        - Maximum 1600 characters (concatenated SMS)
        - Plain text only (no rich formatting)
        - Automatic message splitting if needed
        
        Args:
            content: Message content
            recipient_id: Recipient phone number
            session_id: Session ID
            **kwargs: Additional options (include_session_id, etc.)
        
        Returns:
            OutgoingMessage: Formatted SMS message
        
        Validates: Requirements 11.4
        """
        # Validate message format
        is_valid, error = self.validate_message_format(content)
        if not is_valid:
            logger.warning(f"SMS message validation failed: {error}")
            # Truncate if too long
            if len(content) > self.CONCATENATED_SMS_LIMIT:
                content = content[:self.CONCATENATED_SMS_LIMIT - 3] + "..."
        
        # Optionally include session ID for easy resumption
        include_session_id = kwargs.get('include_session_id', False)
        if include_session_id:
            session_marker = f"\n[SESSION:{session_id}]"
            # Ensure we don't exceed limit with session marker
            if len(content) + len(session_marker) > self.CONCATENATED_SMS_LIMIT:
                content = content[:self.CONCATENATED_SMS_LIMIT - len(session_marker) - 3] + "..."
            content += session_marker
        
        return OutgoingMessage(
            content=content,
            recipient_id=recipient_id,
            channel='sms',
            session_id=session_id,
            metadata={
                'from_number': self.from_number,
                'to_number': recipient_id,
            }
        )
    
    def send_message(self, message: OutgoingMessage) -> bool:
        """
        Send SMS via Twilio API.
        
        Args:
            message: Formatted outgoing message
        
        Returns:
            bool: True if sent successfully
        
        Validates: Requirements 11.5
        """
        if not self.client:
            logger.error("Cannot send SMS: Twilio client not initialized")
            return False
        
        if not self.from_number:
            logger.error("Cannot send SMS: No from_number configured")
            return False
        
        try:
            # Split message if it exceeds single SMS limit
            message_parts = self.split_long_message(
                message.content, 
                self.SINGLE_SMS_LIMIT
            )
            
            # Send each part
            for i, part in enumerate(message_parts):
                # Add part indicator if multiple parts
                if len(message_parts) > 1:
                    part_content = f"({i+1}/{len(message_parts)}) {part}"
                else:
                    part_content = part
                
                twilio_message = self.client.messages.create(
                    body=part_content,
                    from_=self.from_number,
                    to=message.recipient_id
                )
                
                logger.info(f"SMS sent successfully: {twilio_message.sid} (part {i+1}/{len(message_parts)})")
            
            return True
            
        except TwilioRestException as e:
            logger.error(f"Twilio API error sending SMS: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {e}")
            return False
    
    def validate_message_format(self, content: str) -> tuple[bool, Optional[str]]:
        """
        Validate SMS message format.
        
        Checks:
        - Character limit (1600 chars for concatenated SMS)
        - Content is not empty
        
        Args:
            content: Message content
        
        Returns:
            tuple: (is_valid, error_message)
        
        Validates: Requirements 11.4
        """
        if not content or not content.strip():
            return False, "Message content cannot be empty"
        
        if len(content) > self.CONCATENATED_SMS_LIMIT:
            return False, f"Message exceeds SMS limit of {self.CONCATENATED_SMS_LIMIT} characters"
        
        return True, None
    
    def get_character_limit(self) -> Optional[int]:
        """Get SMS character limit."""
        return self.CONCATENATED_SMS_LIMIT
    
    def supports_rich_media(self) -> bool:
        """SMS does not support rich media."""
        return False
