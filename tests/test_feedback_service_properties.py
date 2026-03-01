"""
Property-based tests for FeedbackService.

Tests universal correctness properties across all valid inputs using hypothesis.
"""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import datetime, timedelta
from src.feedback.feedback_service import FeedbackService, FeedbackPrompt, AccuracyMetrics
from src.models.data_models import UserFeedback, SymptomVector, SymptomInfo


# Custom strategies for generating test data
@st.composite
def session_ids(draw):
    """Generate valid session IDs."""
    return f"session-{draw(st.integers(min_value=1, max_value=10000))}"


@st.composite
def prediction_ids(draw):
    """Generate valid prediction IDs."""
    return f"pred-{draw(st.integers(min_value=1, max_value=10000))}"


@st.composite
def illness_names(draw):
    """Generate illness names."""
    illnesses = [
        'influenza', 'pneumonia', 'bronchitis', 'covid-19', 'common_cold',
        'strep_throat', 'sinusitis', 'migraine', 'gastroenteritis', 'asthma'
    ]
    return draw(st.sampled_from(illnesses))


@st.composite
def language_codes(draw):
    """Generate language codes."""
    return draw(st.sampled_from(['en', 'es', 'fr', 'hi', 'zh']))


@st.composite
def symptom_vectors(draw):
    """Generate symptom vectors."""
    num_symptoms = draw(st.integers(min_value=1, max_value=10))
    symptoms = {}
    
    symptom_names = ['fever', 'cough', 'headache', 'fatigue', 'nausea', 
                     'sore_throat', 'runny_nose', 'body_aches', 'chills', 'dizziness']
    
    for _ in range(num_symptoms):
        symptom_name = draw(st.sampled_from(symptom_names))
        symptoms[symptom_name] = SymptomInfo(
            present=True,
            severity=draw(st.integers(min_value=1, max_value=10)),
            duration=draw(st.sampled_from(['<1d', '1-3d', '3-7d', '>7d'])),
            description=draw(st.text(min_size=5, max_size=50))
        )
    
    return SymptomVector(
        symptoms=symptoms,
        question_count=draw(st.integers(min_value=0, max_value=15))
    )


class TestProperty37FeedbackPromptInclusion:
    """
    Property 37: Feedback prompt inclusion
    
    For any prediction delivered to a user, the response should include 
    a prompt requesting feedback on diagnosis accuracy.
    
    Validates: Requirements 13.1
    """
    
    @given(language=language_codes())
    def test_feedback_prompt_always_generated(self, language):
        """Test that feedback prompt is always generated for any language."""
        service = FeedbackService()
        
        prompt = service.generate_feedback_prompt(language)
        
        # Prompt should always be generated
        assert prompt is not None
        assert isinstance(prompt, FeedbackPrompt)
        
        # Prompt should have message and options
        assert len(prompt.message) > 0
        assert len(prompt.options) > 0
        
        # Message should request feedback
        assert any(keyword in prompt.message.lower() 
                  for keyword in ['feedback', 'diagnosis', 'accurate', 'correct', 
                                 'predicción', 'prédiction'])
    
    @given(language=st.text(min_size=1, max_size=10))
    def test_feedback_prompt_handles_any_language_code(self, language):
        """Test that feedback prompt handles any language code gracefully."""
        service = FeedbackService()
        
        # Should not raise exception for any language code
        prompt = service.generate_feedback_prompt(language)
        
        assert prompt is not None
        assert isinstance(prompt, FeedbackPrompt)
        assert len(prompt.message) > 0
        assert len(prompt.options) > 0
    
    @given(language=language_codes())
    def test_feedback_prompt_has_multiple_options(self, language):
        """Test that feedback prompt always provides multiple response options."""
        service = FeedbackService()
        
        prompt = service.generate_feedback_prompt(language)
        
        # Should have at least 2 options (correct/incorrect)
        assert len(prompt.options) >= 2
        
        # Options should be non-empty strings
        assert all(isinstance(opt, str) and len(opt) > 0 for opt in prompt.options)


class TestProperty38FeedbackStorageCompleteness:
    """
    Property 38: Feedback storage completeness
    
    For any feedback submitted, it should be stored with the associated 
    prediction_id, Symptom_Vector, and timestamp.
    
    Validates: Requirements 13.3
    """
    
    @given(
        session_id=session_ids(),
        prediction_id=prediction_ids(),
        was_correct=st.booleans(),
        correct_illness=illness_names(),
        symptom_vector=symptom_vectors(),
        comments=st.one_of(st.none(), st.text(min_size=1, max_size=200))
    )
    def test_feedback_stored_with_all_context(
        self, session_id, prediction_id, was_correct, correct_illness, 
        symptom_vector, comments
    ):
        """Test that feedback is stored with all required context."""
        service = FeedbackService()
        
        # Collect feedback
        feedback = service.collect_feedback(
            session_id=session_id,
            prediction_id=prediction_id,
            was_correct=was_correct,
            correct_illness=correct_illness if not was_correct or was_correct else correct_illness,
            symptom_vector=symptom_vector,
            additional_comments=comments
        )
        
        # Feedback should be stored
        assert feedback is not None
        
        # All required fields should be present
        assert feedback.session_id == session_id
        assert feedback.prediction_id == prediction_id
        assert feedback.was_correct == was_correct
        assert feedback.timestamp is not None
        assert isinstance(feedback.timestamp, datetime)
        
        # Should be retrievable
        retrieved = service.get_feedback_by_prediction(prediction_id)
        assert retrieved is not None
        assert retrieved.prediction_id == prediction_id
        assert retrieved.session_id == session_id
    
    @given(
        session_id=session_ids(),
        prediction_id=prediction_ids(),
        correct_illness=illness_names(),
        symptom_vector=symptom_vectors()
    )
    def test_feedback_timestamp_is_recent(
        self, session_id, prediction_id, correct_illness, symptom_vector
    ):
        """Test that feedback timestamp is set to current time."""
        service = FeedbackService()
        
        before_time = datetime.utcnow()
        
        feedback = service.collect_feedback(
            session_id=session_id,
            prediction_id=prediction_id,
            was_correct=True,
            correct_illness=correct_illness,
            symptom_vector=symptom_vector
        )
        
        after_time = datetime.utcnow()
        
        # Timestamp should be between before and after
        assert before_time <= feedback.timestamp <= after_time
    
    @given(
        session_id=session_ids(),
        prediction_ids_list=st.lists(prediction_ids(), min_size=1, max_size=10, unique=True),
        illness=illness_names()
    )
    def test_multiple_feedback_stored_independently(
        self, session_id, prediction_ids_list, illness
    ):
        """Test that multiple feedback entries are stored independently."""
        service = FeedbackService()
        
        # Collect feedback for multiple predictions
        for pred_id in prediction_ids_list:
            service.collect_feedback(
                session_id=session_id,
                prediction_id=pred_id,
                was_correct=True,
                correct_illness=illness
            )
        
        # All feedback should be retrievable
        session_feedback = service.get_feedback_by_session(session_id)
        assert len(session_feedback) == len(prediction_ids_list)
        
        # Each prediction should have its own feedback
        for pred_id in prediction_ids_list:
            feedback = service.get_feedback_by_prediction(pred_id)
            assert feedback is not None
            assert feedback.prediction_id == pred_id


class TestProperty39IncorrectPredictionFlagging:
    """
    Property 39: Incorrect prediction flagging
    
    For any feedback indicating an incorrect prediction (was_correct = false), 
    the system should flag the case for expert review.
    
    Validates: Requirements 13.5
    """
    
    @given(
        session_id=session_ids(),
        prediction_id=prediction_ids(),
        correct_illness=illness_names()
    )
    def test_incorrect_feedback_always_flagged(
        self, session_id, prediction_id, correct_illness
    ):
        """Test that incorrect predictions are always flagged."""
        service = FeedbackService()
        
        # Collect incorrect feedback
        service.collect_feedback(
            session_id=session_id,
            prediction_id=prediction_id,
            was_correct=False,
            correct_illness=correct_illness
        )
        
        # Should be flagged for review
        flagged = service.get_flagged_cases()
        assert prediction_id in flagged
    
    @given(
        session_id=session_ids(),
        prediction_id=prediction_ids(),
        correct_illness=illness_names()
    )
    def test_correct_feedback_never_flagged(
        self, session_id, prediction_id, correct_illness
    ):
        """Test that correct predictions are never flagged."""
        service = FeedbackService()
        
        # Collect correct feedback
        service.collect_feedback(
            session_id=session_id,
            prediction_id=prediction_id,
            was_correct=True,
            correct_illness=correct_illness
        )
        
        # Should NOT be flagged for review
        flagged = service.get_flagged_cases()
        assert prediction_id not in flagged
    
    @given(
        incorrect_predictions=st.lists(
            st.tuples(session_ids(), prediction_ids(), illness_names()),
            min_size=1,
            max_size=20,
            unique_by=lambda x: x[1]  # Unique by prediction_id
        )
    )
    def test_all_incorrect_predictions_flagged(self, incorrect_predictions):
        """Test that all incorrect predictions are flagged."""
        service = FeedbackService()
        
        # Collect feedback for all incorrect predictions
        for session_id, pred_id, illness in incorrect_predictions:
            service.collect_feedback(
                session_id=session_id,
                prediction_id=pred_id,
                was_correct=False,
                correct_illness=illness
            )
        
        # All should be flagged
        flagged = service.get_flagged_cases()
        for _, pred_id, _ in incorrect_predictions:
            assert pred_id in flagged
        
        # Flagged count should match incorrect count
        assert len(flagged) == len(incorrect_predictions)
    
    @given(
        session_id=session_ids(),
        prediction_id=prediction_ids(),
        correct_illness=illness_names(),
        repeat_count=st.integers(min_value=2, max_value=5)
    )
    def test_duplicate_flagging_prevented(
        self, session_id, prediction_id, correct_illness, repeat_count
    ):
        """Test that same prediction is not flagged multiple times."""
        service = FeedbackService()
        
        # Collect feedback multiple times for same prediction
        for _ in range(repeat_count):
            service.collect_feedback(
                session_id=session_id,
                prediction_id=prediction_id,
                was_correct=False,
                correct_illness=correct_illness
            )
        
        # Should only be flagged once
        flagged = service.get_flagged_cases()
        assert flagged.count(prediction_id) == 1


class TestFeedbackAccuracyComputation:
    """Test accuracy computation properties."""
    
    @given(
        feedback_data=st.lists(
            st.tuples(
                session_ids(),
                prediction_ids(),
                st.booleans(),  # was_correct
                illness_names()
            ),
            min_size=1,
            max_size=50,
            unique_by=lambda x: x[1]  # Unique by prediction_id
        )
    )
    def test_accuracy_computation_consistency(self, feedback_data):
        """Test that accuracy computation is consistent with feedback."""
        service = FeedbackService()
        
        # Collect all feedback
        correct_count = 0
        for session_id, pred_id, was_correct, illness in feedback_data:
            service.collect_feedback(
                session_id=session_id,
                prediction_id=pred_id,
                was_correct=was_correct,
                correct_illness=illness
            )
            if was_correct:
                correct_count += 1
        
        # Compute metrics
        metrics = service.compute_accuracy_metrics()
        
        # Verify counts
        assert metrics.total_feedback_count == len(feedback_data)
        assert metrics.correct_predictions == correct_count
        assert metrics.incorrect_predictions == len(feedback_data) - correct_count
        
        # Verify accuracy calculation
        expected_accuracy = correct_count / len(feedback_data)
        assert abs(metrics.accuracy - expected_accuracy) < 0.001
    
    @given(
        feedback_data=st.lists(
            st.tuples(session_ids(), prediction_ids(), illness_names()),
            min_size=1,
            max_size=30,
            unique_by=lambda x: x[1]
        )
    )
    def test_all_correct_gives_100_percent_accuracy(self, feedback_data):
        """Test that all correct feedback results in 100% accuracy."""
        service = FeedbackService()
        
        # Collect all correct feedback
        for session_id, pred_id, illness in feedback_data:
            service.collect_feedback(
                session_id=session_id,
                prediction_id=pred_id,
                was_correct=True,
                correct_illness=illness
            )
        
        metrics = service.compute_accuracy_metrics()
        
        assert metrics.accuracy == 1.0
        assert metrics.correct_predictions == len(feedback_data)
        assert metrics.incorrect_predictions == 0
    
    @given(
        feedback_data=st.lists(
            st.tuples(session_ids(), prediction_ids(), illness_names()),
            min_size=1,
            max_size=30,
            unique_by=lambda x: x[1]
        )
    )
    def test_all_incorrect_gives_zero_percent_accuracy(self, feedback_data):
        """Test that all incorrect feedback results in 0% accuracy."""
        service = FeedbackService()
        
        # Collect all incorrect feedback
        for session_id, pred_id, illness in feedback_data:
            service.collect_feedback(
                session_id=session_id,
                prediction_id=pred_id,
                was_correct=False,
                correct_illness=illness
            )
        
        metrics = service.compute_accuracy_metrics()
        
        assert metrics.accuracy == 0.0
        assert metrics.correct_predictions == 0
        assert metrics.incorrect_predictions == len(feedback_data)
    
    @given(
        feedback_data=st.lists(
            st.tuples(session_ids(), prediction_ids(), st.booleans(), illness_names()),
            min_size=1,
            max_size=50,
            unique_by=lambda x: x[1]
        )
    )
    def test_accuracy_between_zero_and_one(self, feedback_data):
        """Test that accuracy is always between 0 and 1."""
        service = FeedbackService()
        
        for session_id, pred_id, was_correct, illness in feedback_data:
            service.collect_feedback(
                session_id=session_id,
                prediction_id=pred_id,
                was_correct=was_correct,
                correct_illness=illness
            )
        
        metrics = service.compute_accuracy_metrics()
        
        assert 0.0 <= metrics.accuracy <= 1.0


class TestFeedbackValidation:
    """Test feedback validation properties."""
    
    @given(
        prediction_id=prediction_ids(),
        correct_illness=illness_names()
    )
    def test_empty_session_id_rejected(self, prediction_id, correct_illness):
        """Test that empty session ID is always rejected."""
        service = FeedbackService()
        
        with pytest.raises(ValueError):
            service.collect_feedback(
                session_id="",
                prediction_id=prediction_id,
                was_correct=True,
                correct_illness=correct_illness
            )
    
    @given(
        session_id=session_ids(),
        correct_illness=illness_names()
    )
    def test_empty_prediction_id_rejected(self, session_id, correct_illness):
        """Test that empty prediction ID is always rejected."""
        service = FeedbackService()
        
        with pytest.raises(ValueError):
            service.collect_feedback(
                session_id=session_id,
                prediction_id="",
                was_correct=True,
                correct_illness=correct_illness
            )
    
    @given(
        session_id=session_ids(),
        prediction_id=prediction_ids()
    )
    def test_incorrect_without_correct_illness_rejected(self, session_id, prediction_id):
        """Test that incorrect feedback without correct illness is rejected."""
        service = FeedbackService()
        
        with pytest.raises(ValueError):
            service.collect_feedback(
                session_id=session_id,
                prediction_id=prediction_id,
                was_correct=False,
                correct_illness=None
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
