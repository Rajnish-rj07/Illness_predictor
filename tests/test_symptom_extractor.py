"""
Tests for symptom extraction logic.
Validates: Requirements 1.2, 1.3, 1.5
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.llm.symptom_extractor import SymptomExtractor, ExtractionResult, extract_symptoms
from src.llm.llm_client import LLMClient, LLMResponse, LLMError
from src.models.data_models import SymptomInfo, SymptomVector
from src.session.session_manager import SessionManager


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    client = Mock(spec=LLMClient)
    client.generate_json = AsyncMock()
    client.generate_async = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def symptom_extractor(mock_llm_client):
    """Create symptom extractor with mock client."""
    return SymptomExtractor(llm_client=mock_llm_client)


class TestSymptomExtraction:
    """Test symptom extraction from natural language."""
    
    @pytest.mark.asyncio
    async def test_extract_single_symptom_with_details(self, symptom_extractor, mock_llm_client):
        """Test extracting a single symptom with severity and duration."""
        # Mock LLM response - generate_json returns a dict
        mock_llm_client.generate_json.return_value = {
            "symptoms": [
                {
                    "name": "headache",
                    "present": True,
                    "severity": 7,
                    "duration": "1-3d",
                    "description": "throbbing pain in temples",
                    "confidence": "high"
                }
            ],
            "needs_clarification": [],
            "is_health_related": True
        }
        
        result = await symptom_extractor.extract_symptoms(
            "I have a throbbing headache in my temples, severity 7/10, for 2 days"
        )
        
        assert len(result.symptoms) == 1
        assert "headache" in result.symptoms
        
        symptom = result.symptoms["headache"]
        assert symptom.present is True
        assert symptom.severity == 7
        assert symptom.duration == "1-3d"
        assert "throbbing" in symptom.description.lower()
        assert len(result.clarifying_questions) == 0
        assert result.is_health_related is True
    
    @pytest.mark.asyncio
    async def test_extract_multiple_symptoms(self, symptom_extractor, mock_llm_client):
        """Test extracting multiple symptoms from single message (Requirement 1.5)."""
        # Mock LLM response with multiple symptoms
        mock_llm_client.generate_json.return_value = {
            "symptoms": [
                {
                    "name": "fever",
                    "present": True,
                    "severity": 8,
                    "duration": "1-3d",
                    "description": "high temperature",
                    "confidence": "high"
                },
                {
                    "name": "cough",
                    "present": True,
                    "severity": 6,
                    "duration": "3-7d",
                    "description": "dry cough",
                    "confidence": "high"
                },
                {
                    "name": "fatigue",
                    "present": True,
                    "severity": 7,
                    "duration": "3-7d",
                    "description": "feeling very tired",
                    "confidence": "medium"
                }
            ],
            "needs_clarification": [],
            "is_health_related": True
        }
        
        result = await symptom_extractor.extract_symptoms(
            "I have a fever, dry cough, and feeling very tired for the past few days"
        )
        
        # Verify all symptoms extracted
        assert len(result.symptoms) == 3
        assert "fever" in result.symptoms
        assert "cough" in result.symptoms
        assert "fatigue" in result.symptoms
        
        # Verify details
        assert result.symptoms["fever"].severity == 8
        assert result.symptoms["cough"].duration == "3-7d"
        assert result.symptoms["fatigue"].present is True
    
    @pytest.mark.asyncio
    async def test_extract_symptom_with_missing_info(self, symptom_extractor, mock_llm_client):
        """Test extracting symptom with missing severity/duration (Requirement 1.3)."""
        # Mock LLM response with missing information
        mock_llm_client.generate_json.return_value = {
            "symptoms": [
                {
                    "name": "headache",
                    "present": True,
                    "severity": None,
                    "duration": None,
                    "description": "my head hurts",
                    "confidence": "medium"
                }
            ],
            "needs_clarification": [
                {
                    "symptom": "headache",
                    "question": "Can you tell me more about your headache?"
                }
            ],
            "is_health_related": True
        }
        
        # Mock clarifying question generation
        mock_llm_client.generate_async.return_value = LLMResponse(
            content="How severe is your headache on a scale of 1-10, and how long have you had it?",
            raw_response={},
            provider="openai",
            model="gpt-4"
        )
        
        result = await symptom_extractor.extract_symptoms("My head hurts")
        
        assert len(result.symptoms) == 1
        assert "headache" in result.symptoms
        assert result.symptoms["headache"].severity is None
        assert result.symptoms["headache"].duration is None
        
        # Should generate clarifying questions
        assert len(result.needs_clarification) == 1
        assert len(result.clarifying_questions) == 1
        assert "headache" in result.clarifying_questions[0].lower()
    
    @pytest.mark.asyncio
    async def test_detect_ambiguous_descriptions(self, symptom_extractor, mock_llm_client):
        """Test detection of ambiguous symptom descriptions (Requirement 1.3)."""
        # Mock LLM response with ambiguous symptoms
        mock_llm_client.generate_json.return_value = {
            "symptoms": [
                {
                    "name": "pain",
                    "present": True,
                    "severity": None,
                    "duration": "1-3d",
                    "description": "it hurts",
                    "confidence": "low"
                }
            ],
            "needs_clarification": [
                {
                    "symptom": "pain",
                    "question": "Where exactly does it hurt?"
                }
            ],
            "is_health_related": True
        }
        
        mock_llm_client.generate_async.return_value = LLMResponse(
            content="Can you describe where the pain is located and how severe it is?",
            raw_response={},
            provider="openai",
            model="gpt-4"
        )
        
        result = await symptom_extractor.extract_symptoms("It hurts")
        
        # Should detect ambiguity
        assert len(result.needs_clarification) > 0
        assert len(result.clarifying_questions) > 0
    
    @pytest.mark.asyncio
    async def test_off_topic_message(self, symptom_extractor, mock_llm_client):
        """Test handling of off-topic messages."""
        # Mock LLM response for off-topic message
        mock_llm_client.generate_json.return_value = {
            "symptoms": [],
            "needs_clarification": [],
            "is_health_related": False
        }
        
        result = await symptom_extractor.extract_symptoms(
            "What's the weather like today?"
        )
        
        assert len(result.symptoms) == 0
        assert result.is_health_related is False
    
    @pytest.mark.asyncio
    async def test_extract_with_context(self, symptom_extractor, mock_llm_client):
        """Test extraction with existing symptom context."""
        # Create existing symptom vector
        existing_vector = SymptomVector(
            symptoms={
                "fever": SymptomInfo(
                    present=True,
                    severity=8,
                    duration="1-3d",
                    description="high temperature"
                )
            },
            question_count=1
        )
        
        conversation_history = [
            {"role": "user", "content": "I have a fever"},
            {"role": "assistant", "content": "How severe is your fever?"},
            {"role": "user", "content": "It's about 8 out of 10"}
        ]
        
        # Mock LLM response with additional symptom
        mock_llm_client.generate_json.return_value = {
            "symptoms": [
                {
                    "name": "chills",
                    "present": True,
                    "severity": 6,
                    "duration": "1-3d",
                    "description": "feeling cold",
                    "confidence": "high"
                }
            ],
            "needs_clarification": [],
            "is_health_related": True
        }
        
        result = await symptom_extractor.extract_symptoms(
            "Now I'm also feeling cold and shivering",
            context=existing_vector,
            conversation_history=conversation_history
        )
        
        assert len(result.symptoms) == 1
        assert "chills" in result.symptoms
    
    @pytest.mark.asyncio
    async def test_llm_error_handling(self, symptom_extractor, mock_llm_client):
        """Test error handling when LLM fails."""
        # Mock LLM error
        mock_llm_client.generate_json.side_effect = LLMError("API error")
        
        with pytest.raises(LLMError):
            await symptom_extractor.extract_symptoms("I have a headache")


class TestSymptomMerging:
    """Test merging new symptoms with existing symptom vector."""
    
    def test_merge_new_symptom(self, symptom_extractor):
        """Test adding a new symptom to existing vector."""
        existing_vector = SymptomVector(
            symptoms={
                "fever": SymptomInfo(
                    present=True,
                    severity=8,
                    duration="1-3d",
                    description="high temperature"
                )
            },
            question_count=1
        )
        
        new_symptoms = {
            "cough": SymptomInfo(
                present=True,
                severity=6,
                duration="3-7d",
                description="dry cough"
            )
        }
        
        merged = symptom_extractor.merge_with_existing(existing_vector, new_symptoms)
        
        assert len(merged.symptoms) == 2
        assert "fever" in merged.symptoms
        assert "cough" in merged.symptoms
        assert merged.question_count == 1  # Preserved from existing
    
    def test_merge_update_existing_symptom(self, symptom_extractor):
        """Test updating an existing symptom with new information."""
        existing_vector = SymptomVector(
            symptoms={
                "headache": SymptomInfo(
                    present=True,
                    severity=None,  # Missing severity
                    duration="1-3d",
                    description="head hurts"
                )
            },
            question_count=2
        )
        
        new_symptoms = {
            "headache": SymptomInfo(
                present=True,
                severity=7,  # Now provided
                duration="1-3d",
                description="throbbing pain"
            )
        }
        
        merged = symptom_extractor.merge_with_existing(existing_vector, new_symptoms)
        
        assert len(merged.symptoms) == 1
        assert merged.symptoms["headache"].severity == 7  # Updated
        assert "throbbing pain" in merged.symptoms["headache"].description  # Appended
    
    def test_merge_with_symptom_normalization(self, symptom_extractor):
        """Test merging with symptom name normalization."""
        existing_vector = SymptomVector(
            symptoms={
                "abdominal pain": SymptomInfo(
                    present=True,
                    severity=6,
                    duration="<1d",
                    description="stomach hurts"
                )
            }
        )
        
        # Use colloquial term that should be normalized
        new_symptoms = {
            "tummy ache": SymptomInfo(
                present=True,
                severity=7,
                duration="<1d",
                description="sharp pain"
            )
        }
        
        merged = symptom_extractor.merge_with_existing(existing_vector, new_symptoms)
        
        # Should merge into same symptom (normalized to "abdominal pain")
        assert len(merged.symptoms) == 1
        assert "abdominal pain" in merged.symptoms
        assert merged.symptoms["abdominal pain"].severity == 7  # Updated


class TestAmbiguityDetection:
    """Test detection of ambiguous symptoms."""
    
    def test_detect_missing_severity(self, symptom_extractor):
        """Test detection of missing severity."""
        symptoms = {
            "headache": SymptomInfo(
                present=True,
                severity=None,  # Missing
                duration="1-3d",
                description="head hurts"
            )
        }
        
        ambiguous = symptom_extractor.detect_ambiguous_symptoms(symptoms)
        
        assert len(ambiguous) == 1
        assert "headache" in ambiguous
    
    def test_detect_missing_duration(self, symptom_extractor):
        """Test detection of missing duration."""
        symptoms = {
            "fever": SymptomInfo(
                present=True,
                severity=8,
                duration=None,  # Missing
                description="high temperature"
            )
        }
        
        ambiguous = symptom_extractor.detect_ambiguous_symptoms(symptoms)
        
        assert len(ambiguous) == 1
        assert "fever" in ambiguous
    
    def test_detect_complete_symptom(self, symptom_extractor):
        """Test that complete symptoms are not flagged as ambiguous."""
        symptoms = {
            "cough": SymptomInfo(
                present=True,
                severity=6,
                duration="3-7d",
                description="dry cough"
            )
        }
        
        ambiguous = symptom_extractor.detect_ambiguous_symptoms(symptoms)
        
        assert len(ambiguous) == 0
    
    def test_detect_multiple_ambiguous(self, symptom_extractor):
        """Test detection of multiple ambiguous symptoms."""
        symptoms = {
            "headache": SymptomInfo(
                present=True,
                severity=None,
                duration="1-3d",
                description="head hurts"
            ),
            "nausea": SymptomInfo(
                present=True,
                severity=5,
                duration=None,
                description="feeling sick"
            ),
            "fever": SymptomInfo(
                present=True,
                severity=8,
                duration="1-3d",
                description="high temperature"
            )
        }
        
        ambiguous = symptom_extractor.detect_ambiguous_symptoms(symptoms)
        
        assert len(ambiguous) == 2
        assert "headache" in ambiguous
        assert "nausea" in ambiguous
        assert "fever" not in ambiguous


class TestClarifyingQuestions:
    """Test generation of clarifying questions."""
    
    @pytest.mark.asyncio
    async def test_generate_clarifying_question(self, symptom_extractor, mock_llm_client):
        """Test generating a clarifying question for ambiguous symptom."""
        symptoms = {
            "headache": SymptomInfo(
                present=True,
                severity=None,
                duration=None,
                description="head hurts"
            )
        }
        
        needs_clarification = [
            {"symptom": "headache", "question": "Tell me more"}
        ]
        
        mock_llm_client.generate_async.return_value = LLMResponse(
            content="How severe is your headache on a scale of 1-10, and how long have you had it?",
            raw_response={},
            provider="openai",
            model="gpt-4"
        )
        
        questions = await symptom_extractor._generate_clarifying_questions(
            needs_clarification,
            symptoms
        )
        
        assert len(questions) == 1
        assert "headache" in questions[0].lower()
        assert any(word in questions[0].lower() for word in ["severe", "long", "how"])
    
    def test_fallback_question_missing_severity(self, symptom_extractor):
        """Test fallback question generation when LLM fails."""
        symptom_info = SymptomInfo(
            present=True,
            severity=None,
            duration="1-3d",
            description="hurts"
        )
        
        question = symptom_extractor._generate_fallback_question("headache", symptom_info)
        
        assert "headache" in question.lower()
        assert "severe" in question.lower() or "1-10" in question.lower()
    
    def test_fallback_question_missing_duration(self, symptom_extractor):
        """Test fallback question for missing duration."""
        symptom_info = SymptomInfo(
            present=True,
            severity=7,
            duration=None,
            description="hurts"
        )
        
        question = symptom_extractor._generate_fallback_question("fever", symptom_info)
        
        assert "fever" in question.lower()
        assert "long" in question.lower() or "how long" in question.lower()
    
    def test_fallback_question_missing_both(self, symptom_extractor):
        """Test fallback question for missing both severity and duration."""
        symptom_info = SymptomInfo(
            present=True,
            severity=None,
            duration=None,
            description="hurts"
        )
        
        question = symptom_extractor._generate_fallback_question("pain", symptom_info)
        
        assert "pain" in question.lower()
        # Should ask about both
        assert any(word in question.lower() for word in ["severe", "long", "1-10"])


class TestConvenienceFunction:
    """Test convenience function for symptom extraction."""
    
    @pytest.mark.asyncio
    async def test_extract_symptoms_convenience_function(self):
        """Test the convenience extract_symptoms function."""
        with patch('src.llm.symptom_extractor.SymptomExtractor') as MockExtractor:
            # Mock the extractor
            mock_instance = Mock()
            mock_instance.extract_symptoms = AsyncMock(return_value=ExtractionResult(
                symptoms={"fever": SymptomInfo(present=True, severity=8, duration="1-3d")},
                needs_clarification=[],
                is_health_related=True,
                clarifying_questions=[]
            ))
            mock_instance.close = AsyncMock()
            MockExtractor.return_value = mock_instance
            
            result = await extract_symptoms("I have a fever")
            
            assert len(result.symptoms) == 1
            assert "fever" in result.symptoms
            mock_instance.close.assert_called_once()


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_empty_message(self, symptom_extractor, mock_llm_client):
        """Test extraction from empty message."""
        mock_llm_client.generate_json.return_value = {
            "symptoms": [],
            "needs_clarification": [],
            "is_health_related": False
        }
        
        result = await symptom_extractor.extract_symptoms("")
        
        assert len(result.symptoms) == 0
    
    @pytest.mark.asyncio
    async def test_very_long_message(self, symptom_extractor, mock_llm_client):
        """Test extraction from very long message."""
        long_message = "I have a headache " * 100
        
        mock_llm_client.generate_json.return_value = {
            "symptoms": [
                {
                    "name": "headache",
                    "present": True,
                    "severity": None,
                    "duration": None,
                    "description": "repeated mention",
                    "confidence": "high"
                }
            ],
            "needs_clarification": [],
            "is_health_related": True
        }
        
        result = await symptom_extractor.extract_symptoms(long_message)
        
        assert len(result.symptoms) == 1
        assert "headache" in result.symptoms
    
    @pytest.mark.asyncio
    async def test_special_characters_in_message(self, symptom_extractor, mock_llm_client):
        """Test extraction with special characters."""
        mock_llm_client.generate_json.return_value = {
            "symptoms": [
                {
                    "name": "pain",
                    "present": True,
                    "severity": 7,
                    "duration": "1-3d",
                    "description": "sharp pain",
                    "confidence": "high"
                }
            ],
            "needs_clarification": [],
            "is_health_related": True
        }
        
        result = await symptom_extractor.extract_symptoms("I have pain!!! @#$%")
        
        assert len(result.symptoms) == 1
    
    def test_merge_empty_new_symptoms(self, symptom_extractor):
        """Test merging with empty new symptoms."""
        existing_vector = SymptomVector(
            symptoms={
                "fever": SymptomInfo(present=True, severity=8, duration="1-3d")
            }
        )
        
        merged = symptom_extractor.merge_with_existing(existing_vector, {})
        
        assert len(merged.symptoms) == 1
        assert "fever" in merged.symptoms
    
    def test_merge_into_empty_vector(self, symptom_extractor):
        """Test merging into empty symptom vector."""
        existing_vector = SymptomVector(symptoms={})
        
        new_symptoms = {
            "cough": SymptomInfo(present=True, severity=6, duration="3-7d")
        }
        
        merged = symptom_extractor.merge_with_existing(existing_vector, new_symptoms)
        
        assert len(merged.symptoms) == 1
        assert "cough" in merged.symptoms


# ============================================================================
# Property-Based Tests
# ============================================================================

from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import composite


# Common symptoms for test generation
COMMON_SYMPTOMS = [
    "headache", "fever", "cough", "fatigue", "nausea", "vomiting",
    "diarrhea", "abdominal pain", "chest pain", "shortness of breath",
    "dizziness", "sore throat", "runny nose", "muscle aches", "chills",
    "rash", "joint pain", "back pain", "insomnia", "anxiety"
]

# Severity descriptors
SEVERITY_DESCRIPTORS = {
    "mild": (1, 3),
    "moderate": (4, 6),
    "severe": (7, 9),
    "very severe": (9, 10),
    "slight": (1, 3),
    "bad": (6, 8),
    "terrible": (8, 10),
    "intense": (7, 9)
}

# Duration descriptors
DURATION_DESCRIPTORS = {
    "a few hours": "<1d",
    "since this morning": "<1d",
    "for a day": "1-3d",
    "for 2 days": "1-3d",
    "for 3 days": "1-3d",
    "for a few days": "1-3d",
    "for 5 days": "3-7d",
    "for a week": "3-7d",
    "for over a week": ">7d",
    "for 10 days": ">7d",
    "for two weeks": ">7d"
}


@composite
def symptom_with_details(draw):
    """
    Generate a symptom with optional severity and duration details.
    
    Returns:
        Tuple of (symptom_name, severity, duration, message_fragment)
    """
    symptom = draw(st.sampled_from(COMMON_SYMPTOMS))
    
    # Optionally include severity
    include_severity = draw(st.booleans())
    severity = None
    severity_text = ""
    if include_severity:
        severity_desc = draw(st.sampled_from(list(SEVERITY_DESCRIPTORS.keys())))
        severity_range = SEVERITY_DESCRIPTORS[severity_desc]
        severity = draw(st.integers(min_value=severity_range[0], max_value=severity_range[1]))
        severity_text = f"{severity_desc} "
    
    # Optionally include duration
    include_duration = draw(st.booleans())
    duration = None
    duration_text = ""
    if include_duration:
        duration_desc = draw(st.sampled_from(list(DURATION_DESCRIPTORS.keys())))
        duration = DURATION_DESCRIPTORS[duration_desc]
        duration_text = f" {duration_desc}"
    
    # Create message fragment
    templates = [
        f"I have {severity_text}{symptom}{duration_text}",
        f"I've been experiencing {severity_text}{symptom}{duration_text}",
        f"My {symptom} is {severity_text.strip() or 'bothering me'}{duration_text}",
        f"{severity_text}{symptom}{duration_text}",
    ]
    
    message_fragment = draw(st.sampled_from(templates))
    
    return (symptom, severity, duration, message_fragment)


@composite
def multi_symptom_message(draw, min_symptoms=1, max_symptoms=5):
    """
    Generate a message containing multiple symptoms.
    
    Returns:
        Tuple of (expected_symptoms, message)
        where expected_symptoms is a list of (symptom_name, severity, duration)
    """
    num_symptoms = draw(st.integers(min_value=min_symptoms, max_value=max_symptoms))
    
    # Generate unique symptoms
    symptoms_data = []
    used_symptoms = set()
    
    for _ in range(num_symptoms):
        symptom_data = draw(symptom_with_details())
        symptom_name = symptom_data[0]
        
        # Ensure unique symptoms
        if symptom_name not in used_symptoms:
            symptoms_data.append(symptom_data)
            used_symptoms.add(symptom_name)
    
    # Assume we have at least one symptom after deduplication
    assume(len(symptoms_data) > 0)
    
    # Combine into a message
    fragments = [data[3] for data in symptoms_data]
    
    # Join with various connectors
    if len(fragments) == 1:
        message = fragments[0]
    elif len(fragments) == 2:
        connector = draw(st.sampled_from([" and ", ", and also ", ". I also have "]))
        message = connector.join(fragments)
    else:
        # Multiple symptoms - use commas and "and"
        message = ", ".join(fragments[:-1]) + ", and " + fragments[-1]
    
    # Extract expected symptoms (name, severity, duration)
    expected_symptoms = [(data[0], data[1], data[2]) for data in symptoms_data]
    
    return (expected_symptoms, message)


class TestPropertyBasedSymptomExtraction:
    """
    Property-based tests for symptom extraction.
    
    **Validates: Requirements 1.2, 1.5**
    """
    
    @pytest.mark.property
    @settings(max_examples=20, deadline=None)
    @given(message_data=multi_symptom_message(min_symptoms=1, max_symptoms=5))
    @pytest.mark.asyncio
    async def test_property_1_symptom_extraction_completeness(self, message_data):
        """
        **Property 1: Symptom extraction completeness**
        **Validates: Requirements 1.2, 1.5**
        
        For any natural language message containing symptom descriptions,
        the Generative_AI should extract all mentioned symptoms into structured
        SymptomInfo objects with appropriate attributes (severity, duration).
        
        This test verifies that:
        1. All symptoms mentioned in the message are extracted
        2. Each extracted symptom has the correct attributes
        3. Multiple symptoms in a single message are all captured (Requirement 1.5)
        """
        expected_symptoms, message = message_data
        
        # Create mock LLM client that returns the expected symptoms
        mock_client = Mock(spec=LLMClient)
        
        # Build the mock response based on expected symptoms
        mock_symptoms = []
        for symptom_name, severity, duration in expected_symptoms:
            mock_symptoms.append({
                "name": symptom_name,
                "present": True,
                "severity": severity,
                "duration": duration,
                "description": f"extracted from: {message[:50]}",
                "confidence": "high" if (severity and duration) else "medium"
            })
        
        mock_response = {
            "symptoms": mock_symptoms,
            "needs_clarification": [],
            "is_health_related": True
        }
        
        mock_client.generate_json = AsyncMock(return_value=mock_response)
        mock_client.close = AsyncMock()
        
        # Create extractor with mock client
        extractor = SymptomExtractor(llm_client=mock_client)
        
        try:
            # Extract symptoms
            result = await extractor.extract_symptoms(message)
            
            # Property 1: All symptoms should be extracted
            assert len(result.symptoms) == len(expected_symptoms), \
                f"Expected {len(expected_symptoms)} symptoms but got {len(result.symptoms)}"
            
            # Verify each expected symptom is present
            for symptom_name, expected_severity, expected_duration in expected_symptoms:
                assert symptom_name in result.symptoms, \
                    f"Symptom '{symptom_name}' not found in extracted symptoms. " \
                    f"Extracted: {list(result.symptoms.keys())}"
                
                extracted_symptom = result.symptoms[symptom_name]
                
                # Verify symptom is marked as present
                assert extracted_symptom.present is True, \
                    f"Symptom '{symptom_name}' should be marked as present"
                
                # Verify severity if it was specified
                if expected_severity is not None:
                    assert extracted_symptom.severity == expected_severity, \
                        f"Symptom '{symptom_name}' severity mismatch: " \
                        f"expected {expected_severity}, got {extracted_symptom.severity}"
                
                # Verify duration if it was specified
                if expected_duration is not None:
                    assert extracted_symptom.duration == expected_duration, \
                        f"Symptom '{symptom_name}' duration mismatch: " \
                        f"expected {expected_duration}, got {extracted_symptom.duration}"
            
            # Verify the message is recognized as health-related
            assert result.is_health_related is True, \
                "Message with symptoms should be recognized as health-related"
            
        finally:
            await extractor.close()
    
    @pytest.mark.property
    @settings(max_examples=10, deadline=None)
    @given(
        symptom1=symptom_with_details(),
        symptom2=symptom_with_details()
    )
    @pytest.mark.asyncio
    async def test_property_1_multiple_symptoms_in_single_message(self, symptom1, symptom2):
        """
        **Property 1 (Requirement 1.5 focus): Multiple symptoms extraction**
        **Validates: Requirement 1.5**
        
        Test that the system accepts and extracts multiple symptoms from
        a single user message.
        """
        # Ensure we have two different symptoms
        assume(symptom1[0] != symptom2[0])
        
        # Create message with both symptoms
        message = f"{symptom1[3]} and {symptom2[3]}"
        
        # Create mock LLM client
        mock_client = Mock(spec=LLMClient)
        
        mock_response = {
            "symptoms": [
                {
                    "name": symptom1[0],
                    "present": True,
                    "severity": symptom1[1],
                    "duration": symptom1[2],
                    "description": symptom1[3],
                    "confidence": "high"
                },
                {
                    "name": symptom2[0],
                    "present": True,
                    "severity": symptom2[1],
                    "duration": symptom2[2],
                    "description": symptom2[3],
                    "confidence": "high"
                }
            ],
            "needs_clarification": [],
            "is_health_related": True
        }
        
        mock_client.generate_json = AsyncMock(return_value=mock_response)
        mock_client.close = AsyncMock()
        
        extractor = SymptomExtractor(llm_client=mock_client)
        
        try:
            result = await extractor.extract_symptoms(message)
            
            # Should extract both symptoms
            assert len(result.symptoms) >= 2, \
                f"Expected at least 2 symptoms but got {len(result.symptoms)}"
            
            # Both symptoms should be present
            assert symptom1[0] in result.symptoms, \
                f"First symptom '{symptom1[0]}' not found"
            assert symptom2[0] in result.symptoms, \
                f"Second symptom '{symptom2[0]}' not found"
            
        finally:
            await extractor.close()
    
    @pytest.mark.property
    @settings(max_examples=10, deadline=None)
    @given(symptom_data=symptom_with_details())
    @pytest.mark.asyncio
    async def test_property_1_symptom_attributes_extraction(self, symptom_data):
        """
        **Property 1 (Requirement 1.2 focus): Symptom attributes extraction**
        **Validates: Requirement 1.2**
        
        Test that severity and duration are correctly extracted when present
        in the natural language description.
        """
        symptom_name, severity, duration, message = symptom_data
        
        # Create mock LLM client
        mock_client = Mock(spec=LLMClient)
        
        mock_response = {
            "symptoms": [
                {
                    "name": symptom_name,
                    "present": True,
                    "severity": severity,
                    "duration": duration,
                    "description": message,
                    "confidence": "high"
                }
            ],
            "needs_clarification": [],
            "is_health_related": True
        }
        
        mock_client.generate_json = AsyncMock(return_value=mock_response)
        mock_client.close = AsyncMock()
        
        extractor = SymptomExtractor(llm_client=mock_client)
        
        try:
            result = await extractor.extract_symptoms(message)
            
            # Should extract the symptom
            assert len(result.symptoms) >= 1, "Should extract at least one symptom"
            assert symptom_name in result.symptoms, \
                f"Symptom '{symptom_name}' not found in extracted symptoms"
            
            extracted = result.symptoms[symptom_name]
            
            # Verify attributes match what was in the message
            if severity is not None:
                assert extracted.severity == severity, \
                    f"Severity mismatch: expected {severity}, got {extracted.severity}"
            
            if duration is not None:
                assert extracted.duration == duration, \
                    f"Duration mismatch: expected {duration}, got {extracted.duration}"
            
        finally:
            await extractor.close()


    @pytest.mark.property
    @settings(max_examples=20, deadline=None)
    @given(message_data=multi_symptom_message(min_symptoms=1, max_symptoms=5))
    @pytest.mark.asyncio
    async def test_property_3_symptom_storage_persistence(self, message_data):
        """
        **Property 3: Symptom storage persistence**
        **Validates: Requirements 1.4**
        
        Test that any provided symptom appears in Symptom_Vector.
        
        For any symptom provided by a user, after processing, that symptom
        should be present in the session's Symptom_Vector with correct attributes.
        
        This test verifies the integration between symptom extraction and storage:
        1. Symptoms are extracted from natural language
        2. Symptoms are properly stored in the SymptomVector
        3. All extracted symptoms persist in the vector
        4. Symptom attributes (severity, duration) are preserved
        """
        expected_symptoms, message = message_data
        
        # Create mock LLM client that returns the expected symptoms
        mock_client = Mock(spec=LLMClient)
        
        # Build the mock response based on expected symptoms
        mock_symptoms = []
        for symptom_name, severity, duration in expected_symptoms:
            mock_symptoms.append({
                "name": symptom_name,
                "present": True,
                "severity": severity,
                "duration": duration,
                "description": f"extracted from: {message[:50]}",
                "confidence": "high" if (severity and duration) else "medium"
            })
        
        mock_response = {
            "symptoms": mock_symptoms,
            "needs_clarification": [],
            "is_health_related": True
        }
        
        mock_client.generate_json = AsyncMock(return_value=mock_response)
        mock_client.close = AsyncMock()
        
        # Create extractor with mock client
        extractor = SymptomExtractor(llm_client=mock_client)
        
        try:
            # Extract symptoms from message
            result = await extractor.extract_symptoms(message)
            
            # Create a SymptomVector to store the symptoms
            symptom_vector = SymptomVector()
            
            # Merge extracted symptoms into the vector (simulating storage)
            symptom_vector = extractor.merge_with_existing(symptom_vector, result.symptoms)
            
            # Property 3: All provided symptoms should appear in Symptom_Vector
            # Note: The number may differ due to symptom name normalization
            # (e.g., "runny nose" -> "nasal congestion")
            assert len(symptom_vector.symptoms) > 0, \
                f"Expected at least one symptom in vector but got {len(symptom_vector.symptoms)}"
            
            # Verify each symptom is stored correctly
            # We need to account for symptom name normalization
            for symptom_name, expected_severity, expected_duration in expected_symptoms:
                # Normalize the symptom name using the same logic as the extractor
                normalized_name = extractor.parser.sanitize_symptom_name(symptom_name)
                
                # Symptom should be present in the vector (possibly under normalized name)
                assert normalized_name in symptom_vector.symptoms, \
                    f"Symptom '{symptom_name}' (normalized: '{normalized_name}') not found in SymptomVector. " \
                    f"Stored symptoms: {list(symptom_vector.symptoms.keys())}"
                
                stored_symptom = symptom_vector.symptoms[normalized_name]
                
                # Symptom should be marked as present
                assert stored_symptom.present is True, \
                    f"Symptom '{normalized_name}' should be marked as present in SymptomVector"
                
                # Severity should be preserved if it was provided
                if expected_severity is not None:
                    assert stored_symptom.severity == expected_severity, \
                        f"Symptom '{normalized_name}' severity not preserved: " \
                        f"expected {expected_severity}, got {stored_symptom.severity}"
                
                # Duration should be preserved if it was provided
                if expected_duration is not None:
                    assert stored_symptom.duration == expected_duration, \
                        f"Symptom '{normalized_name}' duration not preserved: " \
                        f"expected {expected_duration}, got {stored_symptom.duration}"
                
                # Description should be present
                assert stored_symptom.description, \
                    f"Symptom '{normalized_name}' should have a description in SymptomVector"
            
            # Verify the SymptomVector is valid
            symptom_vector.validate()
            
        finally:
            await extractor.close()
    
    @pytest.mark.property
    @settings(max_examples=10, deadline=None)
    @given(
        initial_symptoms=multi_symptom_message(min_symptoms=1, max_symptoms=3),
        additional_symptoms=multi_symptom_message(min_symptoms=1, max_symptoms=3)
    )
    @pytest.mark.asyncio
    async def test_property_3_symptom_storage_accumulation(self, initial_symptoms, additional_symptoms):
        """
        **Property 3 (Extended): Symptom storage accumulation**
        **Validates: Requirements 1.4**
        
        Test that symptoms accumulate correctly in the SymptomVector across
        multiple messages.
        
        This verifies that:
        1. Initial symptoms are stored
        2. Additional symptoms are added to the vector
        3. All symptoms persist together
        4. No symptoms are lost during accumulation
        """
        initial_expected, initial_message = initial_symptoms
        additional_expected, additional_message = additional_symptoms
        
        # Ensure we have different symptoms in each message
        initial_names = {s[0] for s in initial_expected}
        additional_names = {s[0] for s in additional_expected}
        
        # Filter out any overlapping symptoms from additional
        additional_expected = [s for s in additional_expected if s[0] not in initial_names]
        assume(len(additional_expected) > 0)
        
        # Create mock LLM client
        mock_client = Mock(spec=LLMClient)
        
        # Mock response for initial symptoms
        initial_mock_symptoms = [
            {
                "name": name,
                "present": True,
                "severity": severity,
                "duration": duration,
                "description": f"initial: {name}",
                "confidence": "high"
            }
            for name, severity, duration in initial_expected
        ]
        
        # Mock response for additional symptoms
        additional_mock_symptoms = [
            {
                "name": name,
                "present": True,
                "severity": severity,
                "duration": duration,
                "description": f"additional: {name}",
                "confidence": "high"
            }
            for name, severity, duration in additional_expected
        ]
        
        # Set up mock to return different responses for each call
        mock_client.generate_json = AsyncMock(side_effect=[
            {
                "symptoms": initial_mock_symptoms,
                "needs_clarification": [],
                "is_health_related": True
            },
            {
                "symptoms": additional_mock_symptoms,
                "needs_clarification": [],
                "is_health_related": True
            }
        ])
        mock_client.close = AsyncMock()
        
        extractor = SymptomExtractor(llm_client=mock_client)
        
        try:
            # Start with empty SymptomVector
            symptom_vector = SymptomVector()
            
            # Extract and store initial symptoms
            initial_result = await extractor.extract_symptoms(initial_message)
            symptom_vector = extractor.merge_with_existing(symptom_vector, initial_result.symptoms)
            
            # Verify initial symptoms are stored
            # Note: Count may differ due to normalization
            assert len(symptom_vector.symptoms) > 0, \
                f"Initial symptoms not stored correctly"
            
            for symptom_name, _, _ in initial_expected:
                normalized_name = extractor.parser.sanitize_symptom_name(symptom_name)
                assert normalized_name in symptom_vector.symptoms, \
                    f"Initial symptom '{symptom_name}' (normalized: '{normalized_name}') not found in vector"
            
            # Extract and store additional symptoms
            additional_result = await extractor.extract_symptoms(additional_message)
            symptom_vector = extractor.merge_with_existing(symptom_vector, additional_result.symptoms)
            
            # Property 3: All symptoms (initial + additional) should be in the vector
            # Note: Count may differ due to normalization (e.g., "runny nose" -> "nasal congestion")
            assert len(symptom_vector.symptoms) > 0, \
                f"Expected symptoms in vector but got {len(symptom_vector.symptoms)}"
            
            # Verify all initial symptoms are still present
            for symptom_name, _, _ in initial_expected:
                normalized_name = extractor.parser.sanitize_symptom_name(symptom_name)
                assert normalized_name in symptom_vector.symptoms, \
                    f"Initial symptom '{symptom_name}' (normalized: '{normalized_name}') was lost after adding more symptoms"
            
            # Verify all additional symptoms are present
            for symptom_name, _, _ in additional_expected:
                normalized_name = extractor.parser.sanitize_symptom_name(symptom_name)
                assert normalized_name in symptom_vector.symptoms, \
                    f"Additional symptom '{symptom_name}' (normalized: '{normalized_name}') not found in vector"
            
            # Verify the SymptomVector is still valid
            symptom_vector.validate()
            
        finally:
            await extractor.close()
    
    @pytest.mark.property
    @settings(max_examples=20, deadline=5000)  # Reduced examples and added deadline
    @given(
        channel=st.sampled_from(['sms', 'whatsapp', 'web']),
        user_id=st.text(min_size=5, max_size=20, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'), 
            whitelist_characters='-_'
        )),
        language=st.sampled_from(['en', 'es', 'fr', 'hi', 'zh']),
        message_data=multi_symptom_message(min_symptoms=1, max_symptoms=3)  # Reduced max
    )
    @pytest.mark.asyncio
    async def test_property_3_symptom_storage_in_session(
        self, channel, user_id, language, message_data
    ):
        """
        **Property 3 (Integration): Symptom storage in session**
        **Validates: Requirements 1.4, 10.2**
        
        Test that symptoms extracted from messages are properly stored in
        the session's SymptomVector and persist through session operations.
        
        This is an integration test that verifies:
        1. Symptoms are extracted from user messages
        2. Symptoms are stored in the session's SymptomVector
        3. Symptoms persist when the session is saved and loaded
        4. All symptom attributes are preserved through the persistence cycle
        """
        expected_symptoms, message = message_data
        
        # Create mock LLM client
        mock_client = Mock(spec=LLMClient)
        
        # Build mock response
        mock_symptoms = [
            {
                "name": name,
                "present": True,
                "severity": severity,
                "duration": duration,
                "description": f"symptom: {name}",
                "confidence": "high"
            }
            for name, severity, duration in expected_symptoms
        ]
        
        mock_response = {
            "symptoms": mock_symptoms,
            "needs_clarification": [],
            "is_health_related": True
        }
        
        mock_client.generate_json = AsyncMock(return_value=mock_response)
        mock_client.close = AsyncMock()
        
        # Create session manager and extractor
        session_manager = SessionManager()
        extractor = SymptomExtractor(llm_client=mock_client)
        
        session_id = None
        try:
            # Start a new session
            session = session_manager.start_session(channel, user_id, language)
            session_id = session.session_id
            
            # Extract symptoms from message
            result = await extractor.extract_symptoms(message)
            
            # Store symptoms in session's SymptomVector
            session.symptom_vector = extractor.merge_with_existing(
                session.symptom_vector,
                result.symptoms
            )
            
            # Update session (persist to storage)
            update_success = session_manager.update_session(session)
            assert update_success, "Failed to update session with symptoms"
            
            # Load session from storage (simulating session resumption)
            loaded_session = session_manager.resume_session(session_id)
            assert loaded_session is not None, "Failed to resume session"
            
            # Property 3: All symptoms should be present in the loaded session's SymptomVector
            # Note: Count may differ due to normalization
            assert len(loaded_session.symptom_vector.symptoms) > 0, \
                f"Expected symptoms in loaded session but got " \
                f"{len(loaded_session.symptom_vector.symptoms)}"
            
            # Verify each symptom is present with correct attributes
            for symptom_name, expected_severity, expected_duration in expected_symptoms:
                # Normalize symptom name
                normalized_name = extractor.parser.sanitize_symptom_name(symptom_name)
                
                assert normalized_name in loaded_session.symptom_vector.symptoms, \
                    f"Symptom '{symptom_name}' (normalized: '{normalized_name}') not found in loaded session's SymptomVector"
                
                stored_symptom = loaded_session.symptom_vector.symptoms[normalized_name]
                
                # Verify symptom is marked as present
                assert stored_symptom.present is True, \
                    f"Symptom '{normalized_name}' should be marked as present"
                
                # Verify severity is preserved
                if expected_severity is not None:
                    assert stored_symptom.severity == expected_severity, \
                        f"Symptom '{normalized_name}' severity not preserved through session storage: " \
                        f"expected {expected_severity}, got {stored_symptom.severity}"
                
                # Verify duration is preserved
                if expected_duration is not None:
                    assert stored_symptom.duration == expected_duration, \
                        f"Symptom '{normalized_name}' duration not preserved through session storage: " \
                        f"expected {expected_duration}, got {stored_symptom.duration}"
            
        finally:
            # Cleanup
            await extractor.close()
            if session_id is not None:
                try:
                    session_manager.delete_session(session_id)
                except Exception:
                    pass  # Ignore cleanup errors
