"""
Structured prompts for LLM-based symptom extraction and conversation management.
"""

from typing import List, Dict, Any, Optional
from src.models.data_models import SymptomInfo, SymptomVector


# System prompts for different conversation stages

SYMPTOM_EXTRACTION_SYSTEM_PROMPT = """You are a medical assistant AI helping to extract symptom information from patient descriptions.

Your task is to:
1. Identify all symptoms mentioned in the patient's message
2. Extract severity (1-10 scale) if mentioned
3. Extract duration (<1d, 1-3d, 3-7d, >7d) if mentioned
4. Identify if any information is ambiguous and needs clarification

Guidelines:
- Be thorough but conservative - only extract symptoms explicitly mentioned
- Map colloquial terms to medical symptom names (e.g., "tummy ache" -> "abdominal pain")
- If severity or duration is unclear, mark as null
- Identify when clarifying questions are needed

Respond with valid JSON in this format:
{
  "symptoms": [
    {
      "name": "symptom_name",
      "present": true,
      "severity": 7,  // 1-10 or null
      "duration": "1-3d",  // "<1d", "1-3d", "3-7d", ">7d" or null
      "description": "patient's description",
      "confidence": "high"  // "high", "medium", "low"
    }
  ],
  "needs_clarification": [
    {
      "symptom": "symptom_name",
      "question": "clarifying question to ask"
    }
  ],
  "is_health_related": true  // false if message is off-topic
}"""


CLARIFICATION_SYSTEM_PROMPT = """You are a medical assistant AI helping to ask clarifying questions about symptoms.

Your task is to generate a natural, empathetic question to clarify ambiguous symptom information.

Guidelines:
- Use simple, clear language
- Be empathetic and professional
- Ask one specific question at a time
- Provide examples when helpful
- Keep questions concise

The question should help determine:
- Severity (how bad is it on a scale of 1-10?)
- Duration (how long have you had this?)
- Specific characteristics (sharp vs dull pain, constant vs intermittent, etc.)"""


CONVERSATION_SYSTEM_PROMPT = """You are a compassionate medical assistant AI helping patients describe their symptoms.

Your role:
- Guide patients through symptom reporting
- Ask relevant follow-up questions
- Maintain a warm, professional tone
- Redirect off-topic conversations gently
- Explain medical terms when needed
- Show empathy for patient concerns

Guidelines:
- Use natural, conversational language
- Avoid medical jargon unless necessary
- Be patient with confused or anxious users
- Never provide diagnoses or medical advice
- Always recommend consulting healthcare professionals for serious concerns
- Maintain HIPAA compliance - don't ask for personal identifying information"""


CONFUSION_HANDLING_SYSTEM_PROMPT = """You are a medical assistant AI helping a confused patient.

The patient has indicated confusion or given unclear responses. Your task is to:
1. Acknowledge their confusion empathetically
2. Rephrase the question in simpler terms
3. Provide concrete examples
4. Offer alternative ways to describe their symptoms

Keep your response brief, clear, and supportive."""


OFF_TOPIC_REDIRECT_SYSTEM_PROMPT = """You are a medical assistant AI. The patient has sent an off-topic message.

Your task is to:
1. Briefly acknowledge their message
2. Gently redirect to health information gathering
3. Maintain a friendly, professional tone

Keep your response concise and focused on getting back to symptom assessment."""


# Prompt templates

def create_symptom_extraction_prompt(message: str) -> str:
    """
    Create prompt for extracting symptoms from user message.
    
    Args:
        message: User's message describing symptoms
        
    Returns:
        Formatted prompt for LLM
    """
    return f"""Extract symptom information from this patient message:

Patient message: "{message}"

Analyze the message and extract all symptoms with their attributes. Respond with valid JSON."""


def create_clarification_prompt(
    symptom: str,
    current_info: Optional[SymptomInfo] = None
) -> str:
    """
    Create prompt for generating clarifying question.
    
    Args:
        symptom: Symptom name that needs clarification
        current_info: Current information about the symptom
        
    Returns:
        Formatted prompt for LLM
    """
    context = f"The patient mentioned '{symptom}'"
    
    if current_info:
        if current_info.severity is None:
            context += " but didn't specify how severe it is"
        if current_info.duration is None:
            context += " but didn't specify how long they've had it"
    
    return f"""{context}.

Generate a natural, empathetic question to clarify this symptom. The question should help determine severity and/or duration."""


def create_confusion_handling_prompt(
    original_question: str,
    user_response: str
) -> str:
    """
    Create prompt for handling user confusion.
    
    Args:
        original_question: The question that confused the user
        user_response: User's confused response
        
    Returns:
        Formatted prompt for LLM
    """
    return f"""Original question: "{original_question}"

Patient's response: "{user_response}"

The patient seems confused. Rephrase the question in simpler terms with examples."""


def create_off_topic_redirect_prompt(message: str) -> str:
    """
    Create prompt for redirecting off-topic conversation.
    
    Args:
        message: User's off-topic message
        
    Returns:
        Formatted prompt for LLM
    """
    return f"""Patient message: "{message}"

This message is not related to health symptoms. Acknowledge it briefly and redirect to symptom assessment."""


def create_context_aware_prompt(
    message: str,
    symptom_vector: SymptomVector,
    conversation_history: List[Dict[str, str]]
) -> str:
    """
    Create context-aware prompt including conversation history.
    
    Args:
        message: Current user message
        symptom_vector: Current symptom vector
        conversation_history: Previous messages
        
    Returns:
        Formatted prompt with context
    """
    # Summarize current symptoms
    symptoms_summary = []
    for symptom_name, info in symptom_vector.symptoms.items():
        severity_str = f"severity {info.severity}/10" if info.severity else "severity unknown"
        duration_str = f"duration {info.duration}" if info.duration else "duration unknown"
        symptoms_summary.append(f"- {symptom_name}: {severity_str}, {duration_str}")
    
    symptoms_text = "\n".join(symptoms_summary) if symptoms_summary else "None reported yet"
    
    # Format conversation history (last 5 messages)
    history_text = ""
    if conversation_history:
        recent_history = conversation_history[-5:]
        history_lines = []
        for msg in recent_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            history_lines.append(f"{role.capitalize()}: {content}")
        history_text = "\n".join(history_lines)
    
    return f"""Current conversation context:

Symptoms reported so far:
{symptoms_text}

Recent conversation:
{history_text}

Current patient message: "{message}"

Extract any new symptom information from this message, considering the conversation context. Respond with valid JSON."""


def create_empathetic_response_prompt(
    user_message: str,
    response_type: str = "acknowledgment"
) -> str:
    """
    Create prompt for generating empathetic responses.
    
    Args:
        user_message: User's message
        response_type: Type of response (acknowledgment, encouragement, etc.)
        
    Returns:
        Formatted prompt for empathetic response
    """
    prompts = {
        "acknowledgment": "Generate a brief, empathetic acknowledgment of the patient's message.",
        "encouragement": "Generate an encouraging message to help the patient continue describing symptoms.",
        "reassurance": "Generate a reassuring message while maintaining professional boundaries.",
        "gratitude": "Thank the patient for providing information."
    }
    
    instruction = prompts.get(response_type, prompts["acknowledgment"])
    
    return f"""Patient message: "{user_message}"

{instruction}

Keep the response brief (1-2 sentences), warm, and professional."""


# Validation prompts

def create_validation_prompt(extracted_data: Dict[str, Any]) -> str:
    """
    Create prompt for validating extracted symptom data.
    
    Args:
        extracted_data: Extracted symptom data to validate
        
    Returns:
        Formatted validation prompt
    """
    return f"""Review this extracted symptom data for accuracy and completeness:

{extracted_data}

Validate:
1. Are symptom names medically accurate?
2. Are severity values (1-10) reasonable?
3. Are duration categories correct?
4. Is any critical information missing?

Respond with valid JSON:
{{
  "is_valid": true/false,
  "issues": ["list of any issues found"],
  "suggestions": ["suggestions for improvement"]
}}"""


# Multi-language support prompts

def create_translation_prompt(
    text: str,
    source_language: str,
    target_language: str
) -> str:
    """
    Create prompt for translating symptom descriptions.
    
    Args:
        text: Text to translate
        source_language: Source language code
        target_language: Target language code
        
    Returns:
        Formatted translation prompt
    """
    return f"""Translate this medical symptom description from {source_language} to {target_language}.

Maintain medical accuracy and preserve symptom severity/duration information.

Original text: "{text}"

Provide the translation only, without explanations."""


def create_language_detection_prompt(text: str) -> str:
    """
    Create prompt for detecting language of user message.
    
    Args:
        text: Text to analyze
        
    Returns:
        Formatted language detection prompt
    """
    return f"""Detect the language of this text: "{text}"

Respond with valid JSON:
{{
  "language_code": "en",  // ISO 639-1 code
  "language_name": "English",
  "confidence": 0.95  // 0-1
}}"""


# Helper functions

def format_symptom_list(symptoms: Dict[str, SymptomInfo]) -> str:
    """
    Format symptom dictionary as readable text.
    
    Args:
        symptoms: Dictionary of symptom name to SymptomInfo
        
    Returns:
        Formatted symptom list
    """
    if not symptoms:
        return "No symptoms reported"
    
    lines = []
    for name, info in symptoms.items():
        parts = [name]
        if info.severity:
            parts.append(f"(severity: {info.severity}/10)")
        if info.duration:
            parts.append(f"(duration: {info.duration})")
        lines.append(" ".join(parts))
    
    return "\n".join(lines)


def extract_json_from_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response that may contain additional text.
    
    Args:
        response: LLM response text
        
    Returns:
        Parsed JSON dict or None if not found
    """
    import json
    import re
    
    # Try to find JSON in response
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Try parsing entire response
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return None
