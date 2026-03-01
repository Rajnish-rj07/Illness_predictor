"""
Unit tests for ConversationManager.

Tests conversation flow, off-topic handling, confusion detection, and integration
with SessionManager, QuestionEngine, and PredictionService.

Validates: Requirements 1.1, 4.1, 4.4, 4.5, 10.1, 10.3
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
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
from src.llm.symptom_extractor import SymptomExtractor, ExtractionResult
from src.question_engine.question_engine import QuestionEngine, Question
from src.prediction.prediction_service import PredictionService


@pytest.fixture
def mock_session_manager():
    """Create mock SessionManager."""
    manager = Mock(spec=SessionManager)
    return manager


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    client = Mock(spec=LLMClient)
    client.generate_json = AsyncMock()
    client.generate_async = AsyncMock()
    return client


@pytest.fixture
def mock_symptom_extractor():
    """Create mock SymptomExtractor."""
    extractor = Mock(spec=SymptomExtractor)
    extractor.extract_symptoms = AsyncMock()
    extractor.merge_with_existing = Mock()
    extractor.close = AsyncMock()
    return extractor


@pytest.fixture
def mock_question_engine():
    """Create mock QuestionEngine."""
    engine = Mock(spec=QuestionEngine)
    return engine


@pytest.fixture
def mock_prediction_service():
    """Create mock PredictionService."""
    service = Mock(spec=PredictionService)
    return service


@pytest.fixture
def sample_session():
    """Create a sample session for testing."""
    return Session(
        session_id="test-session-123",
        user_id="user-456",
        channel="web",
        language="en",
        created_at=datetime.utcnow(),
        last_active=datetime.utcnow(),
        status=SessionStatus.ACTIVE,
        conversation_context=ConversationContext(),
        symptom_vector=SymptomVector()
    )


@pytest.fixture
def conversation_manager(
    mock_session_manager,
    mock_llm_client,
    mock_question_engine,
    mock_prediction_service
):
    """Create ConversationManager with mocked dependencies."""
    manager = ConversationManager(
        session_manager=mock_session_manager,
        llm_client=mock_llm_client,
        question_engine=mock_question_engine,
        prediction_service=mock_prediction_service
    )
    return manager


class TestStartSession:
    """Tests for start_session method."""
    
    def test_start_session_creates_new_session(
        self,
        conversation_manager,
        mock_session_manager,
        sample_session
    ):
        """Test that start_session creates a new session."""
        # Arrange
        mock_session_manager.start_session.return_value = sample_session
        mock_session_manager.update_session.return_value = True
        
        # Act
        response = conversation_manager.start_session(
            channel="web",
            user_id="user-456",
            language="en"
        )
        
        # Assert
        assert response.session_id == "test-session-123"
        assert not response.is_complete
        assert "Hello" in response.message or "help" in response.message.lower()
        mock_session_manager.start_session.assert_called_once_with(
            channel="web",
            user_id="user-456",
            language="en"
        )
        mock_session_manager.update_session.assert_called_once()
    
    def test_start_session_includes_welcome_message(
        self,
        conversation_manager,
        mock_session_manager,
        sample_session
    ):
        """Test that start_session includes appropriate welcome message."""
        # Arrange
        mock_session_manager.start_session.return_value = sample_session
        mock_session_manager.update_session.return_value = True
        
        # Act
        response = conversation_manager.start_session(
            channel="web",
            user_id="user-456"
        )
        
        # Assert
        assert "symptom" in response.message.lower()
        assert "⚠️" in response.message or "important" in response.message.lower()
    
    def test_start_session_adds_message_to_context(
        self,
        conversation_manager,
        mock_session_manager,
        sample_session
    ):
        """Test that welcome message is added to conversation context."""
        # Arrange
        mock_session_manager.start_session.return_value = sample_session
        mock_session_manager.update_session.return_value = True
        
        # Act
        conversation_manager.start_session(
            channel="web",
            user_id="user-456"
        )
        
        # Assert
        # Check that update_session was called with session containing message
        call_args = mock_session_manager.update_session.call_args
        updated_session = call_args[0][0]
        assert len(updated_session.conversation_context.messages) > 0
        assert updated_session.conversation_context.messages[0].role == "assistant"


class TestProcessMessage:
    """Tests for process_message method."""
    
    @pytest.mark.asyncio
    async def test_process_message_expired_session(
        self,
        conversation_manager,
        mock_session_manager
    ):
        """Test handling of expired session."""
        # Arrange
        mock_session_manager.resume_session.return_value = None
        
        # Act
        response = await conversation_manager.process_message(
            session_id="expired-session",
            message="I have a fever"
        )
        
        # Assert
        assert response.is_complete
        assert "expired" in response.message.lower()
    
    @pytest.mark.asyncio
    async def test_process_message_adds_to_context(
        self,
        conversation_manager,
        mock_session_manager,
        sample_session
    ):
        """Test that user message is added to conversation context (Requirement 4.1)."""
        # Arrange
        mock_session_manager.resume_session.return_value = sample_session
        
        # Mock symptom extraction
        with patch.object(
            conversation_manager.symptom_extractor,
            'extract_symptoms',
            new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = ExtractionResult(
                symptoms={"fever": SymptomInfo(present=True, description="high fever")},
                needs_clarification=[],
                is_health_related=True,
                clarifying_questions=[]
            )
            
            # Mock merge
            conversation_manager.symptom_extractor.merge_with_existing = Mock(
                return_value=SymptomVector(
                    symptoms={"fever": SymptomInfo(present=True)}
                )
            )
            
            # Mock question engine
            conversation_manager.question_engine.should_stop_questioning = Mock(return_value=False)
            conversation_manager.question_engine.generate_next_question = Mock(
                return_value=Question(
                    symptom="cough",
                    question_text="Do you have a cough?",
                    information_gain=0.5
                )
            )
            
            # Act
            await conversation_manager.process_message(
                session_id="test-session-123",
                message="I have a fever"
            )
            
            # Assert
            # Check that user message was added
            assert len(sample_session.conversation_context.messages) >= 1
            user_messages = [
                msg for msg in sample_session.conversation_context.messages
                if msg.role == "user"
            ]
            assert len(user_messages) > 0
            assert user_messages[0].content == "I have a fever"
    
    @pytest.mark.asyncio
    async def test_process_message_off_topic_detection(
        self,
        conversation_manager,
        mock_session_manager,
        sample_session
    ):
        """Test off-topic message detection and redirection (Requirement 4.4)."""
        # Arrange
        mock_session_manager.resume_session.return_value = sample_session
        mock_session_manager.update_session.return_value = True
        
        # Act
        response = await conversation_manager.process_message(
            session_id="test-session-123",
            message="What's the weather like today?"
        )
        
        # Assert
        assert not response.is_complete
        assert "health" in response.message.lower() or "symptom" in response.message.lower()
        mock_session_manager.update_session.assert_called()
    
    @pytest.mark.asyncio
    async def test_process_message_confusion_detection(
        self,
        conversation_manager,
        mock_session_manager,
        sample_session
    ):
        """Test confusion detection and rephrasing (Requirement 4.5)."""
        # Arrange
        # Add a previous question to the context
        sample_session.conversation_context.messages.append(
            Message(role="assistant", content="Do you have a cough?")
        )
        mock_session_manager.resume_session.return_value = sample_session
        mock_session_manager.update_session.return_value = True
        
        # Act
        response = await conversation_manager.process_message(
            session_id="test-session-123",
            message="I don't understand what you mean"
        )
        
        # Assert
        assert response.needs_clarification
        assert "rephrase" in response.message.lower() or "example" in response.message.lower()
    
    @pytest.mark.asyncio
    async def test_process_message_extracts_symptoms(
        self,
        conversation_manager,
        mock_session_manager,
        sample_session
    ):
        """Test symptom extraction from user message."""
        # Arrange
        mock_session_manager.resume_session.return_value = sample_session
        
        # Mock symptom extraction
        with patch.object(
            conversation_manager.symptom_extractor,
            'extract_symptoms',
            new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = ExtractionResult(
                symptoms={
                    "fever": SymptomInfo(present=True, severity=8, duration="1-3d"),
                    "headache": SymptomInfo(present=True, severity=6)
                },
                needs_clarification=[],
                is_health_related=True,
                clarifying_questions=[]
            )
            
            # Mock merge
            conversation_manager.symptom_extractor.merge_with_existing = Mock(
                return_value=SymptomVector(
                    symptoms={
                        "fever": SymptomInfo(present=True, severity=8),
                        "headache": SymptomInfo(present=True, severity=6)
                    }
                )
            )
            
            # Mock question engine
            conversation_manager.question_engine.should_stop_questioning = Mock(return_value=False)
            conversation_manager.question_engine.generate_next_question = Mock(
                return_value=Question(
                    symptom="cough",
                    question_text="Do you have a cough?",
                    information_gain=0.5
                )
            )
            
            # Act
            await conversation_manager.process_message(
                session_id="test-session-123",
                message="I have a fever and headache for 2 days"
            )
            
            # Assert
            mock_extract.assert_called_once()
            # Check that symptoms were extracted
            assert "fever" in sample_session.symptom_vector.symptoms
            assert "headache" in sample_session.symptom_vector.symptoms
    
    @pytest.mark.asyncio
    async def test_process_message_handles_clarification(
        self,
        conversation_manager,
        mock_session_manager,
        sample_session
    ):
        """Test handling of clarification needs."""
        # Arrange
        mock_session_manager.resume_session.return_value = sample_session
        mock_session_manager.update_session.return_value = True
        
        # Mock symptom extraction with clarification needed
        with patch.object(
            conversation_manager.symptom_extractor,
            'extract_symptoms',
            new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = ExtractionResult(
                symptoms={"fever": SymptomInfo(present=True)},
                needs_clarification=[{"symptom": "fever", "missing": "severity"}],
                is_health_related=True,
                clarifying_questions=["How severe is your fever on a scale of 1-10?"]
            )
            
            # Act
            response = await conversation_manager.process_message(
                session_id="test-session-123",
                message="I have a fever"
            )
            
            # Assert
            assert response.needs_clarification
            assert "severe" in response.message.lower() or "scale" in response.message.lower()
    
    @pytest.mark.asyncio
    async def test_process_message_generates_next_question(
        self,
        conversation_manager,
        mock_session_manager,
        sample_session
    ):
        """Test generation of next question."""
        # Arrange
        mock_session_manager.resume_session.return_value = sample_session
        
        # Mock symptom extraction
        with patch.object(
            conversation_manager.symptom_extractor,
            'extract_symptoms',
            new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = ExtractionResult(
                symptoms={"fever": SymptomInfo(present=True, severity=8)},
                needs_clarification=[],
                is_health_related=True,
                clarifying_questions=[]
            )
            
            # Mock merge
            conversation_manager.symptom_extractor.merge_with_existing = Mock(
                return_value=SymptomVector(
                    symptoms={"fever": SymptomInfo(present=True, severity=8)}
                )
            )
            
            # Mock question engine
            conversation_manager.question_engine.should_stop_questioning = Mock(return_value=False)
            conversation_manager.question_engine.generate_next_question = Mock(
                return_value=Question(
                    symptom="cough",
                    question_text="Do you have a cough?",
                    information_gain=0.5
                )
            )
            
            # Act
            response = await conversation_manager.process_message(
                session_id="test-session-123",
                message="I have a high fever"
            )
            
            # Assert
            assert not response.is_complete
            assert "cough" in response.message.lower()
            conversation_manager.question_engine.generate_next_question.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_message_triggers_prediction(
        self,
        conversation_manager,
        mock_session_manager,
        mock_prediction_service,
        sample_session
    ):
        """Test triggering prediction when stopping criteria met."""
        # Arrange
        sample_session.symptom_vector = SymptomVector(
            symptoms={
                "fever": SymptomInfo(present=True, severity=8),
                "cough": SymptomInfo(present=True, severity=7),
                "fatigue": SymptomInfo(present=True, severity=6)
            },
            question_count=5
        )
        mock_session_manager.resume_session.return_value = sample_session
        
        # Mock symptom extraction
        with patch.object(
            conversation_manager.symptom_extractor,
            'extract_symptoms',
            new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = ExtractionResult(
                symptoms={"body_aches": SymptomInfo(present=True)},
                needs_clarification=[],
                is_health_related=True,
                clarifying_questions=[]
            )
            
            # Mock merge
            conversation_manager.symptom_extractor.merge_with_existing = Mock(
                return_value=sample_session.symptom_vector
            )
            
            # Mock question engine to stop questioning
            conversation_manager.question_engine.should_stop_questioning = Mock(return_value=True)
            
            # Mock prediction service
            mock_predictions = [
                Prediction(
                    illness="influenza",
                    confidence_score=0.85,
                    severity=Severity.MODERATE,
                    treatment_suggestions=TreatmentInfo()
                )
            ]
            mock_prediction_service.predict.return_value = mock_predictions
            mock_prediction_service.format_results.return_value = "You may have influenza."
            
            # Act
            response = await conversation_manager.process_message(
                session_id="test-session-123",
                message="yes"
            )
            
            # Assert
            assert response.is_complete
            assert response.predictions is not None
            assert len(response.predictions) > 0
            mock_prediction_service.predict.assert_called_once()


class TestResumeSession:
    """Tests for resume_session method."""
    
    def test_resume_session_calls_session_manager(
        self,
        conversation_manager,
        mock_session_manager,
        sample_session
    ):
        """Test that resume_session delegates to SessionManager."""
        # Arrange
        mock_session_manager.resume_session.return_value = sample_session
        
        # Act
        result = conversation_manager.resume_session("test-session-123")
        
        # Assert
        assert result == sample_session
        mock_session_manager.resume_session.assert_called_once_with("test-session-123")
    
    def test_resume_session_returns_none_for_expired(
        self,
        conversation_manager,
        mock_session_manager
    ):
        """Test that resume_session returns None for expired sessions."""
        # Arrange
        mock_session_manager.resume_session.return_value = None
        
        # Act
        result = conversation_manager.resume_session("expired-session")
        
        # Assert
        assert result is None


class TestEndSession:
    """Tests for end_session method."""
    
    def test_end_session_calls_session_manager(
        self,
        conversation_manager,
        mock_session_manager
    ):
        """Test that end_session delegates to SessionManager."""
        # Arrange
        mock_session_manager.end_session.return_value = True
        
        # Act
        result = conversation_manager.end_session("test-session-123")
        
        # Assert
        assert result is True
        mock_session_manager.end_session.assert_called_once_with("test-session-123")


class TestHelperMethods:
    """Tests for helper methods."""
    
    def test_is_off_topic_detects_weather(self, conversation_manager):
        """Test off-topic detection for weather queries."""
        assert conversation_manager._is_off_topic("What's the weather like?")
    
    def test_is_off_topic_detects_sports(self, conversation_manager):
        """Test off-topic detection for sports queries."""
        assert conversation_manager._is_off_topic("Who won the game yesterday?")
    
    def test_is_off_topic_allows_health(self, conversation_manager):
        """Test that health-related messages are not flagged as off-topic."""
        assert not conversation_manager._is_off_topic("I have a fever and cough")
    
    def test_is_confused_detects_confusion(self, conversation_manager):
        """Test confusion detection."""
        assert conversation_manager._is_confused("I don't understand")
        assert conversation_manager._is_confused("What do you mean?")
        assert conversation_manager._is_confused("Can you clarify?")
    
    def test_is_confused_allows_normal_responses(self, conversation_manager):
        """Test that normal responses are not flagged as confused."""
        assert not conversation_manager._is_confused("Yes, I have a cough")
        assert not conversation_manager._is_confused("No, I don't have that symptom")
    
    def test_handle_off_topic_returns_redirection(self, conversation_manager):
        """Test that off-topic handler returns appropriate redirection."""
        message = conversation_manager._handle_off_topic()
        assert "health" in message.lower() or "symptom" in message.lower()
    
    @pytest.mark.asyncio
    async def test_handle_confusion_rephrases_question(
        self,
        conversation_manager,
        sample_session
    ):
        """Test that confusion handler rephrases the last question."""
        # Add a question to context
        sample_session.conversation_context.messages.append(
            Message(role="assistant", content="Do you have a cough?")
        )
        
        # Act
        message = await conversation_manager._handle_confusion(sample_session)
        
        # Assert
        assert "rephrase" in message.lower() or "example" in message.lower()
    
    def test_format_clarification_single_question(self, conversation_manager):
        """Test formatting of single clarification question."""
        questions = ["How severe is your fever?"]
        result = conversation_manager._format_clarification_questions(questions)
        assert result == "How severe is your fever?"
    
    def test_format_clarification_multiple_questions(self, conversation_manager):
        """Test formatting of multiple clarification questions."""
        questions = [
            "How severe is your fever?",
            "How long have you had it?"
        ]
        result = conversation_manager._format_clarification_questions(questions)
        assert "1." in result
        assert "2." in result
        assert "fever" in result.lower()


class TestConversationFlow:
    """Integration tests for complete conversation flows."""
    
    @pytest.mark.asyncio
    async def test_complete_conversation_flow(
        self,
        conversation_manager,
        mock_session_manager,
        mock_prediction_service,
        sample_session
    ):
        """Test a complete conversation from start to prediction."""
        # Start session
        mock_session_manager.start_session.return_value = sample_session
        mock_session_manager.update_session.return_value = True
        
        start_response = conversation_manager.start_session(
            channel="web",
            user_id="user-456"
        )
        
        assert start_response.session_id == "test-session-123"
        assert not start_response.is_complete
        
        # Process first message
        mock_session_manager.resume_session.return_value = sample_session
        
        with patch.object(
            conversation_manager.symptom_extractor,
            'extract_symptoms',
            new_callable=AsyncMock
        ) as mock_extract:
            # First message: initial symptoms
            mock_extract.return_value = ExtractionResult(
                symptoms={"fever": SymptomInfo(present=True, severity=8)},
                needs_clarification=[],
                is_health_related=True,
                clarifying_questions=[]
            )
            
            conversation_manager.symptom_extractor.merge_with_existing = Mock(
                return_value=SymptomVector(
                    symptoms={"fever": SymptomInfo(present=True, severity=8)}
                )
            )
            
            conversation_manager.question_engine.should_stop_questioning = Mock(return_value=False)
            conversation_manager.question_engine.generate_next_question = Mock(
                return_value=Question(
                    symptom="cough",
                    question_text="Do you have a cough?",
                    information_gain=0.5
                )
            )
            
            response1 = await conversation_manager.process_message(
                session_id="test-session-123",
                message="I have a high fever"
            )
            
            assert not response1.is_complete
            assert "cough" in response1.message.lower()
            
            # Second message: answer question
            sample_session.symptom_vector = SymptomVector(
                symptoms={
                    "fever": SymptomInfo(present=True, severity=8),
                    "cough": SymptomInfo(present=True, severity=7)
                },
                question_count=1
            )
            
            mock_extract.return_value = ExtractionResult(
                symptoms={"cough": SymptomInfo(present=True, severity=7)},
                needs_clarification=[],
                is_health_related=True,
                clarifying_questions=[]
            )
            
            conversation_manager.symptom_extractor.merge_with_existing = Mock(
                return_value=sample_session.symptom_vector
            )
            
            # Trigger prediction
            conversation_manager.question_engine.should_stop_questioning = Mock(return_value=True)
            
            mock_predictions = [
                Prediction(
                    illness="influenza",
                    confidence_score=0.85,
                    severity=Severity.MODERATE,
                    treatment_suggestions=TreatmentInfo()
                )
            ]
            mock_prediction_service.predict.return_value = mock_predictions
            mock_prediction_service.format_results.return_value = "You may have influenza."
            
            response2 = await conversation_manager.process_message(
                session_id="test-session-123",
                message="Yes, I have a cough"
            )
            
            assert response2.is_complete
            assert response2.predictions is not None
            assert len(response2.predictions) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
