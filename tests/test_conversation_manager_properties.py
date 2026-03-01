"""
Property-based tests for ConversationManager.

Tests universal properties that should hold across all valid inputs:
- Property 15: Context accumulation
- Property 16: Off-topic redirection

Validates: Requirements 4.1, 4.4
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.conversation.conversation_manager import ConversationManager, ConversationResponse
from src.models.data_models import (
    Session,
    SessionStatus,
    ConversationContext,
    SymptomVector,
    SymptomInfo,
    Message,
    Prediction,
    Severity,
    TreatmentInfo,
)
from src.session.session_manager import SessionManager
from src.llm.llm_client import LLMClient
from src.llm.symptom_extractor import ExtractionResult
from src.question_engine.question_engine import QuestionEngine, Question
from src.prediction.prediction_service import PredictionService


# Custom strategies for generating test data
@st.composite
def health_related_messages(draw):
    """Generate health-related messages."""
    symptoms = [
        "fever", "cough", "headache", "fatigue", "nausea", "vomiting",
        "diarrhea", "sore throat", "runny nose", "body aches", "chills",
        "shortness of breath", "chest pain", "dizziness", "weakness"
    ]
    
    templates = [
        "I have {symptom}",
        "I'm experiencing {symptom}",
        "I've had {symptom} for a few days",
        "My {symptom} is getting worse",
        "I feel {symptom}",
        "I have a {symptom}",
        "I'm suffering from {symptom}",
    ]
    
    symptom = draw(st.sampled_from(symptoms))
    template = draw(st.sampled_from(templates))
    
    return template.format(symptom=symptom)


@st.composite
def off_topic_messages(draw):
    """Generate off-topic (non-health) messages."""
    templates = [
        "What's the weather like today?",
        "Who won the game yesterday?",
        "Tell me a joke",
        "What's the latest news?",
        "Can you recommend a good movie?",
        "What's the stock market doing?",
        "Tell me about cryptocurrency",
        "What's a good recipe for dinner?",
        "Who is your favorite celebrity?",
        "What music do you like?",
    ]
    
    return draw(st.sampled_from(templates))


@st.composite
def sessions(draw):
    """Generate valid Session objects."""
    session_id = f"test-{draw(st.integers(min_value=1000, max_value=9999))}"
    user_id = f"user-{draw(st.integers(min_value=100, max_value=999))}"
    channel = draw(st.sampled_from(["web", "sms", "whatsapp"]))
    language = draw(st.sampled_from(["en", "es", "fr"]))
    
    now = datetime.utcnow()
    
    # Generate some messages for context
    num_messages = draw(st.integers(min_value=0, max_value=5))
    messages = []
    for i in range(num_messages):
        role = "user" if i % 2 == 0 else "assistant"
        content = draw(st.text(min_size=5, max_size=100))
        messages.append(Message(role=role, content=content, timestamp=now))
    
    context = ConversationContext(messages=messages)
    
    return Session(
        session_id=session_id,
        user_id=user_id,
        channel=channel,
        language=language,
        created_at=now,
        last_active=now,
        status=SessionStatus.ACTIVE,
        conversation_context=context,
        symptom_vector=SymptomVector()
    )


def create_mock_conversation_manager():
    """Create ConversationManager with mocked dependencies."""
    mock_session_manager = Mock(spec=SessionManager)
    mock_llm_client = Mock(spec=LLMClient)
    mock_question_engine = Mock(spec=QuestionEngine)
    mock_prediction_service = Mock(spec=PredictionService)
    
    manager = ConversationManager(
        session_manager=mock_session_manager,
        llm_client=mock_llm_client,
        question_engine=mock_question_engine,
        prediction_service=mock_prediction_service
    )
    
    return manager, mock_session_manager


class TestProperty15ContextAccumulation:
    """
    Property 15: Context accumulation
    
    For any sequence of messages in a session, the Conversation_Context should
    contain all previous messages and extracted information.
    
    Validates: Requirement 4.1
    """
    
    @given(
        session=sessions(),
        messages=st.lists(
            health_related_messages(),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_property_15_context_accumulation(self, session, messages):
        """
        Feature: illness-prediction-system, Property 15: Context accumulation
        
        For any sequence of messages in a session, the Conversation_Context should
        contain all previous messages and extracted information.
        
        **Validates: Requirements 4.1**
        """
        # Arrange
        manager, mock_session_manager = create_mock_conversation_manager()
        
        # Track initial message count
        initial_message_count = len(session.conversation_context.messages)
        
        # Mock session manager to return our session
        mock_session_manager.resume_session.return_value = session
        mock_session_manager.update_session.return_value = True
        
        # Mock symptom extraction to return health-related results
        with patch.object(
            manager.symptom_extractor,
            'extract_symptoms',
            new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = ExtractionResult(
                symptoms={"fever": SymptomInfo(present=True)},
                needs_clarification=[],
                is_health_related=True,
                clarifying_questions=[]
            )
            
            # Mock merge
            manager.symptom_extractor.merge_with_existing = Mock(
                return_value=SymptomVector(
                    symptoms={"fever": SymptomInfo(present=True)}
                )
            )
            
            # Mock question engine
            manager.question_engine.should_stop_questioning = Mock(return_value=False)
            manager.question_engine.generate_next_question = Mock(
                return_value=Question(
                    symptom="cough",
                    question_text="Do you have a cough?",
                    information_gain=0.5
                )
            )
            
            # Act - Process each message
            for i, message in enumerate(messages):
                await manager.process_message(session.session_id, message)
                
                # Assert - Context should accumulate
                # Each message adds 2 messages: user message + assistant response
                expected_count = initial_message_count + (i + 1) * 2
                actual_count = len(session.conversation_context.messages)
                
                assert actual_count == expected_count, (
                    f"After {i+1} messages, expected {expected_count} messages in context, "
                    f"but got {actual_count}"
                )
                
                # Verify all previous user messages are present
                user_messages = [
                    msg for msg in session.conversation_context.messages
                    if msg.role == "user"
                ]
                
                # Should have initial user messages + new ones
                initial_user_count = sum(
                    1 for msg in session.conversation_context.messages[:initial_message_count]
                    if msg.role == "user"
                )
                expected_user_count = initial_user_count + (i + 1)
                
                assert len(user_messages) == expected_user_count, (
                    f"Expected {expected_user_count} user messages, got {len(user_messages)}"
                )
                
                # Verify the current message is in the context
                assert any(
                    msg.content == message and msg.role == "user"
                    for msg in session.conversation_context.messages
                ), f"Message '{message}' not found in conversation context"


class TestProperty16OffTopicRedirection:
    """
    Property 16: Off-topic redirection
    
    For any message that does not contain health-related information, the system
    should acknowledge the message and redirect the conversation to symptom gathering.
    
    Validates: Requirement 4.4
    """
    
    @given(
        session=sessions(),
        off_topic_message=off_topic_messages()
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_property_16_off_topic_redirection(self, session, off_topic_message):
        """
        Feature: illness-prediction-system, Property 16: Off-topic redirection
        
        For any message that does not contain health-related information, the system
        should acknowledge the message and redirect the conversation to symptom gathering.
        
        **Validates: Requirements 4.4**
        """
        # Arrange
        manager, mock_session_manager = create_mock_conversation_manager()
        
        # Mock session manager
        mock_session_manager.resume_session.return_value = session
        mock_session_manager.update_session.return_value = True
        
        # Act
        response = await manager.process_message(session.session_id, off_topic_message)
        
        # Assert - Response should redirect to health topics
        assert not response.is_complete, (
            "Off-topic message should not complete the session"
        )
        
        # Response should mention health or symptoms
        response_lower = response.message.lower()
        health_keywords = ["health", "symptom", "illness", "medical", "condition"]
        
        assert any(keyword in response_lower for keyword in health_keywords), (
            f"Off-topic response should redirect to health topics. "
            f"Response: {response.message}"
        )
        
        # Should not trigger predictions
        assert response.predictions is None, (
            "Off-topic message should not trigger predictions"
        )
        
        # Message should be added to context
        user_messages = [
            msg for msg in session.conversation_context.messages
            if msg.role == "user" and msg.content == off_topic_message
        ]
        
        assert len(user_messages) > 0, (
            "Off-topic message should be added to conversation context"
        )
    
    @given(
        session=sessions(),
        health_message=health_related_messages()
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_property_16_health_messages_not_redirected(self, session, health_message):
        """
        Test that health-related messages are NOT redirected.
        
        This is the inverse property - health messages should be processed normally.
        """
        # Arrange
        manager, mock_session_manager = create_mock_conversation_manager()
        
        # Mock session manager
        mock_session_manager.resume_session.return_value = session
        mock_session_manager.update_session.return_value = True
        
        # Mock symptom extraction to return health-related results
        with patch.object(
            manager.symptom_extractor,
            'extract_symptoms',
            new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = ExtractionResult(
                symptoms={"fever": SymptomInfo(present=True)},
                needs_clarification=[],
                is_health_related=True,
                clarifying_questions=[]
            )
            
            # Mock merge
            manager.symptom_extractor.merge_with_existing = Mock(
                return_value=SymptomVector(
                    symptoms={"fever": SymptomInfo(present=True)}
                )
            )
            
            # Mock question engine
            manager.question_engine.should_stop_questioning = Mock(return_value=False)
            manager.question_engine.generate_next_question = Mock(
                return_value=Question(
                    symptom="cough",
                    question_text="Do you have a cough?",
                    information_gain=0.5
                )
            )
            
            # Act
            response = await manager.process_message(session.session_id, health_message)
            
            # Assert - Should NOT be a redirection message
            # Redirection messages contain specific keywords
            response_lower = response.message.lower()
            redirection_phrases = [
                "specifically designed",
                "appreciate your message",
                "could you please tell me about"
            ]
            
            is_redirection = any(phrase in response_lower for phrase in redirection_phrases)
            
            assert not is_redirection, (
                f"Health-related message should not trigger redirection. "
                f"Message: {health_message}, Response: {response.message}"
            )
            
            # Should call symptom extraction
            mock_extract.assert_called_once()


class TestHelperMethodProperties:
    """Property tests for helper methods."""
    
    @given(message=st.text(min_size=1, max_size=200))
    @settings(max_examples=20)
    def test_off_topic_detection_consistency(self, message):
        """
        Test that off-topic detection is consistent.
        
        The same message should always produce the same result.
        """
        manager, _ = create_mock_conversation_manager()
        
        # Call twice
        result1 = manager._is_off_topic(message)
        result2 = manager._is_off_topic(message)
        
        # Should be consistent
        assert result1 == result2, (
            f"Off-topic detection should be consistent for message: {message}"
        )
    
    @given(message=st.text(min_size=1, max_size=200))
    @settings(max_examples=20)
    def test_confusion_detection_consistency(self, message):
        """
        Test that confusion detection is consistent.
        
        The same message should always produce the same result.
        """
        manager, _ = create_mock_conversation_manager()
        
        # Call twice
        result1 = manager._is_confused(message)
        result2 = manager._is_confused(message)
        
        # Should be consistent
        assert result1 == result2, (
            f"Confusion detection should be consistent for message: {message}"
        )
    
    @given(
        questions=st.lists(
            st.text(min_size=5, max_size=100),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=20)
    def test_clarification_formatting_includes_all_questions(self, questions):
        """
        Test that clarification formatting includes all questions.
        """
        manager, _ = create_mock_conversation_manager()
        
        # Format questions
        result = manager._format_clarification_questions(questions)
        
        # All questions should be in the result (after stripping whitespace)
        for question in questions:
            # Strip whitespace for comparison since formatting may strip it
            question_stripped = question.strip()
            assert question_stripped in result, (
                f"Question '{question_stripped}' not found in formatted result: {result}"
            )
    
    @given(
        questions=st.lists(
            st.text(min_size=5, max_size=100),
            min_size=2,
            max_size=5
        )
    )
    @settings(max_examples=20)
    def test_clarification_formatting_numbers_multiple_questions(self, questions):
        """
        Test that multiple questions are numbered.
        """
        manager, _ = create_mock_conversation_manager()
        
        # Format questions
        result = manager._format_clarification_questions(questions)
        
        # Should contain numbering for multiple questions
        if len(questions) > 1:
            assert "1." in result, "Multiple questions should be numbered"
            assert "2." in result, "Multiple questions should be numbered"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
