"""
Unit tests for channel adapters.
Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.channel.channel_adapter import ChannelAdapter, IncomingMessage, OutgoingMessage
from src.channel.sms_adapter import SMSAdapter
from src.channel.whatsapp_adapter import WhatsAppAdapter
from src.channel.web_adapter import WebAdapter


class TestChannelAdapterBase:
    """Test base ChannelAdapter functionality."""
    
    def test_split_long_message_short_content(self):
        """Test that short messages are not split."""
        adapter = WebAdapter()  # Use concrete implementation
        content = "This is a short message"
        parts = adapter.split_long_message(content, max_length=100)
        
        assert len(parts) == 1
        assert parts[0] == content
    
    def test_split_long_message_by_sentences(self):
        """Test that long messages are split by sentences."""
        adapter = WebAdapter()
        content = "First sentence. Second sentence. Third sentence. Fourth sentence."
        parts = adapter.split_long_message(content, max_length=30)
        
        assert len(parts) > 1
        # Each part should be within limit
        for part in parts:
            assert len(part) <= 30
    
    def test_split_long_message_by_words(self):
        """Test that very long sentences are split by words."""
        adapter = WebAdapter()
        content = "word " * 50  # 250 characters
        parts = adapter.split_long_message(content, max_length=50)
        
        assert len(parts) > 1
        for part in parts:
            assert len(part) <= 50


class TestSMSAdapter:
    """Test SMS adapter functionality."""
    
    def test_initialization_with_credentials(self):
        """Test SMS adapter initialization with credentials."""
        adapter = SMSAdapter(
            account_sid='test_sid',
            auth_token='test_token',
            from_number='+1234567890'
        )
        
        assert adapter.channel_name == 'sms'
        assert adapter.account_sid == 'test_sid'
        assert adapter.auth_token == 'test_token'
        assert adapter.from_number == '+1234567890'
    
    def test_initialization_without_credentials(self):
        """Test SMS adapter initialization without credentials (test mode)."""
        adapter = SMSAdapter()
        
        assert adapter.channel_name == 'sms'
        assert adapter.client is None
    
    def test_parse_incoming_message_basic(self):
        """Test parsing basic SMS webhook payload."""
        adapter = SMSAdapter()
        raw_message = {
            'From': '+1234567890',
            'Body': 'I have a headache',
            'MessageSid': 'SM123456'
        }
        
        incoming = adapter.parse_incoming_message(raw_message)
        
        assert incoming.content == 'I have a headache'
        assert incoming.sender_id == '+1234567890'
        assert incoming.channel == 'sms'
        assert incoming.session_id is None
        assert incoming.metadata['message_sid'] == 'SM123456'
    
    def test_parse_incoming_message_with_session_id(self):
        """Test parsing SMS with embedded session ID."""
        adapter = SMSAdapter()
        raw_message = {
            'From': '+1234567890',
            'Body': 'Yes [SESSION:abc-123]',
            'MessageSid': 'SM123456'
        }
        
        incoming = adapter.parse_incoming_message(raw_message)
        
        assert incoming.content == 'Yes'
        assert incoming.session_id == 'abc-123'
    
    def test_format_outgoing_message_basic(self):
        """Test formatting basic SMS message."""
        adapter = SMSAdapter(from_number='+1234567890')
        
        outgoing = adapter.format_outgoing_message(
            content='Your prediction is ready',
            recipient_id='+0987654321',
            session_id='session-123'
        )
        
        assert outgoing.content == 'Your prediction is ready'
        assert outgoing.recipient_id == '+0987654321'
        assert outgoing.channel == 'sms'
        assert outgoing.session_id == 'session-123'
    
    def test_format_outgoing_message_with_session_id(self):
        """Test formatting SMS with session ID included."""
        adapter = SMSAdapter(from_number='+1234567890')
        
        outgoing = adapter.format_outgoing_message(
            content='Your prediction is ready',
            recipient_id='+0987654321',
            session_id='session-123',
            include_session_id=True
        )
        
        assert '[SESSION:session-123]' in outgoing.content
    
    def test_format_outgoing_message_truncates_long_content(self):
        """Test that overly long SMS content is truncated."""
        adapter = SMSAdapter(from_number='+1234567890')
        long_content = 'x' * 2000  # Exceeds 1600 char limit
        
        outgoing = adapter.format_outgoing_message(
            content=long_content,
            recipient_id='+0987654321',
            session_id='session-123'
        )
        
        assert len(outgoing.content) <= SMSAdapter.CONCATENATED_SMS_LIMIT
        assert outgoing.content.endswith('...')
    
    def test_validate_message_format_valid(self):
        """Test validation of valid SMS message."""
        adapter = SMSAdapter()
        is_valid, error = adapter.validate_message_format('Valid message')
        
        assert is_valid is True
        assert error is None
    
    def test_validate_message_format_empty(self):
        """Test validation of empty SMS message."""
        adapter = SMSAdapter()
        is_valid, error = adapter.validate_message_format('')
        
        assert is_valid is False
        assert 'empty' in error.lower()
    
    def test_validate_message_format_too_long(self):
        """Test validation of overly long SMS message."""
        adapter = SMSAdapter()
        long_message = 'x' * 2000
        is_valid, error = adapter.validate_message_format(long_message)
        
        assert is_valid is False
        assert 'limit' in error.lower()
    
    def test_get_character_limit(self):
        """Test getting SMS character limit."""
        adapter = SMSAdapter()
        assert adapter.get_character_limit() == 1600
    
    def test_supports_rich_media(self):
        """Test that SMS does not support rich media."""
        adapter = SMSAdapter()
        assert adapter.supports_rich_media() is False
    
    @patch('src.channel.sms_adapter.Client')
    def test_send_message_success(self, mock_client_class):
        """Test successful SMS sending."""
        # Setup mock
        mock_client = Mock()
        mock_message = Mock()
        mock_message.sid = 'SM123456'
        mock_client.messages.create.return_value = mock_message
        mock_client_class.return_value = mock_client
        
        adapter = SMSAdapter(
            account_sid='test_sid',
            auth_token='test_token',
            from_number='+1234567890'
        )
        
        message = OutgoingMessage(
            content='Test message',
            recipient_id='+0987654321',
            channel='sms',
            session_id='session-123'
        )
        
        result = adapter.send_message(message)
        
        assert result is True
        mock_client.messages.create.assert_called_once()
    
    def test_send_message_no_client(self):
        """Test sending SMS without initialized client."""
        adapter = SMSAdapter()  # No credentials
        
        message = OutgoingMessage(
            content='Test message',
            recipient_id='+0987654321',
            channel='sms',
            session_id='session-123'
        )
        
        result = adapter.send_message(message)
        
        assert result is False


class TestWhatsAppAdapter:
    """Test WhatsApp adapter functionality."""
    
    def test_initialization_with_credentials(self):
        """Test WhatsApp adapter initialization with credentials."""
        adapter = WhatsAppAdapter(
            access_token='test_token',
            phone_number_id='123456'
        )
        
        assert adapter.channel_name == 'whatsapp'
        assert adapter.access_token == 'test_token'
        assert adapter.phone_number_id == '123456'
    
    def test_initialization_without_credentials(self):
        """Test WhatsApp adapter initialization without credentials."""
        adapter = WhatsAppAdapter()
        
        assert adapter.channel_name == 'whatsapp'
    
    def test_parse_incoming_message_text(self):
        """Test parsing WhatsApp text message."""
        adapter = WhatsAppAdapter()
        raw_message = {
            'entry': [{
                'changes': [{
                    'value': {
                        'messages': [{
                            'from': '1234567890',
                            'id': 'wamid.123',
                            'type': 'text',
                            'text': {
                                'body': 'I have a fever'
                            },
                            'timestamp': '1234567890'
                        }]
                    }
                }]
            }]
        }
        
        incoming = adapter.parse_incoming_message(raw_message)
        
        assert incoming.content == 'I have a fever'
        assert incoming.sender_id == '1234567890'
        assert incoming.channel == 'whatsapp'
        assert incoming.metadata['message_id'] == 'wamid.123'
        assert incoming.metadata['message_type'] == 'text'
    
    def test_parse_incoming_message_button_reply(self):
        """Test parsing WhatsApp button reply."""
        adapter = WhatsAppAdapter()
        raw_message = {
            'entry': [{
                'changes': [{
                    'value': {
                        'messages': [{
                            'from': '1234567890',
                            'id': 'wamid.123',
                            'type': 'interactive',
                            'interactive': {
                                'type': 'button_reply',
                                'button_reply': {
                                    'title': 'Yes'
                                }
                            }
                        }]
                    }
                }]
            }]
        }
        
        incoming = adapter.parse_incoming_message(raw_message)
        
        assert incoming.content == 'Yes'
        assert incoming.metadata['message_type'] == 'interactive'
    
    def test_parse_incoming_message_with_session_id(self):
        """Test parsing WhatsApp message with session ID."""
        adapter = WhatsAppAdapter()
        raw_message = {
            'entry': [{
                'changes': [{
                    'value': {
                        'messages': [{
                            'from': '1234567890',
                            'id': 'wamid.123',
                            'type': 'text',
                            'text': {
                                'body': 'Yes [SESSION:abc-123]'
                            }
                        }]
                    }
                }]
            }]
        }
        
        incoming = adapter.parse_incoming_message(raw_message)
        
        assert incoming.content == 'Yes'
        assert incoming.session_id == 'abc-123'
    
    def test_parse_incoming_message_invalid_payload(self):
        """Test parsing invalid WhatsApp payload."""
        adapter = WhatsAppAdapter()
        raw_message = {'invalid': 'payload'}
        
        incoming = adapter.parse_incoming_message(raw_message)
        
        # Should return default message instead of crashing
        assert incoming.sender_id == 'unknown'
        assert 'error' in incoming.metadata
    
    def test_format_outgoing_message_basic(self):
        """Test formatting basic WhatsApp message."""
        adapter = WhatsAppAdapter()
        
        outgoing = adapter.format_outgoing_message(
            content='Your prediction is ready',
            recipient_id='1234567890',
            session_id='session-123'
        )
        
        assert outgoing.content == 'Your prediction is ready'
        assert outgoing.recipient_id == '1234567890'
        assert outgoing.channel == 'whatsapp'
        assert outgoing.metadata['message_type'] == 'text'
    
    def test_format_outgoing_message_with_buttons(self):
        """Test formatting WhatsApp message with buttons."""
        adapter = WhatsAppAdapter()
        
        outgoing = adapter.format_outgoing_message(
            content='Do you have a fever?',
            recipient_id='1234567890',
            session_id='session-123',
            buttons=['Yes', 'No', 'Not sure']
        )
        
        assert outgoing.metadata['message_type'] == 'interactive'
        assert outgoing.metadata['buttons'] == ['Yes', 'No', 'Not sure']
    
    def test_format_outgoing_message_truncates_long_content(self):
        """Test that overly long WhatsApp content is truncated."""
        adapter = WhatsAppAdapter()
        long_content = 'x' * 5000  # Exceeds 4096 char limit
        
        outgoing = adapter.format_outgoing_message(
            content=long_content,
            recipient_id='1234567890',
            session_id='session-123'
        )
        
        assert len(outgoing.content) <= WhatsAppAdapter.MESSAGE_LIMIT
    
    def test_validate_message_format_valid(self):
        """Test validation of valid WhatsApp message."""
        adapter = WhatsAppAdapter()
        is_valid, error = adapter.validate_message_format('Valid message')
        
        assert is_valid is True
        assert error is None
    
    def test_validate_message_format_empty(self):
        """Test validation of empty WhatsApp message."""
        adapter = WhatsAppAdapter()
        is_valid, error = adapter.validate_message_format('')
        
        assert is_valid is False
        assert 'empty' in error.lower()
    
    def test_validate_message_format_too_long(self):
        """Test validation of overly long WhatsApp message."""
        adapter = WhatsAppAdapter()
        long_message = 'x' * 5000
        is_valid, error = adapter.validate_message_format(long_message)
        
        assert is_valid is False
        assert 'limit' in error.lower()
    
    def test_get_character_limit(self):
        """Test getting WhatsApp character limit."""
        adapter = WhatsAppAdapter()
        assert adapter.get_character_limit() == 4096
    
    def test_supports_rich_media(self):
        """Test that WhatsApp supports rich media."""
        adapter = WhatsAppAdapter()
        assert adapter.supports_rich_media() is True
    
    @patch('src.channel.whatsapp_adapter.requests.post')
    def test_send_message_success(self, mock_post):
        """Test successful WhatsApp message sending."""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = {
            'messages': [{'id': 'wamid.123'}]
        }
        mock_post.return_value = mock_response
        
        adapter = WhatsAppAdapter(
            access_token='test_token',
            phone_number_id='123456'
        )
        
        message = OutgoingMessage(
            content='Test message',
            recipient_id='1234567890',
            channel='whatsapp',
            session_id='session-123',
            metadata={'message_type': 'text'}
        )
        
        result = adapter.send_message(message)
        
        assert result is True
        mock_post.assert_called_once()
    
    @patch('src.channel.whatsapp_adapter.requests.post')
    def test_send_message_with_buttons(self, mock_post):
        """Test sending WhatsApp message with buttons."""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = {
            'messages': [{'id': 'wamid.123'}]
        }
        mock_post.return_value = mock_response
        
        adapter = WhatsAppAdapter(
            access_token='test_token',
            phone_number_id='123456'
        )
        
        message = OutgoingMessage(
            content='Do you have a fever?',
            recipient_id='1234567890',
            channel='whatsapp',
            session_id='session-123',
            metadata={
                'message_type': 'interactive',
                'buttons': ['Yes', 'No']
            }
        )
        
        result = adapter.send_message(message)
        
        assert result is True
        # Verify interactive payload was sent
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        assert payload['type'] == 'interactive'
    
    def test_send_message_no_credentials(self):
        """Test sending WhatsApp message without credentials."""
        adapter = WhatsAppAdapter()  # No credentials
        
        message = OutgoingMessage(
            content='Test message',
            recipient_id='1234567890',
            channel='whatsapp',
            session_id='session-123'
        )
        
        result = adapter.send_message(message)
        
        assert result is False


class TestWebAdapter:
    """Test Web adapter functionality."""
    
    def test_initialization(self):
        """Test Web adapter initialization."""
        adapter = WebAdapter()
        
        assert adapter.channel_name == 'web'
    
    def test_parse_incoming_message_basic(self):
        """Test parsing basic web API request."""
        adapter = WebAdapter()
        raw_message = {
            'content': 'I have a headache',
            'user_id': 'user-123',
            'session_id': 'session-456'
        }
        
        incoming = adapter.parse_incoming_message(raw_message)
        
        assert incoming.content == 'I have a headache'
        assert incoming.sender_id == 'user-123'
        assert incoming.channel == 'web'
        assert incoming.session_id == 'session-456'
    
    def test_parse_incoming_message_with_metadata(self):
        """Test parsing web request with metadata."""
        adapter = WebAdapter()
        raw_message = {
            'content': 'I have a headache',
            'user_id': 'user-123',
            'ip_address': '192.168.1.1',
            'user_agent': 'Mozilla/5.0'
        }
        
        incoming = adapter.parse_incoming_message(raw_message)
        
        assert incoming.metadata['ip_address'] == '192.168.1.1'
        assert incoming.metadata['user_agent'] == 'Mozilla/5.0'
    
    def test_format_outgoing_message_basic(self):
        """Test formatting basic web response."""
        adapter = WebAdapter()
        
        outgoing = adapter.format_outgoing_message(
            content='Your prediction is ready',
            recipient_id='user-123',
            session_id='session-456'
        )
        
        assert outgoing.content == 'Your prediction is ready'
        assert outgoing.recipient_id == 'user-123'
        assert outgoing.channel == 'web'
        assert outgoing.metadata['format_type'] == 'plain'
    
    def test_format_outgoing_message_with_structured_data(self):
        """Test formatting web response with structured data."""
        adapter = WebAdapter()
        
        structured_data = {
            'predictions': [
                {'illness': 'flu', 'confidence': 0.85}
            ]
        }
        
        outgoing = adapter.format_outgoing_message(
            content='Your prediction is ready',
            recipient_id='user-123',
            session_id='session-456',
            format_type='json',
            structured_data=structured_data
        )
        
        assert outgoing.metadata['format_type'] == 'json'
        assert outgoing.metadata['structured_data'] == structured_data
    
    def test_validate_message_format_valid(self):
        """Test validation of valid web message."""
        adapter = WebAdapter()
        is_valid, error = adapter.validate_message_format('Valid message')
        
        assert is_valid is True
        assert error is None
    
    def test_validate_message_format_empty(self):
        """Test validation of empty web message."""
        adapter = WebAdapter()
        is_valid, error = adapter.validate_message_format('')
        
        assert is_valid is False
        assert 'empty' in error.lower()
    
    def test_get_character_limit(self):
        """Test that web has no character limit."""
        adapter = WebAdapter()
        assert adapter.get_character_limit() is None
    
    def test_supports_rich_media(self):
        """Test that web supports rich media."""
        adapter = WebAdapter()
        assert adapter.supports_rich_media() is True
    
    def test_send_message(self):
        """Test web message sending (always succeeds)."""
        adapter = WebAdapter()
        
        message = OutgoingMessage(
            content='Test message',
            recipient_id='user-123',
            channel='web',
            session_id='session-456'
        )
        
        result = adapter.send_message(message)
        
        assert result is True
    
    def test_format_response(self):
        """Test formatting complete API response."""
        adapter = WebAdapter()
        
        message = OutgoingMessage(
            content='Your prediction is ready',
            recipient_id='user-123',
            channel='web',
            session_id='session-456',
            metadata={
                'format_type': 'json',
                'structured_data': {'test': 'data'}
            }
        )
        
        response = adapter.format_response(message)
        
        assert response['session_id'] == 'session-456'
        assert response['message'] == 'Your prediction is ready'
        assert response['channel'] == 'web'
        assert response['format_type'] == 'json'
        assert response['data'] == {'test': 'data'}
    
    def test_format_response_with_additional_data(self):
        """Test formatting API response with additional data."""
        adapter = WebAdapter()
        
        message = OutgoingMessage(
            content='Test',
            recipient_id='user-123',
            channel='web',
            session_id='session-456'
        )
        
        additional_data = {
            'status': 'success',
            'timestamp': '2024-01-01T00:00:00Z'
        }
        
        response = adapter.format_response(message, additional_data)
        
        assert response['status'] == 'success'
        assert response['timestamp'] == '2024-01-01T00:00:00Z'


class TestChannelConsistency:
    """Test channel consistency across adapters."""
    
    def test_all_adapters_have_channel_name(self):
        """Test that all adapters have correct channel names."""
        sms = SMSAdapter()
        whatsapp = WhatsAppAdapter()
        web = WebAdapter()
        
        assert sms.get_channel_name() == 'sms'
        assert whatsapp.get_channel_name() == 'whatsapp'
        assert web.get_channel_name() == 'web'
    
    def test_all_adapters_implement_required_methods(self):
        """Test that all adapters implement required methods."""
        adapters = [SMSAdapter(), WhatsAppAdapter(), WebAdapter()]
        
        for adapter in adapters:
            # Check all required methods exist
            assert hasattr(adapter, 'parse_incoming_message')
            assert hasattr(adapter, 'format_outgoing_message')
            assert hasattr(adapter, 'send_message')
            assert hasattr(adapter, 'validate_message_format')
            assert hasattr(adapter, 'get_character_limit')
            assert hasattr(adapter, 'supports_rich_media')
    
    def test_character_limits_are_correct(self):
        """Test that character limits match specifications."""
        sms = SMSAdapter()
        whatsapp = WhatsAppAdapter()
        web = WebAdapter()
        
        assert sms.get_character_limit() == 1600
        assert whatsapp.get_character_limit() == 4096
        assert web.get_character_limit() is None
    
    def test_rich_media_support(self):
        """Test rich media support flags."""
        sms = SMSAdapter()
        whatsapp = WhatsAppAdapter()
        web = WebAdapter()
        
        assert sms.supports_rich_media() is False
        assert whatsapp.supports_rich_media() is True
        assert web.supports_rich_media() is True
