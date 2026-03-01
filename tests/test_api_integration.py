"""
Integration tests for API endpoints.

Tests end-to-end conversation flow, multi-channel routing, and error handling.

Validates: Requirements 1.1, 4.1, 11.1, 11.2
"""

import pytest
from fastapi.testclient import TestClient
from src.api.app import app
from src.api.routes.sessions import sessions_storage
from src.api.routes.webhooks import sessions_storage as webhook_sessions_storage


# Create test client
client = TestClient(app)


class TestSessionEndpoints:
    """Test session management endpoints."""
    
    def setup_method(self):
        """Clear sessions before each test."""
        sessions_storage.clear()
    
    def test_create_session_success(self):
        """Test successful session creation."""
        response = client.post(
            "/sessions",
            json={
                "channel": "web",
                "user_id": "test-user-123",
                "language": "en"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "session_id" in data
        assert data["user_id"] == "test-user-123"
        assert data["channel"] == "web"
        assert data["language"] == "en"
        assert data["status"] == "active"
    
    def test_create_session_invalid_channel(self):
        """Test session creation with invalid channel."""
        response = client.post(
            "/sessions",
            json={
                "channel": "invalid",
                "user_id": "test-user-123",
                "language": "en"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid channel" in (data.get("detail", "") or data.get("error", ""))
    
    def test_send_message_to_session(self):
        """Test sending a message to an active session."""
        # Create session first
        create_response = client.post(
            "/sessions",
            json={
                "channel": "web",
                "user_id": "test-user-123",
                "language": "en"
            }
        )
        session_id = create_response.json()["session_id"]
        
        # Send message
        message_response = client.post(
            f"/sessions/{session_id}/messages",
            json={"message": "I have a headache"}
        )
        
        assert message_response.status_code == 200
        data = message_response.json()
        
        assert data["session_id"] == session_id
        assert "response" in data
        assert data["session_status"] == "active"
    
    def test_send_message_to_nonexistent_session(self):
        """Test sending message to non-existent session."""
        response = client.post(
            "/sessions/nonexistent-id/messages",
            json={"message": "test"}
        )
        
        assert response.status_code == 404
        data = response.json()
        error_msg = (data.get("detail", "") or data.get("error", "")).lower()
        assert "not found" in error_msg
    
    def test_get_session_state(self):
        """Test retrieving session state."""
        # Create session
        create_response = client.post(
            "/sessions",
            json={
                "channel": "web",
                "user_id": "test-user-123",
                "language": "en"
            }
        )
        session_id = create_response.json()["session_id"]
        
        # Get session state
        state_response = client.get(f"/sessions/{session_id}")
        
        assert state_response.status_code == 200
        data = state_response.json()
        
        assert data["session_id"] == session_id
        assert data["user_id"] == "test-user-123"
        assert data["channel"] == "web"
        assert "message_count" in data
        assert "symptom_count" in data
        assert "question_count" in data
    
    def test_get_nonexistent_session(self):
        """Test retrieving non-existent session."""
        response = client.get("/sessions/nonexistent-id")
        
        assert response.status_code == 404
    
    def test_delete_session(self):
        """Test deleting a session."""
        # Create session
        create_response = client.post(
            "/sessions",
            json={
                "channel": "web",
                "user_id": "test-user-123",
                "language": "en"
            }
        )
        session_id = create_response.json()["session_id"]
        
        # Delete session
        delete_response = client.delete(f"/sessions/{session_id}")
        
        assert delete_response.status_code == 204
        
        # Verify session is deleted
        get_response = client.get(f"/sessions/{session_id}")
        assert get_response.status_code == 404
    
    def test_delete_nonexistent_session(self):
        """Test deleting non-existent session."""
        response = client.delete("/sessions/nonexistent-id")
        
        assert response.status_code == 404


class TestWebhookEndpoints:
    """Test webhook endpoints."""
    
    def setup_method(self):
        """Clear sessions before each test."""
        webhook_sessions_storage.clear()
    
    def test_sms_webhook_creates_session(self):
        """Test that SMS webhook creates a new session."""
        response = client.post(
            "/webhooks/sms",
            data={
                "From": "+1234567890",
                "Body": "I have a fever",
                "MessageSid": "SM123456"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "session_id" in data
    
    def test_sms_webhook_resumes_existing_session(self):
        """Test that SMS webhook resumes existing session."""
        # First message creates session
        response1 = client.post(
            "/webhooks/sms",
            data={
                "From": "+1234567890",
                "Body": "I have a fever"
            }
        )
        session_id_1 = response1.json()["session_id"]
        
        # Second message should resume same session
        response2 = client.post(
            "/webhooks/sms",
            data={
                "From": "+1234567890",
                "Body": "And a cough"
            }
        )
        session_id_2 = response2.json()["session_id"]
        
        assert session_id_1 == session_id_2
    
    def test_whatsapp_webhook_creates_session(self):
        """Test that WhatsApp webhook creates a new session."""
        response = client.post(
            "/webhooks/whatsapp",
            json={
                "from": "whatsapp:+1234567890",
                "body": "I have a headache"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "session_id" in data
    
    def test_whatsapp_webhook_with_text_body(self):
        """Test WhatsApp webhook with nested text body."""
        response = client.post(
            "/webhooks/whatsapp",
            json={
                "from": "whatsapp:+1234567890",
                "text": {
                    "body": "I have a headache"
                }
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
    
    def test_whatsapp_webhook_missing_body(self):
        """Test WhatsApp webhook with missing message body."""
        response = client.post(
            "/webhooks/whatsapp",
            json={
                "from": "whatsapp:+1234567890"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        error_msg = data.get("detail", "") or data.get("error", "")
        assert "No message body" in error_msg
    
    def test_sms_webhook_status(self):
        """Test SMS webhook status endpoint."""
        response = client.get("/webhooks/sms/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "operational"
        assert data["endpoint"] == "/webhooks/sms"
    
    def test_whatsapp_webhook_status(self):
        """Test WhatsApp webhook status endpoint."""
        response = client.get("/webhooks/whatsapp/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "operational"
        assert data["endpoint"] == "/webhooks/whatsapp"


class TestEndToEndConversationFlow:
    """Test complete end-to-end conversation flows."""
    
    def setup_method(self):
        """Clear sessions before each test."""
        sessions_storage.clear()
    
    def test_complete_web_conversation_flow(self):
        """Test complete conversation flow via web channel."""
        # 1. Create session
        create_response = client.post(
            "/sessions",
            json={
                "channel": "web",
                "user_id": "test-user-web",
                "language": "en"
            }
        )
        assert create_response.status_code == 201
        session_id = create_response.json()["session_id"]
        
        # 2. Send initial symptom message
        msg1_response = client.post(
            f"/sessions/{session_id}/messages",
            json={"message": "I have a fever and headache"}
        )
        assert msg1_response.status_code == 200
        
        # 3. Send follow-up message
        msg2_response = client.post(
            f"/sessions/{session_id}/messages",
            json={"message": "Yes, for 2 days"}
        )
        assert msg2_response.status_code == 200
        
        # 4. Get session state
        state_response = client.get(f"/sessions/{session_id}")
        assert state_response.status_code == 200
        state_data = state_response.json()
        assert state_data["message_count"] >= 4  # 2 user + 2 assistant
        
        # 5. Delete session
        delete_response = client.delete(f"/sessions/{session_id}")
        assert delete_response.status_code == 204
    
    def test_sms_conversation_flow(self):
        """Test conversation flow via SMS channel."""
        phone = "+1234567890"
        
        # First SMS
        response1 = client.post(
            "/webhooks/sms",
            data={
                "From": phone,
                "Body": "I have a fever"
            }
        )
        assert response1.status_code == 200
        session_id = response1.json()["session_id"]
        
        # Second SMS (should use same session)
        response2 = client.post(
            "/webhooks/sms",
            data={
                "From": phone,
                "Body": "And a cough"
            }
        )
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id
    
    def test_whatsapp_conversation_flow(self):
        """Test conversation flow via WhatsApp channel."""
        user_id = "whatsapp:+1234567890"
        
        # First message
        response1 = client.post(
            "/webhooks/whatsapp",
            json={
                "from": user_id,
                "body": "I have a headache"
            }
        )
        assert response1.status_code == 200
        session_id = response1.json()["session_id"]
        
        # Second message (should use same session)
        response2 = client.post(
            "/webhooks/whatsapp",
            json={
                "from": user_id,
                "body": "It's been 3 days"
            }
        )
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id


class TestMultiChannelRouting:
    """Test multi-channel message routing."""
    
    def setup_method(self):
        """Clear sessions before each test."""
        sessions_storage.clear()
        webhook_sessions_storage.clear()
    
    def test_separate_sessions_per_channel(self):
        """Test that different channels create separate sessions."""
        user_id = "test-user"
        
        # Create web session
        web_response = client.post(
            "/sessions",
            json={
                "channel": "web",
                "user_id": user_id,
                "language": "en"
            }
        )
        web_session_id = web_response.json()["session_id"]
        
        # Create SMS session (via webhook)
        sms_response = client.post(
            "/webhooks/sms",
            data={
                "From": user_id,
                "Body": "Test message"
            }
        )
        sms_session_id = sms_response.json()["session_id"]
        
        # Sessions should be different
        assert web_session_id != sms_session_id
    
    def test_channel_specific_session_lookup(self):
        """Test that sessions are looked up by channel."""
        phone = "+1234567890"
        
        # Send SMS
        sms_response = client.post(
            "/webhooks/sms",
            data={
                "From": phone,
                "Body": "SMS message"
            }
        )
        sms_session_id = sms_response.json()["session_id"]
        
        # Send WhatsApp from same number
        wa_response = client.post(
            "/webhooks/whatsapp",
            json={
                "from": phone,
                "body": "WhatsApp message"
            }
        )
        wa_session_id = wa_response.json()["session_id"]
        
        # Should create separate sessions
        assert sms_session_id != wa_session_id


class TestErrorHandling:
    """Test error handling across endpoints."""
    
    def setup_method(self):
        """Clear sessions before each test."""
        sessions_storage.clear()
    
    def test_invalid_json_payload(self):
        """Test handling of invalid JSON payload."""
        response = client.post(
            "/sessions",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        response = client.post(
            "/sessions",
            json={"channel": "web"}  # Missing user_id
        )
        
        assert response.status_code == 422
    
    def test_empty_message_body(self):
        """Test handling of empty message body."""
        # Create session
        create_response = client.post(
            "/sessions",
            json={
                "channel": "web",
                "user_id": "test-user",
                "language": "en"
            }
        )
        session_id = create_response.json()["session_id"]
        
        # Try to send empty message
        response = client.post(
            f"/sessions/{session_id}/messages",
            json={"message": ""}
        )
        
        assert response.status_code == 422


class TestAPIDocumentation:
    """Test API documentation endpoints."""
    
    def test_openapi_schema_accessible(self):
        """Test that OpenAPI schema is accessible."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        
        assert "openapi" in schema
        assert "paths" in schema
    
    def test_docs_endpoint_accessible(self):
        """Test that Swagger docs are accessible."""
        response = client.get("/docs")
        
        assert response.status_code == 200
    
    def test_redoc_endpoint_accessible(self):
        """Test that ReDoc is accessible."""
        response = client.get("/redoc")
        
        assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
