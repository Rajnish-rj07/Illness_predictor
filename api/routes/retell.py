"""
Retell AI Integration for Illness Prediction System.

This module provides endpoints for integrating with Retell AI's voice agent platform.
Supports both webhook and WebSocket connections for real-time voice conversations.
"""

from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import asyncio

from src.conversation.conversation_manager import ConversationManager
from src.models.data_models import Prediction

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/retell", tags=["Retell AI"])

# Initialize ConversationManager
conversation_manager = ConversationManager()


# Pydantic Models for Retell AI
class RetellMessage(BaseModel):
    """Message from Retell AI."""
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class RetellChatRequest(BaseModel):
    """Request from Retell AI Custom LLM."""
    call_id: str = Field(..., description="Unique call identifier")
    user_message: str = Field(..., description="User's spoken message")
    conversation_history: Optional[List[RetellMessage]] = Field(default=[], description="Previous messages")
    language: Optional[str] = Field(default="en", description="Language code")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")


class RetellChatResponse(BaseModel):
    """Response to Retell AI."""
    response: str = Field(..., description="Voice-optimized response text")
    end_call: bool = Field(default=False, description="Whether to end the call")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")


class RetellToolCall(BaseModel):
    """Tool call request from Retell AI."""
    call_id: str = Field(..., description="Unique call identifier")
    tool_name: str = Field(..., description="Name of the tool to call")
    parameters: Dict[str, Any] = Field(..., description="Tool parameters")


class RetellToolResponse(BaseModel):
    """Tool call response to Retell AI."""
    result: str = Field(..., description="Voice-optimized result")
    success: bool = Field(default=True, description="Whether the tool call succeeded")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")


# Session storage for Retell calls
retell_sessions = {}


@router.post("/chat", response_model=RetellChatResponse)
async def retell_chat(request: RetellChatRequest):
    """
    Main endpoint for Retell AI Custom LLM integration.
    
    This endpoint receives voice transcriptions from Retell AI and returns
    voice-optimized responses for the illness prediction conversation.
    
    Args:
        request: Retell chat request with user message and context
        
    Returns:
        Voice-optimized response for TTS
    """
    try:
        logger.info(f"Retell chat request for call {request.call_id}")
        
        # Get or create session for this call
        session_id = retell_sessions.get(request.call_id)
        
        if not session_id:
            # Start new session
            response = conversation_manager.start_session(
                channel="voice",
                user_id=request.call_id,
                language=request.language or "en"
            )
            session_id = response.session_id
            retell_sessions[request.call_id] = session_id
            
            # Return welcome message
            voice_response = format_for_voice(response.message, request.language)
            
            return RetellChatResponse(
                response=voice_response,
                end_call=False,
                metadata={"session_id": session_id}
            )
        
        # Process user message
        response = await conversation_manager.process_message(
            session_id=session_id,
            message=request.user_message
        )
        
        # Format response for voice
        voice_response = format_for_voice(
            response.message,
            request.language,
            predictions=response.predictions
        )
        
        # Check if conversation is complete
        end_call = response.is_complete
        
        logger.info(f"Retell response for call {request.call_id}: {len(voice_response)} chars")
        
        return RetellChatResponse(
            response=voice_response,
            end_call=end_call,
            metadata={
                "session_id": session_id,
                "has_predictions": response.predictions is not None,
                "is_complete": response.is_complete
            }
        )
    
    except Exception as e:
        logger.error(f"Error in retell_chat: {str(e)}", exc_info=True)
        
        # Return graceful error message for voice
        error_message = format_error_for_voice(str(e), request.language)
        
        return RetellChatResponse(
            response=error_message,
            end_call=False,
            metadata={"error": str(e)}
        )


@router.post("/tool/predict-illness", response_model=RetellToolResponse)
async def predict_illness_tool(request: RetellToolCall):
    """
    Retell AI Custom Tool for illness prediction.
    
    This endpoint is called when Retell AI's function calling triggers
    the illness prediction tool.
    
    Args:
        request: Tool call request with symptoms
        
    Returns:
        Voice-optimized prediction results
    """
    try:
        logger.info(f"Illness prediction tool called for {request.call_id}")
        
        # Get session
        session_id = retell_sessions.get(request.call_id)
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found for this call"
            )
        
        # Extract symptoms from parameters
        symptoms = request.parameters.get("symptoms", "")
        
        # Process symptoms and get predictions
        response = await conversation_manager.process_message(
            session_id=session_id,
            message=symptoms
        )
        
        # Format predictions for voice
        if response.predictions:
            result = format_predictions_for_voice(
                response.predictions,
                request.parameters.get("language", "en")
            )
        else:
            result = "I'm still gathering information about your symptoms. Let me ask you a few more questions."
        
        return RetellToolResponse(
            result=result,
            success=True,
            metadata={
                "prediction_count": len(response.predictions) if response.predictions else 0
            }
        )
    
    except Exception as e:
        logger.error(f"Error in predict_illness_tool: {str(e)}", exc_info=True)
        
        return RetellToolResponse(
            result=format_error_for_voice(str(e), request.parameters.get("language", "en")),
            success=False,
            metadata={"error": str(e)}
        )


@router.post("/end-call")
async def end_retell_call(call_id: str):
    """
    Clean up session when Retell call ends.
    
    Args:
        call_id: Retell call identifier
    """
    try:
        session_id = retell_sessions.get(call_id)
        if session_id:
            conversation_manager.end_session(session_id)
            del retell_sessions[call_id]
            logger.info(f"Ended Retell call {call_id}")
        
        return {"status": "success", "call_id": call_id}
    
    except Exception as e:
        logger.error(f"Error ending call: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/health")
async def retell_health():
    """Health check for Retell integration."""
    return {
        "status": "healthy",
        "active_calls": len(retell_sessions),
        "timestamp": datetime.utcnow().isoformat()
    }


# Helper Functions

def format_for_voice(text: str, language: str = "en", predictions: Optional[List[Prediction]] = None) -> str:
    """
    Format text for voice/TTS output.
    
    Makes the response more natural for spoken conversation by:
    - Removing markdown formatting
    - Simplifying technical terms
    - Adding natural pauses
    - Making it more conversational
    
    Args:
        text: Original text
        language: Language code
        predictions: Optional predictions to include
        
    Returns:
        Voice-optimized text
    """
    # Remove markdown formatting
    voice_text = text.replace("**", "").replace("*", "")
    voice_text = voice_text.replace("#", "").replace("`", "")
    
    # Remove emoji (they don't work well in TTS)
    emoji_map = {
        "🟢": "low severity",
        "🟡": "moderate severity",
        "🟠": "high severity",
        "🔴": "critical severity",
        "⚠️": "",
        "🚨": "urgent",
    }
    for emoji, replacement in emoji_map.items():
        voice_text = voice_text.replace(emoji, replacement)
    
    # Simplify bullet points
    voice_text = voice_text.replace("- ", ". ")
    voice_text = voice_text.replace("• ", ". ")
    
    # Add natural pauses
    voice_text = voice_text.replace("\n\n", ". ")
    voice_text = voice_text.replace("\n", ". ")
    
    # Remove multiple spaces
    voice_text = " ".join(voice_text.split())
    
    # Make more conversational
    voice_text = voice_text.replace("Please", "")
    voice_text = voice_text.replace("Could you", "Can you")
    
    # Limit length for voice (max ~200 words)
    words = voice_text.split()
    if len(words) > 200:
        voice_text = " ".join(words[:200]) + "..."
    
    return voice_text.strip()


def format_predictions_for_voice(predictions: List[Prediction], language: str = "en") -> str:
    """
    Format predictions for voice output.
    
    Creates a natural, spoken summary of predictions that's easy to understand
    when spoken aloud.
    
    Args:
        predictions: List of predictions
        language: Language code
        
    Returns:
        Voice-optimized prediction summary
    """
    if not predictions:
        return "I don't have enough information to make a prediction yet."
    
    # Start with intro
    if len(predictions) == 1:
        intro = "Based on your symptoms, the most likely condition is"
    else:
        intro = f"Based on your symptoms, here are the {len(predictions)} most likely conditions."
    
    # Format each prediction
    prediction_texts = []
    for i, pred in enumerate(predictions[:3], 1):  # Max 3 for voice
        illness_name = pred.illness.replace("_", " ").title()
        confidence = int(pred.confidence_score * 100)
        severity = pred.severity.value
        
        # Create natural sentence
        if i == 1:
            text = f"{illness_name}, with {confidence} percent confidence. This is {severity} severity."
        else:
            text = f"Number {i}, {illness_name}, at {confidence} percent confidence."
        
        prediction_texts.append(text)
    
    # Combine
    result = intro + " " + " ".join(prediction_texts)
    
    # Add disclaimer
    result += " Remember, this is for informational purposes only. Please consult a healthcare professional for proper diagnosis."
    
    # Add emergency warning if critical
    if any(p.severity.value == "critical" for p in predictions):
        result += " Important: Your symptoms may indicate a serious condition. Please seek immediate medical attention."
    
    return result


def format_error_for_voice(error: str, language: str = "en") -> str:
    """
    Format error message for voice output.
    
    Args:
        error: Error message
        language: Language code
        
    Returns:
        User-friendly voice error message
    """
    # Generic friendly error messages
    friendly_errors = {
        "en": "I'm sorry, I'm having trouble processing that right now. Could you please rephrase your symptoms?",
        "es": "Lo siento, tengo problemas para procesar eso ahora. ¿Podrías reformular tus síntomas?",
        "fr": "Désolé, j'ai du mal à traiter cela maintenant. Pourriez-vous reformuler vos symptômes?",
        "hi": "क्षमा करें, मुझे अभी इसे संसाधित करने में परेशानी हो रही है। क्या आप अपने लक्षणों को फिर से बता सकते हैं?",
    }
    
    return friendly_errors.get(language, friendly_errors["en"])
