"""
Webhook endpoints for SMS and WhatsApp integration.

Implements webhook receivers for Twilio SMS and WhatsApp Business API.

Validates: Requirements 11.1, 11.2
"""

from fastapi import APIRouter, HTTPException, status, Form, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

from src.models.data_models import Session, SessionStatus, ConversationContext, SymptomVector, Message

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# Response models
class WebhookResponse(BaseModel):
    """Response model for webhook processing."""
    success: bool
    message: str
    session_id: Optional[str] = None


# Import sessions storage from sessions module
from src.api.routes.sessions import sessions_storage


@router.post("/sms", response_model=WebhookResponse)
async def receive_sms(
    From: str = Form(...),
    Body: str = Form(...),
    MessageSid: Optional[str] = Form(None),
    To: Optional[str] = Form(None)
):
    """
    Receive SMS messages from Twilio.
    
    Validates: Requirements 11.1
    
    Args:
        From: Sender phone number
        Body: Message content
        MessageSid: Twilio message identifier
        To: Recipient phone number
        
    Returns:
        Webhook processing result
    """
    try:
        logger.info(f"Received SMS from {From}: {Body}")
        
        # Find or create session for this phone number
        # In production, implement proper session lookup/creation
        session_id = None
        for sid, session in sessions_storage.items():
            if session.user_id == From and session.channel == 'sms':
                session_id = sid
                break
        
        if not session_id:
            # Create new session
            import uuid
            session_id = str(uuid.uuid4())
            
            now = datetime.utcnow()
            session = Session(
                session_id=session_id,
                user_id=From,  # Use phone number as user_id
                channel='sms',
                language='en',
                created_at=now,
                last_active=now,
                status=SessionStatus.ACTIVE,
                conversation_context=ConversationContext(),
                symptom_vector=SymptomVector()
            )
            sessions_storage[session_id] = session
            logger.info(f"Created new SMS session {session_id} for {From}")
        else:
            # Update existing session
            session = sessions_storage[session_id]
            session.last_active = datetime.utcnow()
            logger.info(f"Resumed SMS session {session_id} for {From}")
        
        # Add message to conversation
        user_message = Message(
            role="user",
            content=Body,
            timestamp=datetime.utcnow()
        )
        session.conversation_context.messages.append(user_message)
        
        # Process message (simplified)
        # In production, integrate with ConversationManager
        response_text = f"SMS received: {Body}"
        
        assistant_message = Message(
            role="assistant",
            content=response_text,
            timestamp=datetime.utcnow()
        )
        session.conversation_context.messages.append(assistant_message)
        
        return WebhookResponse(
            success=True,
            message="SMS processed successfully",
            session_id=session_id
        )
    
    except Exception as e:
        logger.error(f"Failed to process SMS webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process SMS"
        )


@router.post("/whatsapp", response_model=WebhookResponse)
async def receive_whatsapp(request: Request):
    """
    Receive WhatsApp messages from WhatsApp Business API.
    
    Validates: Requirements 11.2
    
    Args:
        request: Raw request with WhatsApp webhook data
        
    Returns:
        Webhook processing result
    """
    try:
        # Parse WhatsApp webhook payload
        data = await request.json()
        
        logger.info(f"Received WhatsApp webhook: {data}")
        
        # Extract message details (format varies by provider)
        # This is a simplified example
        sender = data.get('from', 'unknown')
        message_body = data.get('body', data.get('text', {}).get('body', ''))
        
        if not message_body:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No message body found in webhook"
            )
        
        # Find or create session for this WhatsApp user
        session_id = None
        for sid, session in sessions_storage.items():
            if session.user_id == sender and session.channel == 'whatsapp':
                session_id = sid
                break
        
        if not session_id:
            # Create new session
            import uuid
            session_id = str(uuid.uuid4())
            
            now = datetime.utcnow()
            session = Session(
                session_id=session_id,
                user_id=sender,
                channel='whatsapp',
                language='en',
                created_at=now,
                last_active=now,
                status=SessionStatus.ACTIVE,
                conversation_context=ConversationContext(),
                symptom_vector=SymptomVector()
            )
            sessions_storage[session_id] = session
            logger.info(f"Created new WhatsApp session {session_id} for {sender}")
        else:
            # Update existing session
            session = sessions_storage[session_id]
            session.last_active = datetime.utcnow()
            logger.info(f"Resumed WhatsApp session {session_id} for {sender}")
        
        # Add message to conversation
        user_message = Message(
            role="user",
            content=message_body,
            timestamp=datetime.utcnow()
        )
        session.conversation_context.messages.append(user_message)
        
        # Process message (simplified)
        # In production, integrate with ConversationManager
        response_text = f"WhatsApp received: {message_body}"
        
        assistant_message = Message(
            role="assistant",
            content=response_text,
            timestamp=datetime.utcnow()
        )
        session.conversation_context.messages.append(assistant_message)
        
        return WebhookResponse(
            success=True,
            message="WhatsApp message processed successfully",
            session_id=session_id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process WhatsApp webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process WhatsApp message"
        )


@router.get("/sms/status")
async def sms_webhook_status():
    """
    Health check for SMS webhook endpoint.
    
    Returns:
        Status information
    """
    return {
        "status": "operational",
        "endpoint": "/webhooks/sms",
        "method": "POST"
    }


@router.get("/whatsapp/status")
async def whatsapp_webhook_status():
    """
    Health check for WhatsApp webhook endpoint.
    
    Returns:
        Status information
    """
    return {
        "status": "operational",
        "endpoint": "/webhooks/whatsapp",
        "method": "POST"
    }
