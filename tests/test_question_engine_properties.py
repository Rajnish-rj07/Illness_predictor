"""
Property-based tests for QuestionEngine.

Uses hypothesis library to test universal properties across many inputs.

Validates: Requirements 2.1, 2.3, 2.4, 2.5
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.strategies import composite
from src.question_engine import QuestionEngine, Question, QA
from src.models.data_models import SymptomVector, SymptomInfo


# Custom strategies for generating test data

@composite
def symptom_names(draw):
    """Generate valid symptom names."""
    symptoms = [
        'fever', 'cough', 'fatigue', 'headache', 'nausea',
        'vomiting', 'diarrhea', 'sore_throat', 'runny_nose',
        'body_aches', 'chills', 'shortness_of_breath'
    ]
    return draw(st.sampled_from(symptoms))


@composite
def symptom_info_strategy(draw):
    """Generate SymptomInfo objects."""
    return SymptomInfo(
        present=draw(st.booleans()),
        severity=draw(st.one_of(st.none(), st.integers(min_value=1, max_value=10))),
        duration=draw(st.one_of(st.none(), st.sampled_from(['<1d', '1-3d', '3-7d', '>7d']))),
        description=draw(st.text(min_size=0, max_size=50))
    )


@composite
def symptom_vectors(draw, min_symptoms=0, max_symptoms=10):
    """Generate SymptomVector objects."""
    num_symptoms = draw(st.integers(min_value=min_symptoms, max_value=max_symptoms))
    
    symptoms = {}
    for _ in range(num_symptoms):
        symptom_name = draw(symptom_names())
        if symptom_name not in symptoms:  # Avoid duplicates
            symptoms[symptom_name] = draw(symptom_info_strategy())
    
    question_count = draw(st.integers(min_value=0, max_value=15))
    
    return SymptomVector(
        symptoms=symptoms,
        question_count=question_count,
        confidence_threshold_met=False
    )


@composite
def illness_symptom_maps(draw):
    """Generate illness-symptom mappings."""
    num_illnesses = draw(st.integers(min_value=1, max_value=5))
    
    illness_map = {}
    all_symptoms = ['fever', 'cough', 'fatigue', 'headache', 'nausea', 
                   'vomiting', 'diarrhea', 'sore_throat', 'runny_nose']
    
    for i in range(num_illnesses):
        illness_name = f'illness_{i}'
        num_symptoms = draw(st.integers(min_value=1, max_value=6))
        symptoms = set(draw(st.lists(
            st.sampled_from(all_symptoms),
            min_size=num_symptoms,
            max_size=num_symptoms,
            unique=True
        )))
        illness_map[illness_name] = symptoms
    
    return illness_map


@composite
def question_engines(draw):
    """Generate QuestionEngine instances."""
    illness_map = draw(illness_symptom_maps())
    max_questions = draw(st.integers(min_value=1, max_value=20))
    confidence_threshold = draw(st.floats(min_value=0.0, max_value=1.0))
    
    return QuestionEngine(
        illness_symptom_map=illness_map,
        max_questions=max_questions,
        confidence_threshold=confidence_threshold
    )


class TestQuestionEngineProperties:
    """Property-based tests for QuestionEngine."""
    
    @given(engine=question_engines(), symptom_vector=symptom_vectors())
    @settings(max_examples=100)
    def test_property_4_information_gain_maximization(self, engine, symptom_vector):
        """
        Feature: illness-prediction-system, Property 4: Information gain maximization
        
        For any symptom vector state, the question selected by the Question_Engine
        should have information gain greater than or equal to all other candidate questions.
        
        Validates: Requirements 2.1, 2.3
        """
        # Generate a question
        question = engine.generate_next_question(symptom_vector, [])
        
        if question is None:
            # No question generated - stopping criteria met or no candidates
            return
        
        # Get all candidate symptoms
        candidates = engine.get_candidate_symptoms(symptom_vector)
        
        # Calculate IG for all candidates
        for candidate in candidates:
            ig = engine.calculate_information_gain(candidate, symptom_vector)
            
            # Selected question should have IG >= all others (with small tolerance for floating point)
            assert question.information_gain >= ig - 0.001, \
                f"Selected question {question.symptom} has IG {question.information_gain}, " \
                f"but {candidate} has IG {ig}"
    
    @given(engine=question_engines(), symptom_vector=symptom_vectors())
    @settings(max_examples=100)
    def test_property_5_question_limit_invariant(self, engine, symptom_vector):
        """
        Feature: illness-prediction-system, Property 5: Question limit invariant
        
        For any session, the total number of questions asked should never exceed 15.
        
        Validates: Requirements 2.5
        """
        conversation_history = []
        questions_asked = 0
        current_vector = SymptomVector(
            symptoms=dict(symptom_vector.symptoms),
            question_count=0
        )
        
        # Try to ask many questions
        for _ in range(engine.max_questions + 10):  # Try to exceed limit
            question = engine.generate_next_question(current_vector, conversation_history)
            
            if question is None:
                break
            
            questions_asked += 1
            
            # Add answer to vector
            current_vector.symptoms[question.symptom] = SymptomInfo(
                present=True,
                severity=5
            )
            conversation_history.append(
                QA(question=question.question_text, answer="yes", symptom=question.symptom)
            )
        
        # Should never exceed max_questions
        assert questions_asked <= engine.max_questions, \
            f"Asked {questions_asked} questions, but max is {engine.max_questions}"
    
    @given(engine=question_engines(), symptom_vector=symptom_vectors())
    @settings(max_examples=100)
    def test_property_7_stopping_criteria_correctness(self, engine, symptom_vector):
        """
        Feature: illness-prediction-system, Property 7: Stopping criteria correctness
        
        For any symptom vector where the top prediction confidence exceeds 80% OR
        15 questions have been asked, the Question_Engine should stop questioning
        and trigger prediction.
        
        Validates: Requirements 2.4
        """
        # Test max questions criterion
        if symptom_vector.question_count >= engine.max_questions:
            should_stop = engine.should_stop_questioning(
                symptom_vector,
                symptom_vector.question_count
            )
            assert should_stop is True, \
                f"Should stop when question_count ({symptom_vector.question_count}) >= max_questions ({engine.max_questions})"
        
        # Test confidence threshold criterion
        illness_probs = engine.calculate_illness_probabilities(symptom_vector)
        if illness_probs:
            max_confidence = max(illness_probs.values())
            
            if max_confidence >= engine.confidence_threshold:
                should_stop = engine.should_stop_questioning(
                    symptom_vector,
                    symptom_vector.question_count
                )
                assert should_stop is True, \
                    f"Should stop when confidence ({max_confidence}) >= threshold ({engine.confidence_threshold})"
    
    @given(engine=question_engines(), symptom_vector=symptom_vectors())
    @settings(max_examples=100)
    def test_entropy_non_negative(self, engine, symptom_vector):
        """
        Property: Entropy is always non-negative.
        
        Entropy is a measure of uncertainty and should never be negative.
        """
        illness_probs = engine.calculate_illness_probabilities(symptom_vector)
        
        if illness_probs:
            entropy = engine.calculate_entropy(illness_probs)
            assert entropy >= 0, f"Entropy should be non-negative, got {entropy}"
    
    @given(engine=question_engines(), symptom_vector=symptom_vectors())
    @settings(max_examples=100)
    def test_information_gain_non_negative(self, engine, symptom_vector):
        """
        Property: Information gain is always non-negative.
        
        Information gain represents reduction in entropy and should never be negative.
        """
        candidates = engine.get_candidate_symptoms(symptom_vector)
        
        for symptom in list(candidates)[:5]:  # Test a few candidates
            ig = engine.calculate_information_gain(symptom, symptom_vector)
            assert ig >= 0, f"Information gain for {symptom} should be non-negative, got {ig}"
    
    @given(engine=question_engines(), symptom_vector=symptom_vectors())
    @settings(max_examples=100)
    def test_probabilities_sum_to_one(self, engine, symptom_vector):
        """
        Property: Illness probabilities sum to 1.0.
        
        Probability distributions should be normalized.
        """
        illness_probs = engine.calculate_illness_probabilities(symptom_vector)
        
        if illness_probs:
            total_prob = sum(illness_probs.values())
            assert abs(total_prob - 1.0) < 0.01, \
                f"Probabilities should sum to 1.0, got {total_prob}"
    
    @given(engine=question_engines(), symptom_vector=symptom_vectors())
    @settings(max_examples=100)
    def test_probabilities_in_valid_range(self, engine, symptom_vector):
        """
        Property: All probabilities are in [0, 1].
        
        Individual probabilities should be valid.
        """
        illness_probs = engine.calculate_illness_probabilities(symptom_vector)
        
        for illness, prob in illness_probs.items():
            assert 0 <= prob <= 1, \
                f"Probability for {illness} should be in [0, 1], got {prob}"
    
    @given(engine=question_engines(), symptom_vector=symptom_vectors())
    @settings(max_examples=100)
    def test_candidate_symptoms_not_asked(self, engine, symptom_vector):
        """
        Property: Candidate symptoms should not include already asked symptoms.
        
        The engine should not ask the same question twice.
        """
        candidates = engine.get_candidate_symptoms(symptom_vector)
        asked_symptoms = set(symptom_vector.symptoms.keys())
        
        # No overlap between candidates and asked symptoms
        overlap = candidates & asked_symptoms
        assert len(overlap) == 0, \
            f"Candidate symptoms should not include asked symptoms, but found: {overlap}"
    
    @given(engine=question_engines(), symptom_vector=symptom_vectors())
    @settings(max_examples=100)
    def test_top_predictions_sorted(self, engine, symptom_vector):
        """
        Property: Top predictions are sorted by confidence descending.
        
        Predictions should be ranked correctly.
        """
        top_predictions = engine.get_top_predictions(symptom_vector, top_k=3)
        
        # Check descending order
        for i in range(len(top_predictions) - 1):
            assert top_predictions[i][1] >= top_predictions[i+1][1], \
                f"Predictions not sorted: {top_predictions[i][1]} < {top_predictions[i+1][1]}"
    
    @given(engine=question_engines(), symptom_vector=symptom_vectors(), k=st.integers(min_value=1, max_value=5))
    @settings(max_examples=100)
    def test_top_k_limit(self, engine, symptom_vector, k):
        """
        Property: Top-K predictions returns at most K predictions.
        
        The number of predictions should not exceed K.
        """
        top_predictions = engine.get_top_predictions(symptom_vector, top_k=k)
        
        assert len(top_predictions) <= k, \
            f"Should return at most {k} predictions, got {len(top_predictions)}"
    
    @given(engine=question_engines())
    @settings(max_examples=50)
    def test_empty_vector_generates_question(self, engine):
        """
        Property: Empty symptom vector should generate a question.
        
        The engine should always be able to start questioning.
        """
        symptom_vector = SymptomVector()
        question = engine.generate_next_question(symptom_vector, [])
        
        # Should generate a question unless:
        # 1. max_questions is 0, or
        # 2. confidence threshold is met (e.g., single illness with threshold <= 1.0), or
        # 3. no candidate symptoms available
        if engine.max_questions > 0:
            # Check if stopping criteria is met
            should_stop = engine.should_stop_questioning(symptom_vector, 0)
            candidates = engine.get_candidate_symptoms(symptom_vector)
            
            if not should_stop and len(candidates) > 0:
                assert question is not None, \
                    f"Should generate question for empty vector when max_questions={engine.max_questions}, " \
                    f"threshold={engine.confidence_threshold}, candidates={len(candidates)}"
    
    @given(
        engine=question_engines(),
        symptom_vector=symptom_vectors(),
        question_count=st.integers(min_value=0, max_value=20)
    )
    @settings(max_examples=100)
    def test_stopping_criteria_consistency(self, engine, symptom_vector, question_count):
        """
        Property: Stopping criteria is consistent.
        
        If should_stop_questioning returns True, generate_next_question should return None.
        """
        should_stop = engine.should_stop_questioning(symptom_vector, question_count)
        
        if should_stop:
            # Create conversation history with appropriate length
            conversation_history = [
                QA(question=f"Q{i}", answer="yes", symptom=f"s{i}")
                for i in range(question_count)
            ]
            
            question = engine.generate_next_question(symptom_vector, conversation_history)
            
            # If stopping criteria met, should not generate question
            # (unless there are no candidate symptoms)
            candidates = engine.get_candidate_symptoms(symptom_vector)
            if len(candidates) > 0:
                assert question is None, \
                    "Should not generate question when stopping criteria met"
    
    @given(engine=question_engines(), symptom_vector=symptom_vectors())
    @settings(max_examples=100)
    def test_possible_illnesses_subset(self, engine, symptom_vector):
        """
        Property: Possible illnesses are a subset of all illnesses.
        
        The engine should only consider illnesses in its knowledge base.
        """
        possible = engine.get_possible_illnesses(symptom_vector)
        all_illnesses = set(engine.illness_symptom_map.keys())
        
        assert possible.issubset(all_illnesses), \
            f"Possible illnesses should be subset of all illnesses"
    
    @given(engine=question_engines(), symptom_vector=symptom_vectors())
    @settings(max_examples=100)
    def test_question_text_not_empty(self, engine, symptom_vector):
        """
        Property: Generated questions have non-empty text.
        
        Questions should be human-readable.
        """
        question = engine.generate_next_question(symptom_vector, [])
        
        if question is not None:
            assert len(question.question_text) > 0, \
                "Question text should not be empty"
            assert question.symptom in question.question_text or \
                   question.symptom.replace('_', ' ') in question.question_text, \
                f"Question text should mention symptom {question.symptom}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
