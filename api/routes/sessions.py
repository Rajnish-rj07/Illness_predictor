"""
Session and conversation endpoints for the Illness Prediction System API.

Implements REST endpoints for managing conversation sessions and processing messages.

Validates: Requirements 1.1, 4.1, 9.5, 10.1, 10.3
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging
import asyncio

from src.models.data_models import Session, SessionStatus, ConversationContext, SymptomVector, Prediction
from src.api.app import verify_api_key
from src.conversation.conversation_manager import ConversationManager

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/sessions", tags=["Sessions"])

# Initialize ConversationManager (singleton)
conversation_manager = ConversationManager()

# Legacy sessions_storage for backward compatibility with webhooks
# TODO: Update webhooks to use ConversationManager
sessions_storage = {}


# Request/Response models
class CreateSessionRequest(BaseModel):
    """Request model for creating a new session."""
    channel: str = Field(..., description="Communication channel (sms, whatsapp, web)")
    user_id: str = Field(..., description="Anonymized user identifier")
    language: str = Field(default="en", description="Preferred language code")


class SessionResponse(BaseModel):
    """Response model for session information."""
    session_id: str
    user_id: str
    channel: str
    language: str
    status: str
    created_at: str
    last_active: str
    message: str


class SendMessageRequest(BaseModel):
    """Request model for sending a message."""
    message: str = Field(..., description="User message content", min_length=1)


class PredictionResponse(BaseModel):
    """Response model for a single prediction."""
    illness: str
    confidence_score: float
    severity: str
    treatment_medications: Optional[List[str]] = None
    treatment_non_medication: Optional[List[str]] = None
    treatment_disclaimer: Optional[str] = None


class MessageResponse(BaseModel):
    """Response model for message processing."""
    session_id: str
    response: str
    predictions: Optional[List[PredictionResponse]] = None
    requires_input: bool = True
    session_status: str
    is_complete: bool = False


class SessionStateResponse(BaseModel):
    """Response model for session state."""
    session_id: str
    user_id: str
    channel: str
    language: str
    status: str
    created_at: str
    last_active: str
    message_count: int
    symptom_count: int
    question_count: int


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Create a new conversation session.
    
    Validates: Requirements 10.1
    
    Args:
        request: Session creation request
        api_key: API key for authentication
        
    Returns:
        Session information with welcome message
        
    Raises:
        HTTPException: If session creation fails
    """
    try:
        # Validate channel
        valid_channels = ['sms', 'whatsapp', 'web']
        if request.channel not in valid_channels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid channel. Must be one of: {', '.join(valid_channels)}"
            )
        
        # Start session using ConversationManager
        response = conversation_manager.start_session(
            channel=request.channel,
            user_id=request.user_id,
            language=request.language
        )
        
        # Get the session to extract details
        session = conversation_manager.resume_session(response.session_id)
        
        logger.info(f"Created session {response.session_id} for user {request.user_id}")
        
        return SessionResponse(
            session_id=response.session_id,
            user_id=session.user_id,
            channel=session.channel,
            language=session.language,
            status=session.status.value,
            created_at=session.created_at.isoformat(),
            last_active=session.last_active.isoformat(),
            message=response.message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session"
        )


@router.post("/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Send a message in a conversation session.
    
    Validates: Requirements 1.1, 4.1
    
    Args:
        session_id: Session identifier
        request: Message request
        api_key: API key for authentication
        
    Returns:
        Message response with system reply and predictions (if ready)
        
    Raises:
        HTTPException: If session not found or message processing fails
    """
    try:
        # Process message using ConversationManager
        response = await conversation_manager.process_message(
            session_id=session_id,
            message=request.message
        )
        
        # Convert predictions to response format
        predictions_response = None
        if response.predictions:
            predictions_response = [
                PredictionResponse(
                    illness=pred.illness,
                    confidence_score=pred.confidence_score,
                    severity=pred.severity.value,
                    treatment_medications=pred.treatment_suggestions.medications if pred.treatment_suggestions else None,
                    treatment_non_medication=pred.treatment_suggestions.non_medication if pred.treatment_suggestions else None,
                    treatment_disclaimer=pred.treatment_suggestions.disclaimer if pred.treatment_suggestions else None
                )
                for pred in response.predictions
            ]
        
        # Get session status
        session = conversation_manager.resume_session(session_id)
        session_status = session.status.value if session else "unknown"
        
        logger.info(f"Processed message in session {session_id}")
        
        return MessageResponse(
            session_id=session_id,
            response=response.message,
            predictions=predictions_response,
            requires_input=not response.is_complete,
            session_status=session_status,
            is_complete=response.is_complete
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/{session_id}", response_model=SessionStateResponse)
async def get_session(
    session_id: str,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Get session state and information.
    
    Validates: Requirements 10.3
    
    Args:
        session_id: Session identifier
        api_key: API key for authentication
        
    Returns:
        Session state information
        
    Raises:
        HTTPException: If session not found
    """
    try:
        # Get session using ConversationManager
        session = conversation_manager.resume_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        logger.info(f"Retrieved session {session_id}")
        
        return SessionStateResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            channel=session.channel,
            language=session.language,
            status=session.status.value,
            created_at=session.created_at.isoformat(),
            last_active=session.last_active.isoformat(),
            message_count=len(session.conversation_context.messages),
            symptom_count=len(session.symptom_vector.symptoms),
            question_count=session.symptom_vector.question_count
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session"
        )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    api_key: Optional[str] = Depends(verify_api_key)
):
    """
    Delete session data.
    
    Validates: Requirements 9.5
    
    Args:
        session_id: Session identifier
        api_key: API key for authentication
        
    Raises:
        HTTPException: If session not found
    """
    try:
        # Delete session using ConversationManager
        deleted = conversation_manager.session_manager.delete_session(session_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        logger.info(f"Deleted session {session_id}")
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete session"
        )
