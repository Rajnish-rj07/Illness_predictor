"""
ConversationManager for orchestrating user interactions.

This module implements the central orchestrator for all user interactions across channels.
It integrates with SessionManager, LLM client, QuestionEngine, and PredictionService to
provide a complete conversational experience.

Validates: Requirements 1.1, 4.1, 4.4, 4.5, 10.1, 10.3
"""

import logging
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime

from src.models.data_models import (
    Session,
    Message,
    SymptomVector,
    SymptomInfo,
    Prediction,
    ConversationContext,
)
from src.session.session_manager import SessionManager
from src.llm.llm_client import LLMClient, LLMError
from src.llm.symptom_extractor import SymptomExtractor, ExtractionResult
from src.question_engine.question_engine import QuestionEngine, Question
from src.prediction.prediction_service import PredictionService
from src.ml.ml_model_service import MLModelService

logger = logging.getLogger(__name__)


@dataclass
class ConversationResponse:
    """Response from conversation manager to user."""
    message: str
    predictions: Optional[List[Prediction]] = None
    session_id: Optional[str] = None
    is_complete: bool = False
    needs_clarification: bool = False


class ConversationManager:
    """
    Central orchestrator for user conversations.
    
    Responsibilities:
    - Create and manage user sessions
    - Parse user messages using LLM
    - Extract symptoms from natural language
    - Route to Question Engine or Prediction Service
    - Maintain conversation context
    - Handle off-topic messages with redirection
    - Detect confusion and trigger rephrasing
    
    Validates: Requirements 1.1, 4.1, 4.4, 4.5, 10.1, 10.3
    """
    
    # Keywords for detecting off-topic messages
    OFF_TOPIC_KEYWORDS = [
        'weather', 'sports', 'politics', 'news', 'movie', 'music',
        'game', 'recipe', 'joke', 'story', 'celebrity', 'stock',
        'cryptocurrency', 'bitcoin', 'shopping', 'restaurant'
    ]
    
    # Keywords for detecting confusion
    CONFUSION_KEYWORDS = [
        "don't understand", "confused", "what do you mean", "unclear",
        "not sure", "don't know", "can you explain", "rephrase",
        "what", "huh", "??", "clarify"
    ]
    
    def __init__(
        self,
        session_manager: Optional[SessionManager] = None,
        llm_client: Optional[LLMClient] = None,
        question_engine: Optional[QuestionEngine] = None,
        prediction_service: Optional[PredictionService] = None,
    ):
        """
        Initialize ConversationManager.
        
        Args:
            session_manager: SessionManager instance for session lifecycle
            llm_client: LLM client for natural language processing
            question_engine: QuestionEngine for intelligent questioning
            prediction_service: PredictionService for illness predictions
        """
        self.session_manager = session_manager or SessionManager()
        self.llm_client = llm_client or LLMClient()
        self.symptom_extractor = SymptomExtractor(self.llm_client)
        self.question_engine = question_engine or QuestionEngine()
        
        # Initialize prediction service with ML model service
        if prediction_service is None:
            ml_model_service = MLModelService()
            self.prediction_service = PredictionService(ml_model_service)
        else:
            self.prediction_service = prediction_service
        
        logger.info("ConversationManager initialized")
    
    def start_session(
        self,
        channel: str,
        user_id: str,
        language: str = "en"
    ) -> ConversationResponse:
        """
        Start a new conversation session.
        
        Initiates a conversation requesting initial symptoms.
        
        Args:
            channel: Communication channel ('sms', 'whatsapp', 'web')
            user_id: Anonymized user identifier
            language: User's preferred language (default: 'en')
            
        Returns:
            ConversationResponse with welcome message and session ID
            
        Validates: Requirements 1.1, 10.1
        """
        logger.info(f"Starting new session for user {user_id} on channel {channel}")
        
        # Create new session
        session = self.session_manager.start_session(
            channel=channel,
            user_id=user_id,
            language=language
        )
        
        # Create welcome message
        welcome_message = self._generate_welcome_message(language)
        
        # Add welcome message to conversation context
        session.conversation_context.messages.append(
            Message(role="assistant", content=welcome_message)
        )
        
        # Update session
        self.session_manager.update_session(session)
        
        logger.info(f"Session started: {session.session_id}")
        
        return ConversationResponse(
            message=welcome_message,
            session_id=session.session_id,
            is_complete=False
        )
    
    async def process_message(
        self,
        session_id: str,
        message: str
    ) -> ConversationResponse:
        """
        Process a user message within a session.
        
        This method:
        1. Resumes the session
        2. Adds user message to conversation context
        3. Checks for off-topic or confusion
        4. Extracts symptoms from message
        5. Updates symptom vector
        6. Generates next question or triggers prediction
        7. Returns appropriate response
        
        Args:
            session_id: Unique session identifier
            message: User's message
            
        Returns:
            ConversationResponse with system response
            
        Validates: Requirements 4.1, 4.4, 4.5
        """
        logger.info(f"Processing message for session {session_id}")
        
        # Resume session
        session = self.session_manager.resume_session(session_id)
        
        if session is None:
            logger.warning(f"Session not found or expired: {session_id}")
            return ConversationResponse(
                message="Your session has expired. Please start a new conversation.",
                is_complete=True
            )
        
        # Add user message to conversation context (Requirement 4.1)
        session.conversation_context.messages.append(
            Message(role="user", content=message)
        )
        
        # Check for off-topic messages (Requirement 4.4)
        if self._is_off_topic(message):
            response_message = self._handle_off_topic(session.language)
            session.conversation_context.messages.append(
                Message(role="assistant", content=response_message)
            )
            self.session_manager.update_session(session)
            
            return ConversationResponse(
                message=response_message,
                session_id=session_id,
                is_complete=False
            )
        
        # Check for confusion (Requirement 4.5)
        if self._is_confused(message):
            response_message = await self._handle_confusion(session)
            session.conversation_context.messages.append(
                Message(role="assistant", content=response_message)
            )
            self.session_manager.update_session(session)
            
            return ConversationResponse(
                message=response_message,
                session_id=session_id,
                is_complete=False,
                needs_clarification=True
            )
        
        # Extract symptoms from message
        try:
            extraction_result = await self.symptom_extractor.extract_symptoms(
                message=message,
                context=session.symptom_vector,
                conversation_history=self._get_conversation_history(session)
            )
        except LLMError as e:
            logger.error(f"Failed to extract symptoms: {e}")
            error_message = (
                "I'm having trouble understanding your message. "
                "Could you please rephrase it?"
            )
            session.conversation_context.messages.append(
                Message(role="assistant", content=error_message)
            )
            self.session_manager.update_session(session)
            
            return ConversationResponse(
                message=error_message,
                session_id=session_id,
                is_complete=False
            )
        
        # Check if message is health-related
        if not extraction_result.is_health_related:
            response_message = self._handle_off_topic(session.language)
            session.conversation_context.messages.append(
                Message(role="assistant", content=response_message)
            )
            self.session_manager.update_session(session)
            
            return ConversationResponse(
                message=response_message,
                session_id=session_id,
                is_complete=False
            )
        
        # Update symptom vector with extracted symptoms
        session.symptom_vector = self.symptom_extractor.merge_with_existing(
            session.symptom_vector,
            extraction_result.symptoms
        )
        
        # Update extracted symptoms list in context
        for symptom_name in extraction_result.symptoms.keys():
            if symptom_name not in session.conversation_context.extracted_symptoms:
                session.conversation_context.extracted_symptoms.append(symptom_name)
        
        # Check if clarification is needed
        if extraction_result.clarifying_questions:
            clarification_message = self._format_clarification_questions(
                extraction_result.clarifying_questions
            )
            session.conversation_context.messages.append(
                Message(role="assistant", content=clarification_message)
            )
            self.session_manager.update_session(session)
            
            return ConversationResponse(
                message=clarification_message,
                session_id=session_id,
                is_complete=False,
                needs_clarification=True
            )
        
        # Increment question count if this was a response to a question
        if len(session.conversation_context.messages) > 2:
            prev_message = session.conversation_context.messages[-2]
            if prev_message.role == "assistant" and "?" in prev_message.content:
                session.symptom_vector.question_count += 1
        
        # Check if we should stop questioning and generate prediction
        if self.question_engine.should_stop_questioning(
            session.symptom_vector,
            session.symptom_vector.question_count
        ):
            # Generate predictions
            response = await self._generate_predictions(session)
            self.session_manager.update_session(session)
            return response
        
        # Generate next question
        next_question = self.question_engine.generate_next_question(
            session.symptom_vector,
            self._get_qa_history(session)
        )
        
        if next_question is None:
            # No more questions, generate predictions
            response = await self._generate_predictions(session)
            self.session_manager.update_session(session)
            return response
        
        # Format question naturally
        question_message = self._format_question(next_question, session.language)
        
        session.conversation_context.messages.append(
            Message(role="assistant", content=question_message)
        )
        
        # Update session
        self.session_manager.update_session(session)
        
        logger.info(f"Generated next question for session {session_id}")
        
        return ConversationResponse(
            message=question_message,
            session_id=session_id,
            is_complete=False
        )
    
    def resume_session(self, session_id: str) -> Optional[Session]:
        """
        Resume an existing session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Session object or None if not found/expired
            
        Validates: Requirement 10.3
        """
        logger.info(f"Resuming session: {session_id}")
        return self.session_manager.resume_session(session_id)
    
    def end_session(self, session_id: str) -> bool:
        """
        End a conversation session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if session was successfully ended, False otherwise
        """
        logger.info(f"Ending session: {session_id}")
        return self.session_manager.end_session(session_id)
    
    def _generate_welcome_message(self, language: str = "en") -> str:
        """
        Generate welcome message for new session.
        
        Args:
            language: User's preferred language
            
        Returns:
            Welcome message string
        """
        # For now, only English is implemented
        # TODO: Add multi-language support in Task 14
        return (
            "Hello! I'm here to help you understand your symptoms. "
            "Please describe any symptoms you're experiencing, and I'll ask some "
            "follow-up questions to provide you with potential illness predictions.\n\n"
            "⚠️ Important: This is for informational purposes only and does not "
            "replace professional medical advice. If you have a medical emergency, "
            "please call emergency services immediately.\n\n"
            "What symptoms are you experiencing?"
        )
    
    def _is_off_topic(self, message: str) -> bool:
        """
        Check if message is off-topic (not health-related).
        
        Validates: Requirement 4.4
        
        Args:
            message: User's message
            
        Returns:
            True if message appears off-topic, False otherwise
        """
        message_lower = message.lower()
        
        # Check for off-topic keywords
        for keyword in self.OFF_TOPIC_KEYWORDS:
            if keyword in message_lower:
                logger.debug(f"Off-topic keyword detected: {keyword}")
                return True
        
        return False
    
    def _is_confused(self, message: str) -> bool:
        """
        Check if user is expressing confusion.
        
        Validates: Requirement 4.5
        
        Args:
            message: User's message
            
        Returns:
            True if user appears confused, False otherwise
        """
        message_lower = message.lower()
        
        # Check for confusion keywords
        for keyword in self.CONFUSION_KEYWORDS:
            if keyword in message_lower:
                logger.debug(f"Confusion keyword detected: {keyword}")
                return True
        
        return False
    
    def _handle_off_topic(self, language: str = "en") -> str:
        """
        Generate response for off-topic messages.
        
        Validates: Requirement 4.4
        
        Args:
            language: User's preferred language
            
        Returns:
            Redirection message
        """
        return (
            "I appreciate your message, but I'm specifically designed to help with "
            "health-related symptoms and illness predictions. "
            "Could you please tell me about any symptoms you're experiencing? "
            "For example, do you have a fever, cough, headache, or any other "
            "physical symptoms?"
        )
    
    async def _handle_confusion(self, session: Session) -> str:
        """
        Handle user confusion by rephrasing the last question.
        
        Validates: Requirement 4.5
        
        Args:
            session: Current session
            
        Returns:
            Rephrased question or explanation
        """
        # Get the last assistant message (question)
        last_question = None
        for message in reversed(session.conversation_context.messages):
            if message.role == "assistant":
                last_question = message.content
                break
        
        if last_question is None:
            return (
                "I'm here to help you understand your symptoms. "
                "Please describe any physical symptoms you're experiencing, "
                "such as pain, fever, cough, or any other health concerns."
            )
        
        # Rephrase the question with examples
        rephrased = (
            f"Let me rephrase that. {last_question}\n\n"
            "For example, you can answer with 'yes', 'no', or provide more details "
            "about your symptoms."
        )
        
        return rephrased
    
    def _format_clarification_questions(self, questions: List[str]) -> str:
        """
        Format clarification questions for user.
        
        Args:
            questions: List of clarification questions
            
        Returns:
            Formatted message with questions
        """
        if len(questions) == 1:
            return questions[0]
        
        message = "I need a bit more information:\n\n"
        for i, question in enumerate(questions, 1):
            message += f"{i}. {question}\n"
        
        return message.strip()
    
    def _format_question(self, question: Question, language: str = "en") -> str:
        """
        Format question naturally for user.
        
        Args:
            question: Question object from QuestionEngine
            language: User's preferred language
            
        Returns:
            Formatted question string
        """
        # For now, just return the question text
        # TODO: Add more natural formatting and multi-language support
        return question.question_text
    
    async def _generate_predictions(self, session: Session) -> ConversationResponse:
        """
        Generate illness predictions and format response.
        
        Args:
            session: Current session
            
        Returns:
            ConversationResponse with predictions
        """
        logger.info(f"Generating predictions for session {session.session_id}")
        
        # Generate predictions
        predictions = self.prediction_service.predict(
            symptom_vector=session.symptom_vector,
            language=session.language
        )
        
        # Format results
        if predictions:
            result_message = self.prediction_service.format_results(
                predictions,
                language=session.language
            )
        else:
            result_message = (
                "Based on your symptoms, I'm unable to provide confident predictions. "
                "This could mean:\n"
                "- Your symptoms don't match common illness patterns\n"
                "- More specific information is needed\n"
                "- You should consult a healthcare professional for proper evaluation\n\n"
                "Please seek medical attention if your symptoms are concerning or persistent."
            )
        
        # Add to conversation context
        session.conversation_context.messages.append(
            Message(role="assistant", content=result_message)
        )
        
        # Mark session as ready for completion
        # (User can still provide feedback, but prediction phase is done)
        
        logger.info(f"Generated {len(predictions)} predictions for session {session.session_id}")
        
        return ConversationResponse(
            message=result_message,
            predictions=predictions,
            session_id=session.session_id,
            is_complete=True
        )
    
    def _get_conversation_history(self, session: Session) -> List[Dict[str, str]]:
        """
        Get conversation history in format suitable for LLM.
        
        Args:
            session: Current session
            
        Returns:
            List of message dicts with 'role' and 'content'
        """
        return [
            {"role": msg.role, "content": msg.content}
            for msg in session.conversation_context.messages
        ]
    
    def _get_qa_history(self, session: Session) -> List:
        """
        Get question-answer history for QuestionEngine.
        
        Args:
            session: Current session
            
        Returns:
            List of QA pairs
        """
        # For now, return empty list
        # TODO: Implement proper QA extraction from conversation context
        return []
    
    async def close(self):
        """Close LLM client connection."""
        await self.symptom_extractor.close()
