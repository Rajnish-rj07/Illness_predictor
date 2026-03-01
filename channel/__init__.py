"""
Channel adapters for multi-channel communication support.
Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5
"""

from src.channel.channel_adapter import ChannelAdapter
from src.channel.sms_adapter import SMSAdapter
from src.channel.whatsapp_adapter import WhatsAppAdapter
from src.channel.web_adapter import WebAdapter

__all__ = [
    'ChannelAdapter',
    'SMSAdapter',
    'WhatsAppAdapter',
    'WebAdapter',
]
