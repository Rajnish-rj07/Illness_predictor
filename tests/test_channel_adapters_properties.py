"""
Property-based tests for channel adapters.
Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5

Property 18: Channel consistency
Property 19: SMS format compliance
Property 20: Session creation or resumption
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from src.channel.channel_adapter import IncomingMessage, OutgoingMessage
from src.channel.sms_adapter import SMSAdapter
from src.channel.whatsapp_adapter import WhatsAppAdapter
from src.channel.web_adapter import WebAdapter


# Custom strategies for generating test data

@st.composite
def phone_numbers(draw):
    """Generate valid phone numbers."""
    country_code = draw(st.sampled_from(['+1', '+44', '+91', '+86', '+33']))
    number = draw(st.integers(min_value=1000000000, max_value=9999999999))
    return f"{country_code}{number}"


@st.composite
def session_ids(draw):
    """Generate valid session IDs."""
    prefix = draw(st.sampled_from(['session', 'sess', 'sid']))
    suffix = draw(st.text(alphabet=st.characters(whitelist_categories=('Ll', 'Nd')), min_size=8, max_size=32))
    return f"{prefix}-{suffix}"


@st.composite
def user_ids(draw):
    """Generate valid user IDs."""
    prefix = draw(st.sampled_from(['user', 'usr', 'u']))
    suffix = draw(st.integers(min_value=1, max_value=999999))
    return f"{prefix}-{suffix}"


@st.composite
def message_content(draw, max_length=None):
    """Generate message content."""
    if max_length:
        length = draw(st.integers(min_value=1, max_value=max_length))
    else:
        length = draw(st.integers(min_value=1, max_value=5000))
    
    # Generate realistic message content
    sentences = draw(st.lists(
        st.text(alphabet=st.characters(whitelist_categories=('L', 'N', 'P', 'Z')), 
                min_size=10, max_size=100),
        min_size=1,
        max_size=max(1, length // 50)
    ))
    content = '. '.join(sentences)
    return content[:length] if max_length else content


@st.composite
def sms_webhook_payloads(draw):
    """Generate SMS webhook payloads."""
    return {
        'From': draw(phone_numbers()),
        'Body': draw(message_content(max_length=1600)),
        'MessageSid': f"SM{draw(st.text(alphabet='0123456789abcdef', min_size=32, max_size=32))}"
    }


@st.composite
def whatsapp_webhook_payloads(draw):
    """Generate WhatsApp webhook payloads."""
    message_type = draw(st.sampled_from(['text', 'button', 'interactive']))
    
    message_data = {
        'from': draw(phone_numbers()),
        'id': f"wamid.{draw(st.text(alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', min_size=20, max_size=40))}",
        'type': message_type,
        'timestamp': str(draw(st.integers(min_value=1600000000, max_value=1700000000)))
    }
    
    if message_type == 'text':
        message_data['text'] = {'body': draw(message_content(max_length=4096))}
    elif message_type == 'button':
        message_data['button'] = {'text': draw(st.text(min_size=1, max_size=20))}
    elif message_type == 'interactive':
        message_data['interactive'] = {
            'type': 'button_reply',
            'button_reply': {'title': draw(st.text(min_size=1, max_size=20))}
        }
    
    return {
        'entry': [{
            'changes': [{
                'value': {
                    'messages': [message_data]
                }
            }]
        }]
    }


@st.composite
def web_api_payloads(draw):
    """Generate web API request payloads."""
    return {
        'content': draw(message_content()),
        'user_id': draw(user_ids()),
        'session_id': draw(st.one_of(st.none(), session_ids()))
    }


class TestProperty18ChannelConsistency:
    """
    Property 18: Channel consistency
    For any response sent through a channel, it should use the same channel
    as the incoming request.
    
    Validates: Requirements 11.5
    """
    
    @given(
        channel=st.sampled_from(['sms', 'whatsapp', 'web']),
        content=message_content(max_length=500),
        recipient_id=user_ids(),
        session_id=session_ids()
    )
    @settings(max_examples=20)
    def test_property_18_outgoing_message_preserves_channel(
        self, channel, content, recipient_id, session_id
    ):
        """
        Property 18: Channel consistency
        
        For any outgoing message formatted by a channel adapter,
        the message's channel field should match the adapter's channel.
        """
        # Select appropriate adapter
        if channel == 'sms':
            adapter = SMSAdapter()
        elif channel == 'whatsapp':
            adapter = WhatsAppAdapter()
        else:
            adapter = WebAdapter()
        
        # Format outgoing message
        outgoing = adapter.format_outgoing_message(
            content=content,
            recipient_id=recipient_id,
            session_id=session_id
        )
        
        # Verify channel consistency
        assert outgoing.channel == channel, \
            f"Outgoing message channel {outgoing.channel} does not match adapter channel {channel}"
        
        assert outgoing.channel == adapter.get_channel_name(), \
            f"Outgoing message channel {outgoing.channel} does not match adapter name {adapter.get_channel_name()}"
    
    @given(payload=sms_webhook_payloads())
    @settings(max_examples=20)
    def test_property_18_sms_incoming_message_has_correct_channel(self, payload):
        """
        Property 18: Channel consistency (SMS)
        
        For any incoming SMS message, the parsed message should have
        channel='sms'.
        """
        adapter = SMSAdapter()
        incoming = adapter.parse_incoming_message(payload)
        
        assert incoming.channel == 'sms', \
            f"Incoming SMS message has incorrect channel: {incoming.channel}"
    
    @given(payload=whatsapp_webhook_payloads())
    @settings(max_examples=20)
    def test_property_18_whatsapp_incoming_message_has_correct_channel(self, payload):
        """
        Property 18: Channel consistency (WhatsApp)
        
        For any incoming WhatsApp message, the parsed message should have
        channel='whatsapp'.
        """
        adapter = WhatsAppAdapter()
        incoming = adapter.parse_incoming_message(payload)
        
        assert incoming.channel == 'whatsapp', \
            f"Incoming WhatsApp message has incorrect channel: {incoming.channel}"
    
    @given(payload=web_api_payloads())
    @settings(max_examples=20)
    def test_property_18_web_incoming_message_has_correct_channel(self, payload):
        """
        Property 18: Channel consistency (Web)
        
        For any incoming web message, the parsed message should have
        channel='web'.
        """
        adapter = WebAdapter()
        incoming = adapter.parse_incoming_message(payload)
        
        assert incoming.channel == 'web', \
            f"Incoming web message has incorrect channel: {incoming.channel}"


class TestProperty19SMSFormatCompliance:
    """
    Property 19: SMS format compliance
    For any response sent via SMS, the message length should not exceed
    1600 characters (allowing for message concatenation).
    
    Validates: Requirements 11.4
    """
    
    @given(
        content=message_content(),
        recipient_id=phone_numbers(),
        session_id=session_ids()
    )
    @settings(max_examples=20)
    def test_property_19_sms_messages_respect_character_limit(
        self, content, recipient_id, session_id
    ):
        """
        Property 19: SMS format compliance
        
        For any message content, when formatted for SMS, the resulting
        message should not exceed 1600 characters.
        """
        adapter = SMSAdapter()
        
        # Format message
        outgoing = adapter.format_outgoing_message(
            content=content,
            recipient_id=recipient_id,
            session_id=session_id
        )
        
        # Verify character limit
        assert len(outgoing.content) <= SMSAdapter.CONCATENATED_SMS_LIMIT, \
            f"SMS message exceeds limit: {len(outgoing.content)} > {SMSAdapter.CONCATENATED_SMS_LIMIT}"
    
    @given(
        content=st.text(min_size=1, max_size=1600),
        recipient_id=phone_numbers(),
        session_id=session_ids()
    )
    @settings(max_examples=20)
    def test_property_19_valid_sms_messages_pass_validation(
        self, content, recipient_id, session_id
    ):
        """
        Property 19: SMS format compliance (validation)
        
        For any message within the SMS character limit, validation
        should pass.
        """
        adapter = SMSAdapter()
        
        # Validate message
        is_valid, error = adapter.validate_message_format(content)
        
        assert is_valid is True, \
            f"Valid SMS message failed validation: {error}"
        assert error is None
    
    @given(
        content=st.text(min_size=1601, max_size=5000),
    )
    @settings(max_examples=20)
    def test_property_19_oversized_sms_messages_fail_validation(self, content):
        """
        Property 19: SMS format compliance (validation failure)
        
        For any message exceeding the SMS character limit, validation
        should fail.
        """
        adapter = SMSAdapter()
        
        # Validate message
        is_valid, error = adapter.validate_message_format(content)
        
        assert is_valid is False, \
            f"Oversized SMS message passed validation: {len(content)} chars"
        assert error is not None
        assert 'limit' in error.lower()


class TestProperty20SessionCreationOrResumption:
    """
    Property 20: Session creation or resumption
    For any incoming message with a channel identifier, the system should
    either create a new session (if no session_id provided) or resume an
    existing session (if valid session_id provided).
    
    Validates: Requirements 11.3
    """
    
    @given(payload=sms_webhook_payloads())
    @settings(max_examples=20)
    def test_property_20_sms_without_session_id_creates_new_session(self, payload):
        """
        Property 20: Session creation (SMS)
        
        For any incoming SMS message without a session ID, the parsed
        message should have session_id=None, indicating a new session
        should be created.
        """
        adapter = SMSAdapter()
        
        # Ensure payload doesn't contain session marker
        payload['Body'] = payload['Body'].replace('[SESSION:', '').replace(']', '')
        
        incoming = adapter.parse_incoming_message(payload)
        
        # Should not have session_id (new session)
        assert incoming.session_id is None, \
            f"Message without session marker should not have session_id: {incoming.session_id}"
        
        # Should have sender_id for session creation
        assert incoming.sender_id is not None and incoming.sender_id != '', \
            "Message should have sender_id for session creation"
    
    @given(
        payload=sms_webhook_payloads(),
        session_id=session_ids()
    )
    @settings(max_examples=20)
    def test_property_20_sms_with_session_id_resumes_session(self, payload, session_id):
        """
        Property 20: Session resumption (SMS)
        
        For any incoming SMS message with a session ID marker, the parsed
        message should extract and preserve the session_id.
        """
        adapter = SMSAdapter()
        
        # Add session marker to payload
        payload['Body'] = f"{payload['Body']} [SESSION:{session_id}]"
        
        incoming = adapter.parse_incoming_message(payload)
        
        # Should have extracted session_id
        assert incoming.session_id == session_id, \
            f"Session ID not extracted correctly: expected {session_id}, got {incoming.session_id}"
        
        # Session marker should be removed from content
        assert '[SESSION:' not in incoming.content, \
            "Session marker should be removed from message content"
    
    @given(payload=whatsapp_webhook_payloads())
    @settings(max_examples=20)
    def test_property_20_whatsapp_without_session_id_creates_new_session(self, payload):
        """
        Property 20: Session creation (WhatsApp)
        
        For any incoming WhatsApp message without a session ID, the parsed
        message should have session_id=None.
        """
        adapter = WhatsAppAdapter()
        incoming = adapter.parse_incoming_message(payload)
        
        # If no session marker in original message, should be None
        # (We're not adding session markers in the generator)
        if '[SESSION:' not in str(payload):
            assert incoming.session_id is None, \
                f"Message without session marker should not have session_id: {incoming.session_id}"
    
    @given(payload=web_api_payloads())
    @settings(max_examples=20)
    def test_property_20_web_preserves_session_id(self, payload):
        """
        Property 20: Session resumption (Web)
        
        For any incoming web message, the session_id from the payload
        should be preserved in the parsed message.
        """
        adapter = WebAdapter()
        incoming = adapter.parse_incoming_message(payload)
        
        # Session ID should match payload
        assert incoming.session_id == payload.get('session_id'), \
            f"Session ID not preserved: expected {payload.get('session_id')}, got {incoming.session_id}"
    
    @given(
        content=message_content(max_length=500),
        user_id=user_ids(),
        has_session=st.booleans()
    )
    @settings(max_examples=20)
    def test_property_20_web_handles_new_and_existing_sessions(
        self, content, user_id, has_session
    ):
        """
        Property 20: Session creation or resumption (Web)
        
        For any web message, the adapter should correctly handle both
        new sessions (session_id=None) and existing sessions (session_id provided).
        """
        adapter = WebAdapter()
        
        payload = {
            'content': content,
            'user_id': user_id,
            'session_id': f"session-{user_id}" if has_session else None
        }
        
        incoming = adapter.parse_incoming_message(payload)
        
        if has_session:
            assert incoming.session_id is not None, \
                "Existing session should have session_id"
            assert incoming.session_id == payload['session_id']
        else:
            assert incoming.session_id is None, \
                "New session should have session_id=None"


class TestChannelAdapterInvariants:
    """Test invariants that should hold for all channel adapters."""
    
    @given(
        adapter_type=st.sampled_from(['sms', 'whatsapp', 'web']),
        content=message_content(max_length=500),
        recipient_id=user_ids(),
        session_id=session_ids()
    )
    @settings(max_examples=20)
    def test_format_then_validate_consistency(
        self, adapter_type, content, recipient_id, session_id
    ):
        """
        Invariant: Messages formatted by an adapter should pass that
        adapter's validation (after any automatic truncation).
        """
        # Select adapter
        if adapter_type == 'sms':
            adapter = SMSAdapter()
        elif adapter_type == 'whatsapp':
            adapter = WhatsAppAdapter()
        else:
            adapter = WebAdapter()
        
        # Format message
        outgoing = adapter.format_outgoing_message(
            content=content,
            recipient_id=recipient_id,
            session_id=session_id
        )
        
        # Validate formatted message
        is_valid, error = adapter.validate_message_format(outgoing.content)
        
        assert is_valid is True, \
            f"Formatted message failed validation for {adapter_type}: {error}"
    
    @given(
        adapter_type=st.sampled_from(['sms', 'whatsapp', 'web']),
        content=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=20)
    def test_empty_content_always_fails_validation(self, adapter_type, content):
        """
        Invariant: Empty or whitespace-only content should always fail
        validation for any channel.
        """
        # Select adapter
        if adapter_type == 'sms':
            adapter = SMSAdapter()
        elif adapter_type == 'whatsapp':
            adapter = WhatsAppAdapter()
        else:
            adapter = WebAdapter()
        
        # Test with empty string
        is_valid, error = adapter.validate_message_format('')
        assert is_valid is False, f"Empty message should fail validation for {adapter_type}"
        
        # Test with whitespace only
        is_valid, error = adapter.validate_message_format('   ')
        assert is_valid is False, f"Whitespace-only message should fail validation for {adapter_type}"
    
    @given(
        adapter_type=st.sampled_from(['sms', 'whatsapp', 'web'])
    )
    @settings(max_examples=20)
    def test_character_limit_consistency(self, adapter_type):
        """
        Invariant: Character limits should be consistent with specifications.
        """
        if adapter_type == 'sms':
            adapter = SMSAdapter()
            assert adapter.get_character_limit() == 1600
        elif adapter_type == 'whatsapp':
            adapter = WhatsAppAdapter()
            assert adapter.get_character_limit() == 4096
        else:
            adapter = WebAdapter()
            assert adapter.get_character_limit() is None
    
    @given(
        adapter_type=st.sampled_from(['sms', 'whatsapp', 'web'])
    )
    @settings(max_examples=20)
    def test_rich_media_support_consistency(self, adapter_type):
        """
        Invariant: Rich media support should be consistent with specifications.
        """
        if adapter_type == 'sms':
            adapter = SMSAdapter()
            assert adapter.supports_rich_media() is False
        elif adapter_type == 'whatsapp':
            adapter = WhatsAppAdapter()
            assert adapter.supports_rich_media() is True
        else:
            adapter = WebAdapter()
            assert adapter.supports_rich_media() is True
