"""
Question Engine for intelligent symptom-based questioning.

This module implements an entropy-based information gain algorithm to select
the most informative follow-up questions for illness prediction.

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Set
import math
import numpy as np
from collections import defaultdict

from src.models.data_models import SymptomVector, SymptomInfo


@dataclass
class Question:
    """Represents a follow-up question about a symptom."""
    symptom: str
    question_text: str
    information_gain: float = 0.0


@dataclass
class QA:
    """Question-Answer pair for conversation history."""
    question: str
    answer: str
    symptom: str


class QuestionEngine:
    """
    Intelligent question generation engine using information gain.
    
    Uses entropy-based information gain to select the most informative
    questions for narrowing down illness predictions.
    
    Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5
    """
    
    def __init__(
        self,
        illness_symptom_map: Optional[Dict[str, Set[str]]] = None,
        max_questions: int = 15,
        confidence_threshold: float = 0.80
    ):
        """
        Initialize the Question Engine.
        
        Args:
            illness_symptom_map: Mapping of illness names to sets of associated symptoms.
                                If None, uses a default mapping.
            max_questions: Maximum number of questions to ask (default: 15)
            confidence_threshold: Confidence threshold to stop questioning (default: 0.80)
        """
        self.max_questions = max_questions
        self.confidence_threshold = confidence_threshold
        
        # Pre-computed question-symptom mappings for efficiency
        if illness_symptom_map is None:
            self.illness_symptom_map = self._get_default_illness_symptom_map()
        else:
            self.illness_symptom_map = illness_symptom_map
        
        # Build reverse mapping: symptom -> illnesses
        self.symptom_illness_map = self._build_symptom_illness_map()
        
        # All possible symptoms
        self.all_symptoms = set(self.symptom_illness_map.keys())
    
    def _get_default_illness_symptom_map(self) -> Dict[str, Set[str]]:
        """
        Get default illness-symptom mapping for testing/demo purposes.
        
        Returns:
            Dictionary mapping illness names to sets of symptoms.
        """
        return {
            'influenza': {
                'fever', 'cough', 'fatigue', 'body_aches', 'headache',
                'chills', 'sore_throat', 'runny_nose'
            },
            'common_cold': {
                'runny_nose', 'sneezing', 'sore_throat', 'cough',
                'mild_headache', 'mild_fatigue'
            },
            'covid19': {
                'fever', 'cough', 'fatigue', 'loss_of_taste', 'loss_of_smell',
                'shortness_of_breath', 'body_aches', 'headache', 'sore_throat'
            },
            'strep_throat': {
                'severe_sore_throat', 'fever', 'swollen_lymph_nodes',
                'difficulty_swallowing', 'red_tonsils', 'headache'
            },
            'migraine': {
                'severe_headache', 'nausea', 'vomiting', 'sensitivity_to_light',
                'sensitivity_to_sound', 'visual_disturbances'
            },
            'tension_headache': {
                'mild_headache', 'pressure_around_head', 'neck_pain',
                'mild_fatigue'
            },
            'gastroenteritis': {
                'nausea', 'vomiting', 'diarrhea', 'abdominal_pain',
                'fever', 'dehydration', 'fatigue'
            },
            'food_poisoning': {
                'nausea', 'vomiting', 'diarrhea', 'abdominal_cramps',
                'fever', 'weakness'
            },
            'allergic_rhinitis': {
                'sneezing', 'runny_nose', 'itchy_eyes', 'nasal_congestion',
                'postnasal_drip', 'cough'
            },
            'bronchitis': {
                'persistent_cough', 'mucus_production', 'fatigue',
                'shortness_of_breath', 'chest_discomfort', 'mild_fever'
            },
            'pneumonia': {
                'cough', 'fever', 'shortness_of_breath', 'chest_pain',
                'fatigue', 'confusion', 'rapid_breathing'
            },
            'sinusitis': {
                'facial_pain', 'nasal_congestion', 'thick_nasal_discharge',
                'reduced_sense_of_smell', 'headache', 'fever', 'cough'
            },
        }
    
    def _build_symptom_illness_map(self) -> Dict[str, Set[str]]:
        """
        Build reverse mapping from symptoms to illnesses.
        
        Returns:
            Dictionary mapping symptom names to sets of illnesses.
        """
        symptom_illness_map = defaultdict(set)
        
        for illness, symptoms in self.illness_symptom_map.items():
            for symptom in symptoms:
                symptom_illness_map[symptom].add(illness)
        
        return dict(symptom_illness_map)
    
    def calculate_entropy(self, illness_probabilities: Dict[str, float]) -> float:
        """
        Calculate entropy of illness probability distribution.
        
        Entropy measures uncertainty in the distribution. Higher entropy means
        more uncertainty about which illness is correct.
        
        Args:
            illness_probabilities: Dictionary mapping illness names to probabilities.
        
        Returns:
            Entropy value (non-negative float).
        """
        entropy = 0.0
        
        for prob in illness_probabilities.values():
            if prob > 0:
                entropy -= prob * math.log2(prob)
        
        return entropy
    
    def get_possible_illnesses(self, symptom_vector: SymptomVector) -> Set[str]:
        """
        Get set of possible illnesses based on current symptoms.
        
        An illness is possible if it has at least one symptom in common with
        the symptom vector, or if no symptoms have been reported yet.
        
        Args:
            symptom_vector: Current symptom vector.
        
        Returns:
            Set of possible illness names.
        """
        if not symptom_vector.symptoms:
            # No symptoms yet, all illnesses are possible
            return set(self.illness_symptom_map.keys())
        
        # Find illnesses that match at least one reported symptom
        possible_illnesses = set()
        
        for symptom_name, symptom_info in symptom_vector.symptoms.items():
            if symptom_info.present and symptom_name in self.symptom_illness_map:
                possible_illnesses.update(self.symptom_illness_map[symptom_name])
        
        # If no matches found, return all illnesses (edge case)
        if not possible_illnesses:
            return set(self.illness_symptom_map.keys())
        
        return possible_illnesses
    
    def calculate_illness_probabilities(
        self,
        symptom_vector: SymptomVector
    ) -> Dict[str, float]:
        """
        Calculate probability distribution over possible illnesses.
        
        Uses a simple scoring approach: each illness gets a score based on
        how many of its symptoms match the symptom vector.
        
        Args:
            symptom_vector: Current symptom vector.
        
        Returns:
            Dictionary mapping illness names to probabilities (sum to 1.0).
        """
        possible_illnesses = self.get_possible_illnesses(symptom_vector)
        
        if not possible_illnesses:
            return {}
        
        # Calculate scores for each illness
        illness_scores = {}
        
        for illness in possible_illnesses:
            illness_symptoms = self.illness_symptom_map[illness]
            
            # Count matching symptoms
            matching_symptoms = 0
            total_illness_symptoms = len(illness_symptoms)
            
            for symptom_name, symptom_info in symptom_vector.symptoms.items():
                if symptom_info.present and symptom_name in illness_symptoms:
                    matching_symptoms += 1
            
            # Score is the proportion of illness symptoms that match
            if total_illness_symptoms > 0:
                score = matching_symptoms / total_illness_symptoms
            else:
                score = 0.0
            
            illness_scores[illness] = score
        
        # Normalize to probabilities
        total_score = sum(illness_scores.values())
        
        if total_score == 0:
            # Uniform distribution if no matches
            prob = 1.0 / len(possible_illnesses)
            return {illness: prob for illness in possible_illnesses}
        
        illness_probabilities = {
            illness: score / total_score
            for illness, score in illness_scores.items()
        }
        
        return illness_probabilities
    
    def calculate_information_gain(
        self,
        symptom: str,
        current_vector: SymptomVector
    ) -> float:
        """
        Calculate expected information gain from asking about a symptom.
        
        Information gain is the reduction in entropy expected from learning
        whether the symptom is present or absent.
        
        Args:
            symptom: Symptom name to evaluate.
            current_vector: Current symptom vector.
        
        Returns:
            Expected information gain (non-negative float).
        """
        # Current entropy
        current_probs = self.calculate_illness_probabilities(current_vector)
        current_entropy = self.calculate_entropy(current_probs)
        
        # Calculate expected entropy after asking about this symptom
        # We need to consider two scenarios: symptom present and symptom absent
        
        # Scenario 1: Symptom is present
        vector_with_symptom = SymptomVector(
            symptoms={**current_vector.symptoms},
            question_count=current_vector.question_count
        )
        vector_with_symptom.symptoms[symptom] = SymptomInfo(
            present=True,
            description=f"Asked about {symptom}"
        )
        probs_with_symptom = self.calculate_illness_probabilities(vector_with_symptom)
        entropy_with_symptom = self.calculate_entropy(probs_with_symptom)
        
        # Scenario 2: Symptom is absent
        vector_without_symptom = SymptomVector(
            symptoms={**current_vector.symptoms},
            question_count=current_vector.question_count
        )
        vector_without_symptom.symptoms[symptom] = SymptomInfo(
            present=False,
            description=f"Asked about {symptom}"
        )
        probs_without_symptom = self.calculate_illness_probabilities(vector_without_symptom)
        entropy_without_symptom = self.calculate_entropy(probs_without_symptom)
        
        # Estimate probability of symptom being present
        # Based on how many possible illnesses have this symptom
        possible_illnesses = self.get_possible_illnesses(current_vector)
        illnesses_with_symptom = sum(
            1 for illness in possible_illnesses
            if symptom in self.illness_symptom_map.get(illness, set())
        )
        
        if len(possible_illnesses) > 0:
            p_symptom_present = illnesses_with_symptom / len(possible_illnesses)
        else:
            p_symptom_present = 0.5
        
        p_symptom_absent = 1.0 - p_symptom_present
        
        # Expected entropy after asking
        expected_entropy = (
            p_symptom_present * entropy_with_symptom +
            p_symptom_absent * entropy_without_symptom
        )
        
        # Information gain is reduction in entropy
        information_gain = current_entropy - expected_entropy
        
        return max(0.0, information_gain)  # Ensure non-negative
    
    def get_candidate_symptoms(self, symptom_vector: SymptomVector) -> Set[str]:
        """
        Get candidate symptoms that haven't been asked yet.
        
        Args:
            symptom_vector: Current symptom vector.
        
        Returns:
            Set of symptom names that are candidates for questioning.
        """
        # Get symptoms already asked about
        asked_symptoms = set(symptom_vector.symptoms.keys())
        
        # Get possible illnesses
        possible_illnesses = self.get_possible_illnesses(symptom_vector)
        
        # Get all symptoms associated with possible illnesses
        candidate_symptoms = set()
        for illness in possible_illnesses:
            candidate_symptoms.update(self.illness_symptom_map.get(illness, set()))
        
        # Remove already asked symptoms
        candidate_symptoms -= asked_symptoms
        
        return candidate_symptoms
    
    def generate_next_question(
        self,
        symptom_vector: SymptomVector,
        conversation_history: List[QA]
    ) -> Optional[Question]:
        """
        Generate the next most informative question.
        
        Selects the question with the highest information gain from candidate
        symptoms that haven't been asked yet.
        
        Args:
            symptom_vector: Current symptom vector.
            conversation_history: List of previous question-answer pairs.
        
        Returns:
            Question object with the best symptom to ask about, or None if
            no more questions should be asked.
        
        Validates: Requirements 2.1, 2.3
        """
        # Check stopping criteria first
        if self.should_stop_questioning(symptom_vector, len(conversation_history)):
            return None
        
        # Get candidate symptoms
        candidate_symptoms = self.get_candidate_symptoms(symptom_vector)
        
        if not candidate_symptoms:
            # No more symptoms to ask about
            return None
        
        # Calculate information gain for each candidate
        symptom_gains = []
        
        for symptom in candidate_symptoms:
            ig = self.calculate_information_gain(symptom, symptom_vector)
            symptom_gains.append((symptom, ig))
        
        # Sort by information gain (descending)
        symptom_gains.sort(key=lambda x: x[1], reverse=True)
        
        # Select symptom with highest information gain
        best_symptom, best_gain = symptom_gains[0]
        
        # Generate question text
        question_text = self._generate_question_text(best_symptom)
        
        return Question(
            symptom=best_symptom,
            question_text=question_text,
            information_gain=best_gain
        )
    
    def _generate_question_text(self, symptom: str) -> str:
        """
        Generate natural language question text for a symptom.
        
        Args:
            symptom: Symptom name (e.g., 'fever', 'cough').
        
        Returns:
            Question text string.
        """
        # Convert symptom name to readable format
        readable_symptom = symptom.replace('_', ' ')
        
        # Generate question
        return f"Are you experiencing {readable_symptom}?"
    
    def should_stop_questioning(
        self,
        symptom_vector: SymptomVector,
        question_count: int
    ) -> bool:
        """
        Determine if questioning should stop based on stopping criteria.
        
        Stopping criteria:
        1. Maximum questions reached (15 questions)
        2. Confidence threshold met (top prediction > 80%)
        
        Args:
            symptom_vector: Current symptom vector.
            question_count: Number of questions asked so far.
        
        Returns:
            True if questioning should stop, False otherwise.
        
        Validates: Requirements 2.4, 2.5
        """
        # Criterion 1: Max questions reached
        if question_count >= self.max_questions:
            return True
        
        # Criterion 2: Confidence threshold met
        illness_probs = self.calculate_illness_probabilities(symptom_vector)
        
        if illness_probs:
            max_confidence = max(illness_probs.values())
            if max_confidence >= self.confidence_threshold:
                return True
        
        return False
    
    def get_top_predictions(
        self,
        symptom_vector: SymptomVector,
        top_k: int = 3
    ) -> List[Tuple[str, float]]:
        """
        Get top-K illness predictions with confidence scores.
        
        Args:
            symptom_vector: Current symptom vector.
            top_k: Number of top predictions to return (default: 3).
        
        Returns:
            List of (illness, confidence) tuples, sorted by confidence descending.
        """
        illness_probs = self.calculate_illness_probabilities(symptom_vector)
        
        # Sort by probability descending
        sorted_predictions = sorted(
            illness_probs.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_predictions[:top_k]
