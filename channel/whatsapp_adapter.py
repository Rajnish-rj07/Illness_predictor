"""
WhatsApp Channel Adapter using WhatsApp Business API.
Validates: Requirements 11.2, 11.4, 11.5
"""

import os
import logging
import requests
from typing import Dict, Any, Optional, List
from requests.exceptions import RequestException

from src.channel.channel_adapter import ChannelAdapter, IncomingMessage, OutgoingMessage

logger = logging.getLogger(__name__)


class WhatsAppAdapter(ChannelAdapter):
    """
    WhatsApp channel adapter using WhatsApp Business API.
    
    Handles:
    - WhatsApp message reception via webhooks
    - Rich media support (formatting, buttons, lists)
    - Message delivery via WhatsApp Business API
    - Character limits (4096 chars per message)
    
    Validates: Requirements 11.2, 11.4, 11.5
    """
    
    # WhatsApp character limit
    MESSAGE_LIMIT = 4096
    
    def __init__(self, access_token: Optional[str] = None,
                 phone_number_id: Optional[str] = None,
                 api_version: str = 'v18.0'):
        """
        Initialize WhatsApp adapter with Business API credentials.
        
        Args:
            access_token: WhatsApp Business API access token (defaults to env var WHATSAPP_ACCESS_TOKEN)
            phone_number_id: WhatsApp Business phone number ID (defaults to env var WHATSAPP_PHONE_NUMBER_ID)
            api_version: WhatsApp API version (default: v18.0)
        """
        super().__init__('whatsapp')
        
        self.access_token = access_token or os.getenv('WHATSAPP_ACCESS_TOKEN')
        self.phone_number_id = phone_number_id or os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        self.api_version = api_version
        self.api_base_url = f"https://graph.facebook.com/{api_version}"
        
        if self.access_token and self.phone_number_id:
            logger.info("WhatsApp adapter initialized with Business API credentials")
        else:
            logger.warning("WhatsApp adapter initialized without credentials (test mode)")
    
    def parse_incoming_message(self, raw_message: Dict[str, Any]) -> IncomingMessage:
        """
        Parse incoming WhatsApp message from webhook payload.
        
        WhatsApp webhook sends nested structure:
        - entry[0].changes[0].value.messages[0]
        - Contains: from, text.body, id, timestamp
        
        Args:
            raw_message: WhatsApp webhook payload
        
        Returns:
            IncomingMessage: Standardized incoming message
        
        Validates: Requirements 11.2, 11.3
        """
        try:
            # Navigate WhatsApp's nested structure
            entry = raw_message.get('entry', [{}])[0]
            changes = entry.get('changes', [{}])[0]
            value = changes.get('value', {})
            messages = value.get('messages', [])
            
            if not messages or not messages[0]:
                raise ValueError("No messages found in webhook payload")
            
            message = messages[0]
            
            sender_id = message.get('from', '')
            if not sender_id:
                raise ValueError("No sender ID in message")
            
            message_id = message.get('id', '')
            message_type = message.get('type', 'text')
            
            # Extract content based on message type
            if message_type == 'text':
                content = message.get('text', {}).get('body', '')
            elif message_type == 'button':
                content = message.get('button', {}).get('text', '')
            elif message_type == 'interactive':
                # Handle interactive messages (buttons, lists)
                interactive = message.get('interactive', {})
                if interactive.get('type') == 'button_reply':
                    content = interactive.get('button_reply', {}).get('title', '')
                elif interactive.get('type') == 'list_reply':
                    content = interactive.get('list_reply', {}).get('title', '')
                else:
                    content = str(interactive)
            else:
                content = f"[Unsupported message type: {message_type}]"
            
            # Extract session ID if present
            session_id = None
            if '[SESSION:' in content:
                try:
                    start = content.index('[SESSION:') + 9
                    end = content.index(']', start)
                    session_id = content[start:end]
                    content = content.replace(f'[SESSION:{session_id}]', '').strip()
                except (ValueError, IndexError):
                    pass
            
            return IncomingMessage(
                content=content,
                sender_id=sender_id,
                channel='whatsapp',
                session_id=session_id,
                metadata={
                    'message_id': message_id,
                    'message_type': message_type,
                    'timestamp': message.get('timestamp'),
                }
            )
            
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Error parsing WhatsApp webhook payload: {e}")
            # Return a default message to avoid breaking the flow
            return IncomingMessage(
                content="",
                sender_id="unknown",
                channel='whatsapp',
                session_id=None,
                metadata={'error': str(e)}
            )
        except Exception as e:
            logger.error(f"Unexpected error parsing WhatsApp webhook payload: {e}")
            return IncomingMessage(
                content="",
                sender_id="unknown",
                channel='whatsapp',
                session_id=None,
                metadata={'error': str(e)}
            )
    
    def format_outgoing_message(self, content: str, recipient_id: str, 
                               session_id: str, **kwargs) -> OutgoingMessage:
        """
        Format message for WhatsApp with rich media support.
        
        WhatsApp supports:
        - Markdown-style formatting (*bold*, _italic_)
        - Up to 4096 characters per message
        - Interactive buttons and lists
        - Emojis and special characters
        
        Args:
            content: Message content
            recipient_id: Recipient WhatsApp ID
            session_id: Session ID
            **kwargs: Additional options (use_formatting, buttons, etc.)
        
        Returns:
            OutgoingMessage: Formatted WhatsApp message
        
        Validates: Requirements 11.4
        """
        # Validate message format
        is_valid, error = self.validate_message_format(content)
        if not is_valid:
            logger.warning(f"WhatsApp message validation failed: {error}")
            if len(content) > self.MESSAGE_LIMIT:
                content = content[:self.MESSAGE_LIMIT - 3] + "..."
        
        # Apply WhatsApp formatting if enabled
        use_formatting = kwargs.get('use_formatting', True)
        if use_formatting:
            content = self._apply_whatsapp_formatting(content)
        
        # Extract button configuration if provided
        buttons = kwargs.get('buttons', [])
        
        metadata = {
            'recipient_id': recipient_id,
            'use_formatting': use_formatting,
        }
        
        # Add button configuration to metadata
        if buttons:
            metadata['buttons'] = buttons
            metadata['message_type'] = 'interactive'
        else:
            metadata['message_type'] = 'text'
        
        return OutgoingMessage(
            content=content,
            recipient_id=recipient_id,
            channel='whatsapp',
            session_id=session_id,
            metadata=metadata
        )
    
    def send_message(self, message: OutgoingMessage) -> bool:
        """
        Send WhatsApp message via Business API.
        
        Args:
            message: Formatted outgoing message
        
        Returns:
            bool: True if sent successfully
        
        Validates: Requirements 11.5
        """
        if not self.access_token or not self.phone_number_id:
            logger.error("Cannot send WhatsApp message: Missing credentials")
            return False
        
        url = f"{self.api_base_url}/{self.phone_number_id}/messages"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
        }
        
        # Build message payload based on type
        message_type = message.metadata.get('message_type', 'text')
        
        if message_type == 'interactive' and message.metadata.get('buttons'):
            # Send interactive message with buttons
            payload = self._build_interactive_payload(message)
        else:
            # Send simple text message
            payload = {
                'messaging_product': 'whatsapp',
                'recipient_type': 'individual',
                'to': message.recipient_id,
                'type': 'text',
                'text': {
                    'preview_url': False,
                    'body': message.content
                }
            }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            message_id = result.get('messages', [{}])[0].get('id')
            logger.info(f"WhatsApp message sent successfully: {message_id}")
            return True
            
        except RequestException as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp message: {e}")
            return False
    
    def validate_message_format(self, content: str) -> tuple[bool, Optional[str]]:
        """
        Validate WhatsApp message format.
        
        Checks:
        - Character limit (4096 chars)
        - Content is not empty
        
        Args:
            content: Message content
        
        Returns:
            tuple: (is_valid, error_message)
        
        Validates: Requirements 11.4
        """
        if not content or not content.strip():
            return False, "Message content cannot be empty"
        
        if len(content) > self.MESSAGE_LIMIT:
            return False, f"Message exceeds WhatsApp limit of {self.MESSAGE_LIMIT} characters"
        
        return True, None
    
    def get_character_limit(self) -> Optional[int]:
        """Get WhatsApp character limit."""
        return self.MESSAGE_LIMIT
    
    def supports_rich_media(self) -> bool:
        """WhatsApp supports rich media."""
        return True
    
    def _apply_whatsapp_formatting(self, content: str) -> str:
        """
        Apply WhatsApp-specific formatting.
        
        WhatsApp supports:
        - *bold*
        - _italic_
        - ~strikethrough~
        - ```monospace```
        
        Args:
            content: Plain text content
        
        Returns:
            str: Formatted content
        """
        # This is a simple pass-through since we expect content to already
        # have WhatsApp formatting markers if needed
        # In a real implementation, you might convert from markdown or HTML
        return content
    
    def _build_interactive_payload(self, message: OutgoingMessage) -> Dict[str, Any]:
        """
        Build interactive message payload with buttons.
        
        Args:
            message: Outgoing message with button metadata
        
        Returns:
            Dict: WhatsApp API payload for interactive message
        """
        buttons = message.metadata.get('buttons', [])
        
        # WhatsApp supports up to 3 buttons
        if len(buttons) > 3:
            logger.warning(f"WhatsApp supports max 3 buttons, truncating from {len(buttons)}")
            buttons = buttons[:3]
        
        # Build button objects
        button_objects = []
        for i, button_text in enumerate(buttons):
            button_objects.append({
                'type': 'reply',
                'reply': {
                    'id': f'button_{i}',
                    'title': button_text[:20]  # Max 20 chars for button title
                }
            })
        
        return {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': message.recipient_id,
            'type': 'interactive',
            'interactive': {
                'type': 'button',
                'body': {
                    'text': message.content
                },
                'action': {
                    'buttons': button_objects
                }
            }
        }
