"""
Symptom extraction logic using LLM to parse natural language.
Validates: Requirements 1.2, 1.3, 1.5
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from src.llm.llm_client import LLMClient, LLMError
from src.llm.response_parser import ResponseParser, ParsedSymptomResponse
from src.llm.prompts import (
    SYMPTOM_EXTRACTION_SYSTEM_PROMPT,
    CLARIFICATION_SYSTEM_PROMPT,
    create_symptom_extraction_prompt,
    create_clarification_prompt,
    create_context_aware_prompt,
)
from src.models.data_models import SymptomInfo, SymptomVector

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of symptom extraction."""
    symptoms: Dict[str, SymptomInfo]
    needs_clarification: List[Dict[str, str]]
    is_health_related: bool
    clarifying_questions: List[str]


class SymptomExtractor:
    """
    Extracts symptoms from natural language using LLM.
    
    Validates: Requirements 1.2, 1.3, 1.5
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize symptom extractor.
        
        Args:
            llm_client: LLM client instance. If None, creates default client.
        """
        self.llm_client = llm_client or LLMClient()
        self.parser = ResponseParser()
        logger.info("SymptomExtractor initialized")
    
    async def extract_symptoms(
        self,
        message: str,
        context: Optional[SymptomVector] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> ExtractionResult:
        """
        Extract symptoms from user message.
        
        Handles:
        - Multiple symptoms in single message (Requirement 1.5)
        - Symptom name, severity, duration, description extraction (Requirement 1.2)
        - Ambiguous descriptions detection (Requirement 1.3)
        
        Args:
            message: User's natural language message
            context: Optional current symptom vector for context
            conversation_history: Optional conversation history
            
        Returns:
            ExtractionResult with extracted symptoms and clarification needs
            
        Raises:
            LLMError: If extraction fails
        """
        try:
            # Create prompt based on context
            if context and conversation_history:
                prompt = create_context_aware_prompt(
                    message,
                    context,
                    conversation_history
                )
            else:
                prompt = create_symptom_extraction_prompt(message)
            
            # Call LLM to extract symptoms
            logger.info(f"Extracting symptoms from message: {message[:100]}...")
            response = await self.llm_client.generate_json(
                prompt=prompt,
                system_prompt=SYMPTOM_EXTRACTION_SYSTEM_PROMPT,
                temperature=0.3,  # Lower temperature for more consistent extraction
            )
            
            # Parse response
            # generate_json returns a dict, but parser expects JSON string
            import json
            response_str = response if isinstance(response, str) else json.dumps(response)
            parsed = self.parser.parse_symptom_extraction(response_str)
            
            # Generate clarifying questions if needed
            clarifying_questions = []
            if parsed.needs_clarification:
                clarifying_questions = await self._generate_clarifying_questions(
                    parsed.needs_clarification,
                    parsed.symptoms
                )
            
            logger.info(
                f"Extracted {len(parsed.symptoms)} symptoms, "
                f"{len(clarifying_questions)} clarifications needed"
            )
            
            return ExtractionResult(
                symptoms=parsed.symptoms,
                needs_clarification=parsed.needs_clarification,
                is_health_related=parsed.is_health_related,
                clarifying_questions=clarifying_questions
            )
            
        except Exception as e:
            logger.error(f"Failed to extract symptoms: {e}")
            raise LLMError(f"Symptom extraction failed: {e}") from e
    
    async def _generate_clarifying_questions(
        self,
        needs_clarification: List[Dict[str, str]],
        symptoms: Dict[str, SymptomInfo]
    ) -> List[str]:
        """
        Generate natural clarifying questions for ambiguous symptoms.
        
        Validates: Requirement 1.3
        
        Args:
            needs_clarification: List of symptoms needing clarification
            symptoms: Current symptom information
            
        Returns:
            List of clarifying questions
        """
        questions = []
        
        for clarification in needs_clarification:
            symptom_name = clarification.get("symptom", "")
            
            # Get current symptom info if available
            current_info = symptoms.get(symptom_name)
            
            try:
                # Generate natural question using LLM
                prompt = create_clarification_prompt(symptom_name, current_info)
                response = await self.llm_client.generate_async(
                    prompt=prompt,
                    system_prompt=CLARIFICATION_SYSTEM_PROMPT,
                    temperature=0.7,  # Higher temperature for more natural questions
                    max_tokens=150
                )
                
                question = response.content.strip()
                questions.append(question)
                
            except Exception as e:
                logger.warning(f"Failed to generate clarifying question for {symptom_name}: {e}")
                # Fallback to template question
                questions.append(self._generate_fallback_question(symptom_name, current_info))
        
        return questions
    
    def _generate_fallback_question(
        self,
        symptom_name: str,
        symptom_info: Optional[SymptomInfo]
    ) -> str:
        """
        Generate fallback clarifying question when LLM fails.
        
        Args:
            symptom_name: Name of symptom
            symptom_info: Current symptom information
            
        Returns:
            Fallback question string
        """
        missing_parts = []
        
        if not symptom_info or symptom_info.severity is None:
            missing_parts.append("how severe it is (on a scale of 1-10)")
        
        if not symptom_info or symptom_info.duration is None:
            missing_parts.append("how long you've had it")
        
        if missing_parts:
            missing_str = " and ".join(missing_parts)
            return f"Can you tell me more about your {symptom_name}? Specifically, {missing_str}?"
        
        return f"Can you describe your {symptom_name} in more detail?"
    
    def merge_with_existing(
        self,
        existing_vector: SymptomVector,
        new_symptoms: Dict[str, SymptomInfo]
    ) -> SymptomVector:
        """
        Merge newly extracted symptoms with existing symptom vector.
        
        Args:
            existing_vector: Current symptom vector
            new_symptoms: Newly extracted symptoms
            
        Returns:
            Updated symptom vector
        """
        # Create a copy of existing symptoms
        merged_symptoms = existing_vector.symptoms.copy()
        
        # Merge new symptoms
        for symptom_name, new_info in new_symptoms.items():
            # Normalize symptom name
            normalized_name = self.parser.sanitize_symptom_name(symptom_name)
            
            if normalized_name in merged_symptoms:
                # Update existing symptom with new information
                existing_info = merged_symptoms[normalized_name]
                
                # Update severity if new value provided and more specific
                if new_info.severity is not None:
                    existing_info.severity = new_info.severity
                
                # Update duration if new value provided and more specific
                if new_info.duration is not None:
                    existing_info.duration = new_info.duration
                
                # Append to description if new information
                if new_info.description and new_info.description not in existing_info.description:
                    if existing_info.description:
                        existing_info.description += f" | {new_info.description}"
                    else:
                        existing_info.description = new_info.description
                
                # Update present flag
                existing_info.present = new_info.present
                
                logger.debug(f"Updated existing symptom: {normalized_name}")
            else:
                # Add new symptom
                merged_symptoms[normalized_name] = new_info
                logger.debug(f"Added new symptom: {normalized_name}")
        
        # Create updated symptom vector
        return SymptomVector(
            symptoms=merged_symptoms,
            question_count=existing_vector.question_count,
            confidence_threshold_met=existing_vector.confidence_threshold_met
        )
    
    def detect_ambiguous_symptoms(
        self,
        symptoms: Dict[str, SymptomInfo]
    ) -> List[str]:
        """
        Detect symptoms with ambiguous or missing information.
        
        Validates: Requirement 1.3
        
        Args:
            symptoms: Dictionary of symptoms to check
            
        Returns:
            List of symptom names that need clarification
        """
        ambiguous = []
        
        for symptom_name, info in symptoms.items():
            # Check if severity or duration is missing
            if info.severity is None or info.duration is None:
                ambiguous.append(symptom_name)
                logger.debug(
                    f"Symptom '{symptom_name}' is ambiguous: "
                    f"severity={info.severity}, duration={info.duration}"
                )
        
        return ambiguous
    
    async def close(self):
        """Close LLM client connection."""
        await self.llm_client.close()


# Convenience function for simple extraction
async def extract_symptoms(
    message: str,
    llm_client: Optional[LLMClient] = None
) -> ExtractionResult:
    """
    Convenience function to extract symptoms from a message.
    
    Args:
        message: User's natural language message
        llm_client: Optional LLM client instance
        
    Returns:
        ExtractionResult with extracted symptoms
    """
    extractor = SymptomExtractor(llm_client)
    try:
        return await extractor.extract_symptoms(message)
    finally:
        await extractor.close()
