"""
Web Channel Adapter for REST API.
Validates: Requirements 11.3, 11.4, 11.5
"""

import logging
from typing import Dict, Any, Optional

from src.channel.channel_adapter import ChannelAdapter, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class WebAdapter(ChannelAdapter):
    """
    Web channel adapter for REST API communication.
    
    Handles:
    - HTTP request/response message format
    - Full HTML/markdown support
    - No character limits
    - Rich formatting and media support
    
    Validates: Requirements 11.3, 11.4, 11.5
    """
    
    def __init__(self):
        """Initialize Web adapter."""
        super().__init__('web')
        logger.info("Web adapter initialized")
    
    def parse_incoming_message(self, raw_message: Dict[str, Any]) -> IncomingMessage:
        """
        Parse incoming message from REST API request.
        
        Expected format:
        {
            "content": "message text",
            "user_id": "user identifier",
            "session_id": "optional session id"
        }
        
        Args:
            raw_message: REST API request payload
        
        Returns:
            IncomingMessage: Standardized incoming message
        
        Validates: Requirements 11.3
        """
        content = raw_message.get('content', '')
        user_id = raw_message.get('user_id', '')
        session_id = raw_message.get('session_id')
        
        # Extract any additional metadata
        metadata = {
            'ip_address': raw_message.get('ip_address'),
            'user_agent': raw_message.get('user_agent'),
            'timestamp': raw_message.get('timestamp'),
        }
        
        # Remove None values from metadata
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
        return IncomingMessage(
            content=content,
            sender_id=user_id,
            channel='web',
            session_id=session_id,
            metadata=metadata
        )
    
    def format_outgoing_message(self, content: str, recipient_id: str, 
                               session_id: str, **kwargs) -> OutgoingMessage:
        """
        Format message for web/REST API response.
        
        Web supports:
        - Full HTML/markdown formatting
        - No character limits
        - Rich media (images, links, etc.)
        - Structured data (JSON)
        
        Args:
            content: Message content
            recipient_id: User identifier
            session_id: Session ID
            **kwargs: Additional options (format_type, structured_data, etc.)
        
        Returns:
            OutgoingMessage: Formatted web message
        
        Validates: Requirements 11.4
        """
        # Validate message format (minimal validation for web)
        is_valid, error = self.validate_message_format(content)
        if not is_valid:
            logger.warning(f"Web message validation failed: {error}")
        
        # Extract formatting options
        format_type = kwargs.get('format_type', 'plain')  # 'plain', 'markdown', 'html'
        structured_data = kwargs.get('structured_data', {})
        
        metadata = {
            'format_type': format_type,
            'recipient_id': recipient_id,
        }
        
        # Add structured data if provided (e.g., predictions, facilities)
        if structured_data:
            metadata['structured_data'] = structured_data
        
        return OutgoingMessage(
            content=content,
            recipient_id=recipient_id,
            channel='web',
            session_id=session_id,
            metadata=metadata
        )
    
    def send_message(self, message: OutgoingMessage) -> bool:
        """
        "Send" message via web (actually just prepare response).
        
        For web/REST API, messages are not actively sent but returned
        as HTTP responses. This method validates the message is ready
        to be returned.
        
        Args:
            message: Formatted outgoing message
        
        Returns:
            bool: Always True (message is ready for response)
        
        Validates: Requirements 11.5
        """
        # For web adapter, we don't actively send messages
        # They are returned as HTTP responses by the API
        logger.debug(f"Web message prepared for session {message.session_id}")
        return True
    
    def validate_message_format(self, content: str) -> tuple[bool, Optional[str]]:
        """
        Validate web message format.
        
        Web has minimal restrictions:
        - Content should not be empty
        
        Args:
            content: Message content
        
        Returns:
            tuple: (is_valid, error_message)
        
        Validates: Requirements 11.4
        """
        if not content or not content.strip():
            return False, "Message content cannot be empty"
        
        return True, None
    
    def get_character_limit(self) -> Optional[int]:
        """Web has no character limit."""
        return None
    
    def supports_rich_media(self) -> bool:
        """Web supports rich media."""
        return True
    
    def format_response(self, message: OutgoingMessage, 
                       additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Format a complete REST API response.
        
        Args:
            message: Outgoing message
            additional_data: Additional data to include in response
        
        Returns:
            Dict: Complete API response payload
        """
        response = {
            'session_id': message.session_id,
            'message': message.content,
            'channel': 'web',
            'format_type': message.metadata.get('format_type', 'plain'),
        }
        
        # Add structured data if present
        if 'structured_data' in message.metadata:
            response['data'] = message.metadata['structured_data']
        
        # Add any additional data
        if additional_data:
            response.update(additional_data)
        
        return response
