"""
Abstract ChannelAdapter interface for multi-channel communication.
Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class IncomingMessage:
    """Represents an incoming message from any channel."""
    content: str
    sender_id: str  # Channel-specific user identifier
    channel: str  # 'sms', 'whatsapp', 'web'
    session_id: Optional[str] = None  # If resuming existing session
    metadata: Dict[str, Any] = None  # Channel-specific metadata
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class OutgoingMessage:
    """Represents an outgoing message to be sent through a channel."""
    content: str
    recipient_id: str  # Channel-specific user identifier
    channel: str  # 'sms', 'whatsapp', 'web'
    session_id: str
    metadata: Dict[str, Any] = None  # Channel-specific formatting/options
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ChannelAdapter(ABC):
    """
    Abstract base class for channel adapters.
    
    Each channel adapter handles:
    - Receiving messages from the channel
    - Formatting responses for the channel
    - Sending messages through the channel
    - Channel-specific constraints (character limits, rich media support)
    
    Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5
    """
    
    def __init__(self, channel_name: str):
        """
        Initialize the channel adapter.
        
        Args:
            channel_name: Name of the channel ('sms', 'whatsapp', 'web')
        """
        self.channel_name = channel_name
    
    @abstractmethod
    def parse_incoming_message(self, raw_message: Dict[str, Any]) -> IncomingMessage:
        """
        Parse a raw incoming message from the channel into a standardized format.
        
        Args:
            raw_message: Raw message data from the channel (webhook payload, API response, etc.)
        
        Returns:
            IncomingMessage: Standardized incoming message
        
        Validates: Requirements 11.3
        """
        pass
    
    @abstractmethod
    def format_outgoing_message(self, content: str, recipient_id: str, 
                               session_id: str, **kwargs) -> OutgoingMessage:
        """
        Format a message for sending through this channel.
        
        Applies channel-specific formatting:
        - SMS: Character limit enforcement, message splitting
        - WhatsApp: Rich media support, formatting
        - Web: Full HTML/markdown support
        
        Args:
            content: Message content to send
            recipient_id: Channel-specific recipient identifier
            session_id: Session ID for tracking
            **kwargs: Additional channel-specific options
        
        Returns:
            OutgoingMessage: Formatted message ready to send
        
        Validates: Requirements 11.4
        """
        pass
    
    @abstractmethod
    def send_message(self, message: OutgoingMessage) -> bool:
        """
        Send a message through the channel.
        
        Args:
            message: Formatted outgoing message
        
        Returns:
            bool: True if message was sent successfully, False otherwise
        
        Validates: Requirements 11.5
        """
        pass
    
    @abstractmethod
    def validate_message_format(self, content: str) -> tuple[bool, Optional[str]]:
        """
        Validate that a message meets channel-specific requirements.
        
        Args:
            content: Message content to validate
        
        Returns:
            tuple: (is_valid, error_message)
                - is_valid: True if message is valid for this channel
                - error_message: Description of validation error, or None if valid
        
        Validates: Requirements 11.4
        """
        pass
    
    def get_channel_name(self) -> str:
        """Get the name of this channel."""
        return self.channel_name
    
    def supports_rich_media(self) -> bool:
        """
        Check if this channel supports rich media (images, buttons, etc.).
        
        Returns:
            bool: True if rich media is supported
        """
        return False
    
    def get_character_limit(self) -> Optional[int]:
        """
        Get the character limit for this channel.
        
        Returns:
            Optional[int]: Character limit, or None if no limit
        """
        return None
    
    def split_long_message(self, content: str, max_length: int) -> List[str]:
        """
        Split a long message into multiple parts that fit within character limits.
        
        Args:
            content: Message content to split
            max_length: Maximum length per message part
        
        Returns:
            List[str]: List of message parts
        """
        if len(content) <= max_length:
            return [content]
        
        parts = []
        current_part = ""
        
        # Split by sentences to avoid breaking mid-sentence
        sentences = content.replace('. ', '.|').replace('! ', '!|').replace('? ', '?|').split('|')
        
        for sentence in sentences:
            if len(current_part) + len(sentence) + 1 <= max_length:
                current_part += sentence + " "
            else:
                if current_part:
                    parts.append(current_part.strip())
                
                # If single sentence is too long, split by words
                if len(sentence) > max_length:
                    words = sentence.split()
                    current_part = ""
                    for word in words:
                        if len(current_part) + len(word) + 1 <= max_length:
                            current_part += word + " "
                        else:
                            if current_part:
                                parts.append(current_part.strip())
                            current_part = word + " "
                else:
                    current_part = sentence + " "
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
