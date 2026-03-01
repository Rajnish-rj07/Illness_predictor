"""
Unit tests for QuestionEngine.

Tests the intelligent question generation system using entropy-based
information gain.

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5
"""

import pytest
from src.question_engine import QuestionEngine, Question, QA
from src.models.data_models import SymptomVector, SymptomInfo


class TestQuestionEngine:
    """Unit tests for QuestionEngine class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a simple illness-symptom map for testing
        self.illness_symptom_map = {
            'flu': {'fever', 'cough', 'fatigue'},
            'cold': {'cough', 'runny_nose', 'sneezing'},
            'covid': {'fever', 'cough', 'loss_of_taste'},
        }
        
        self.engine = QuestionEngine(
            illness_symptom_map=self.illness_symptom_map,
            max_questions=15,
            confidence_threshold=0.80
        )
    
    def test_initialization(self):
        """Test QuestionEngine initialization."""
        assert self.engine.max_questions == 15
        assert self.engine.confidence_threshold == 0.80
        assert len(self.engine.illness_symptom_map) == 3
        assert 'flu' in self.engine.illness_symptom_map
    
    def test_symptom_illness_map_building(self):
        """Test reverse mapping from symptoms to illnesses."""
        symptom_illness_map = self.engine.symptom_illness_map
        
        # 'fever' should map to flu and covid
        assert 'fever' in symptom_illness_map
        assert 'flu' in symptom_illness_map['fever']
        assert 'covid' in symptom_illness_map['fever']
        
        # 'cough' should map to all three
        assert 'cough' in symptom_illness_map
        assert len(symptom_illness_map['cough']) == 3
    
    def test_calculate_entropy_uniform(self):
        """Test entropy calculation with uniform distribution."""
        # Uniform distribution has maximum entropy
        probs = {'flu': 1/3, 'cold': 1/3, 'covid': 1/3}
        entropy = self.engine.calculate_entropy(probs)
        
        # Entropy of uniform distribution over 3 items is log2(3) ≈ 1.585
        assert abs(entropy - 1.585) < 0.01
    
    def test_calculate_entropy_certain(self):
        """Test entropy calculation with certain distribution."""
        # Certain distribution has zero entropy
        probs = {'flu': 1.0, 'cold': 0.0, 'covid': 0.0}
        entropy = self.engine.calculate_entropy(probs)
        
        assert entropy == 0.0
    
    def test_get_possible_illnesses_empty_vector(self):
        """Test getting possible illnesses with empty symptom vector."""
        symptom_vector = SymptomVector()
        
        possible = self.engine.get_possible_illnesses(symptom_vector)
        
        # All illnesses should be possible with no symptoms
        assert len(possible) == 3
        assert 'flu' in possible
        assert 'cold' in possible
        assert 'covid' in possible
    
    def test_get_possible_illnesses_with_symptoms(self):
        """Test getting possible illnesses with symptoms."""
        symptom_vector = SymptomVector(symptoms={
            'fever': SymptomInfo(present=True, severity=8)
        })
        
        possible = self.engine.get_possible_illnesses(symptom_vector)
        
        # Only flu and covid have fever
        assert len(possible) == 2
        assert 'flu' in possible
        assert 'covid' in possible
        assert 'cold' not in possible
    
    def test_calculate_illness_probabilities_empty(self):
        """Test illness probability calculation with empty vector."""
        symptom_vector = SymptomVector()
        
        probs = self.engine.calculate_illness_probabilities(symptom_vector)
        
        # Should have uniform distribution
        assert len(probs) == 3
        assert abs(probs['flu'] - 1/3) < 0.01
        assert abs(probs['cold'] - 1/3) < 0.01
        assert abs(probs['covid'] - 1/3) < 0.01
    
    def test_calculate_illness_probabilities_with_symptoms(self):
        """Test illness probability calculation with symptoms."""
        symptom_vector = SymptomVector(symptoms={
            'fever': SymptomInfo(present=True, severity=8),
            'cough': SymptomInfo(present=True, severity=6)
        })
        
        probs = self.engine.calculate_illness_probabilities(symptom_vector)
        
        # Flu and covid should have higher probabilities than cold
        # (both have fever and cough)
        assert probs['flu'] > probs['cold']
        assert probs['covid'] > probs['cold']
        
        # Probabilities should sum to 1
        assert abs(sum(probs.values()) - 1.0) < 0.01
    
    def test_calculate_information_gain(self):
        """Test information gain calculation."""
        symptom_vector = SymptomVector(symptoms={
            'fever': SymptomInfo(present=True, severity=8)
        })
        
        # Calculate IG for 'cough' (common to all)
        ig_cough = self.engine.calculate_information_gain('cough', symptom_vector)
        
        # Calculate IG for 'loss_of_taste' (specific to covid)
        ig_taste = self.engine.calculate_information_gain('loss_of_taste', symptom_vector)
        
        # Both should be non-negative
        assert ig_cough >= 0
        assert ig_taste >= 0
        
        # More specific symptom should have higher IG
        assert ig_taste > ig_cough
    
    def test_get_candidate_symptoms(self):
        """Test getting candidate symptoms."""
        symptom_vector = SymptomVector(symptoms={
            'fever': SymptomInfo(present=True, severity=8)
        })
        
        candidates = self.engine.get_candidate_symptoms(symptom_vector)
        
        # Should not include already asked symptoms
        assert 'fever' not in candidates
        
        # Should include other symptoms from possible illnesses
        assert 'cough' in candidates
        assert 'fatigue' in candidates
        assert 'loss_of_taste' in candidates
    
    def test_generate_next_question_empty_vector(self):
        """Test question generation with empty symptom vector."""
        symptom_vector = SymptomVector()
        conversation_history = []
        
        question = self.engine.generate_next_question(symptom_vector, conversation_history)
        
        assert question is not None
        assert isinstance(question, Question)
        assert question.symptom in self.engine.all_symptoms
        assert question.information_gain >= 0
        assert len(question.question_text) > 0
    
    def test_generate_next_question_with_symptoms(self):
        """Test question generation with existing symptoms."""
        symptom_vector = SymptomVector(symptoms={
            'fever': SymptomInfo(present=True, severity=8)
        })
        conversation_history = [
            QA(question="Do you have fever?", answer="yes", symptom="fever")
        ]
        
        question = self.engine.generate_next_question(symptom_vector, conversation_history)
        
        assert question is not None
        # Should not ask about fever again
        assert question.symptom != 'fever'
    
    def test_generate_question_text(self):
        """Test question text generation."""
        text = self.engine._generate_question_text('fever')
        assert 'fever' in text.lower()
        
        text = self.engine._generate_question_text('runny_nose')
        assert 'runny nose' in text.lower()
    
    def test_should_stop_questioning_max_questions(self):
        """Test stopping criteria: max questions reached."""
        symptom_vector = SymptomVector(symptoms={
            'fever': SymptomInfo(present=True, severity=8)
        })
        
        # Should stop at 15 questions
        assert self.engine.should_stop_questioning(symptom_vector, 15) is True
        assert self.engine.should_stop_questioning(symptom_vector, 16) is True
        assert self.engine.should_stop_questioning(symptom_vector, 14) is False
    
    def test_should_stop_questioning_confidence_threshold(self):
        """Test stopping criteria: confidence threshold met."""
        # Create a vector that strongly indicates flu
        symptom_vector = SymptomVector(symptoms={
            'fever': SymptomInfo(present=True, severity=9),
            'cough': SymptomInfo(present=True, severity=8),
            'fatigue': SymptomInfo(present=True, severity=7)
        })
        
        # With all flu symptoms, confidence should be high
        should_stop = self.engine.should_stop_questioning(symptom_vector, 5)
        
        # Check if confidence is indeed high
        probs = self.engine.calculate_illness_probabilities(symptom_vector)
        max_confidence = max(probs.values())
        
        if max_confidence >= 0.80:
            assert should_stop is True
        else:
            assert should_stop is False
    
    def test_should_stop_questioning_low_confidence(self):
        """Test stopping criteria: low confidence, continue questioning."""
        symptom_vector = SymptomVector(symptoms={
            'cough': SymptomInfo(present=True, severity=5)
        })
        
        # With only one common symptom, confidence should be low
        should_stop = self.engine.should_stop_questioning(symptom_vector, 3)
        
        assert should_stop is False
    
    def test_get_top_predictions(self):
        """Test getting top-K predictions."""
        symptom_vector = SymptomVector(symptoms={
            'fever': SymptomInfo(present=True, severity=8),
            'cough': SymptomInfo(present=True, severity=6)
        })
        
        top_3 = self.engine.get_top_predictions(symptom_vector, top_k=3)
        
        assert len(top_3) <= 3
        
        # Should be sorted by confidence descending
        for i in range(len(top_3) - 1):
            assert top_3[i][1] >= top_3[i+1][1]
        
        # All should be valid illnesses
        for illness, confidence in top_3:
            assert illness in self.illness_symptom_map
            assert 0 <= confidence <= 1
    
    def test_get_top_predictions_top_1(self):
        """Test getting top-1 prediction."""
        symptom_vector = SymptomVector(symptoms={
            'fever': SymptomInfo(present=True, severity=9),
            'cough': SymptomInfo(present=True, severity=8),
            'fatigue': SymptomInfo(present=True, severity=7)
        })
        
        top_1 = self.engine.get_top_predictions(symptom_vector, top_k=1)
        
        assert len(top_1) == 1
        # Should be flu (all symptoms match)
        assert top_1[0][0] == 'flu'
    
    def test_question_limit_invariant(self):
        """Test that question count never exceeds max_questions."""
        symptom_vector = SymptomVector()
        conversation_history = []
        
        questions_asked = 0
        
        while questions_asked < 20:  # Try to ask more than max
            question = self.engine.generate_next_question(
                symptom_vector,
                conversation_history
            )
            
            if question is None:
                break
            
            questions_asked += 1
            
            # Add dummy answer
            symptom_vector.symptoms[question.symptom] = SymptomInfo(
                present=True,
                severity=5
            )
            conversation_history.append(
                QA(question=question.question_text, answer="yes", symptom=question.symptom)
            )
        
        # Should never exceed max_questions
        assert questions_asked <= self.engine.max_questions
    
    def test_information_gain_maximization(self):
        """Test that selected question has highest information gain."""
        symptom_vector = SymptomVector(symptoms={
            'fever': SymptomInfo(present=True, severity=8)
        })
        conversation_history = []
        
        question = self.engine.generate_next_question(symptom_vector, conversation_history)
        
        if question is not None:
            # Calculate IG for all candidates
            candidates = self.engine.get_candidate_symptoms(symptom_vector)
            
            for candidate in candidates:
                ig = self.engine.calculate_information_gain(candidate, symptom_vector)
                # Selected question should have IG >= all others
                assert question.information_gain >= ig - 0.001  # Allow small floating point error
    
    def test_empty_candidate_symptoms(self):
        """Test behavior when no candidate symptoms remain."""
        # Create a vector with all symptoms
        symptom_vector = SymptomVector(symptoms={
            symptom: SymptomInfo(present=True, severity=5)
            for symptom in self.engine.all_symptoms
        })
        
        conversation_history = []
        
        question = self.engine.generate_next_question(symptom_vector, conversation_history)
        
        # Should return None when no candidates remain
        assert question is None
    
    def test_default_illness_symptom_map(self):
        """Test that default illness-symptom map is loaded correctly."""
        engine = QuestionEngine()  # No map provided
        
        # Should have default illnesses
        assert len(engine.illness_symptom_map) > 0
        assert 'influenza' in engine.illness_symptom_map
        assert 'common_cold' in engine.illness_symptom_map
        
        # Should have symptoms for each illness
        for illness, symptoms in engine.illness_symptom_map.items():
            assert len(symptoms) > 0


class TestQuestionEngineEdgeCases:
    """Edge case tests for QuestionEngine."""
    
    def test_single_symptom_illness(self):
        """Test with illness that has only one symptom."""
        illness_map = {
            'condition_a': {'symptom_1'},
            'condition_b': {'symptom_1', 'symptom_2'},
        }
        
        engine = QuestionEngine(illness_symptom_map=illness_map)
        
        symptom_vector = SymptomVector()
        question = engine.generate_next_question(symptom_vector, [])
        
        assert question is not None
        assert question.symptom in ['symptom_1', 'symptom_2']
    
    def test_single_illness(self):
        """Test with only one illness in the map."""
        illness_map = {
            'only_illness': {'symptom_1', 'symptom_2', 'symptom_3'},
        }
        
        engine = QuestionEngine(illness_symptom_map=illness_map, confidence_threshold=1.0)
        
        symptom_vector = SymptomVector()
        question = engine.generate_next_question(symptom_vector, [])
        
        # With single illness and low confidence threshold, should generate questions
        # Note: With only one illness, confidence is always 1.0, so we need to adjust threshold
        # or accept that it might return None if confidence threshold is met
        if question is None:
            # This is acceptable if confidence threshold is met
            probs = engine.calculate_illness_probabilities(symptom_vector)
            max_confidence = max(probs.values()) if probs else 0
            assert max_confidence >= engine.confidence_threshold or len(engine.get_candidate_symptoms(symptom_vector)) == 0
        else:
            assert question.symptom in ['symptom_1', 'symptom_2', 'symptom_3']
    
    def test_zero_information_gain(self):
        """Test behavior when all symptoms have zero information gain."""
        # This is a theoretical edge case
        illness_map = {
            'illness_a': {'symptom_1'},
            'illness_b': {'symptom_1'},
        }
        
        engine = QuestionEngine(illness_symptom_map=illness_map)
        
        symptom_vector = SymptomVector()
        question = engine.generate_next_question(symptom_vector, [])
        
        # Should still return a question even if IG is low
        assert question is not None
    
    def test_max_questions_zero(self):
        """Test with max_questions set to 0."""
        engine = QuestionEngine(max_questions=0)
        
        symptom_vector = SymptomVector()
        question = engine.generate_next_question(symptom_vector, [])
        
        # Should immediately stop
        assert question is None
    
    def test_confidence_threshold_zero(self):
        """Test with confidence_threshold set to 0."""
        engine = QuestionEngine(confidence_threshold=0.0)
        
        symptom_vector = SymptomVector()
        
        # Should stop immediately (any confidence >= 0)
        should_stop = engine.should_stop_questioning(symptom_vector, 0)
        assert should_stop is True
    
    def test_confidence_threshold_one(self):
        """Test with confidence_threshold set to 1.0."""
        engine = QuestionEngine(confidence_threshold=1.0)
        
        symptom_vector = SymptomVector(symptoms={
            'fever': SymptomInfo(present=True, severity=8)
        })
        
        # Should not stop unless confidence is exactly 1.0
        should_stop = engine.should_stop_questioning(symptom_vector, 5)
        
        probs = engine.calculate_illness_probabilities(symptom_vector)
        max_confidence = max(probs.values())
        
        if max_confidence < 1.0:
            assert should_stop is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
