"""
Application-layer data models for the Illness Prediction System.
These dataclasses represent business entities with serialization/deserialization support.

Validates: Requirements 1.4, 3.1, 9.2, 10.1, 10.2
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import json
import numpy as np


class Severity(str, Enum):
    """Illness severity enumeration."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class DriftType(str, Enum):
    """Drift type enumeration."""
    NO_DRIFT = "no_drift"
    FEATURE_DRIFT = "feature_drift"
    CONCEPT_DRIFT = "concept_drift"
    BOTH = "both"


class SessionStatus(str, Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"


def _serialize_datetime(dt: Optional[datetime]) -> Optional[str]:
    """Serialize datetime to ISO format string."""
    return dt.isoformat() if dt else None


def _deserialize_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Deserialize ISO format string to datetime."""
    return datetime.fromisoformat(dt_str) if dt_str else None


def _serialize_numpy(arr: Optional[np.ndarray]) -> Optional[List]:
    """Serialize numpy array to list."""
    return arr.tolist() if arr is not None else None


def _deserialize_numpy(arr_list: Optional[List]) -> Optional[np.ndarray]:
    """Deserialize list to numpy array."""
    return np.array(arr_list) if arr_list is not None else None


@dataclass
class SymptomInfo:
    """
    Information about a single symptom.
    Validates: Requirements 1.4
    """
    present: bool
    severity: Optional[int] = None  # 1-10 scale
    duration: Optional[str] = None  # '<1d', '1-3d', '3-7d', '>7d'
    description: str = ""  # User's natural language description
    
    def validate(self) -> None:
        """Validate symptom info fields."""
        if self.severity is not None and not (1 <= self.severity <= 10):
            raise ValueError(f"Severity must be between 1 and 10, got {self.severity}")
        
        valid_durations = ['<1d', '1-3d', '3-7d', '>7d']
        if self.duration is not None and self.duration not in valid_durations:
            raise ValueError(f"Duration must be one of {valid_durations}, got {self.duration}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'present': self.present,
            'severity': self.severity,
            'duration': self.duration,
            'description': self.description,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SymptomInfo':
        """Deserialize from dictionary."""
        return cls(
            present=data['present'],
            severity=data.get('severity'),
            duration=data.get('duration'),
            description=data.get('description', ''),
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'SymptomInfo':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class SymptomVector:
    """
    Structured representation of user-reported symptoms.
    Validates: Requirements 1.4, 2.2
    """
    symptoms: Dict[str, SymptomInfo] = field(default_factory=dict)
    question_count: int = 0
    confidence_threshold_met: bool = False
    
    def validate(self) -> None:
        """Validate symptom vector fields."""
        if self.question_count < 0:
            raise ValueError(f"Question count cannot be negative, got {self.question_count}")
        
        if self.question_count > 15:
            raise ValueError(f"Question count cannot exceed 15, got {self.question_count}")
        
        # Validate each symptom
        for symptom_name, symptom_info in self.symptoms.items():
            symptom_info.validate()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'symptoms': {name: info.to_dict() for name, info in self.symptoms.items()},
            'question_count': self.question_count,
            'confidence_threshold_met': self.confidence_threshold_met,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SymptomVector':
        """Deserialize from dictionary."""
        symptoms = {
            name: SymptomInfo.from_dict(info_dict)
            for name, info_dict in data.get('symptoms', {}).items()
        }
        return cls(
            symptoms=symptoms,
            question_count=data.get('question_count', 0),
            confidence_threshold_met=data.get('confidence_threshold_met', False),
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'SymptomVector':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class Message:
    """A single message in a conversation."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': _serialize_datetime(self.timestamp),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Deserialize from dictionary."""
        return cls(
            role=data['role'],
            content=data['content'],
            timestamp=_deserialize_datetime(data.get('timestamp')),
        )


@dataclass
class ConversationContext:
    """Context accumulated during a conversation session."""
    messages: List[Message] = field(default_factory=list)
    extracted_symptoms: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'messages': [msg.to_dict() for msg in self.messages],
            'extracted_symptoms': self.extracted_symptoms,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        """Deserialize from dictionary."""
        messages = [Message.from_dict(msg_dict) for msg_dict in data.get('messages', [])]
        return cls(
            messages=messages,
            extracted_symptoms=data.get('extracted_symptoms', []),
        )


@dataclass
class TreatmentInfo:
    """
    Treatment suggestions for a predicted illness.
    Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
    """
    medications: List[str] = field(default_factory=list)
    non_medication: List[str] = field(default_factory=list)
    disclaimer: str = ""
    seek_professional: bool = True
    
    def validate(self) -> None:
        """Validate treatment info."""
        # Critical/High severity should not have medication suggestions
        if not self.seek_professional and len(self.medications) > 0:
            raise ValueError("Treatment info should not have medications if professional care is not recommended")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'medications': self.medications,
            'non_medication': self.non_medication,
            'disclaimer': self.disclaimer,
            'seek_professional': self.seek_professional,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TreatmentInfo':
        """Deserialize from dictionary."""
        return cls(
            medications=data.get('medications', []),
            non_medication=data.get('non_medication', []),
            disclaimer=data.get('disclaimer', ''),
            seek_professional=data.get('seek_professional', True),
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TreatmentInfo':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class Explanation:
    """
    Explanation for a prediction using SHAP values.
    Validates: Requirements 14.1, 14.2, 14.3
    """
    top_contributors: List[Tuple[str, float]] = field(default_factory=list)
    explanation_text: str = ""
    shap_values: Optional[np.ndarray] = None
    
    def validate(self) -> None:
        """Validate explanation fields."""
        if len(self.top_contributors) > 3:
            raise ValueError(f"Top contributors should be at most 3, got {len(self.top_contributors)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'top_contributors': self.top_contributors,
            'explanation_text': self.explanation_text,
            'shap_values': _serialize_numpy(self.shap_values),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Explanation':
        """Deserialize from dictionary."""
        return cls(
            top_contributors=data.get('top_contributors', []),
            explanation_text=data.get('explanation_text', ''),
            shap_values=_deserialize_numpy(data.get('shap_values')),
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Explanation':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class Prediction:
    """
    An illness prediction with confidence score and metadata.
    Validates: Requirements 3.1, 3.2, 3.3, 3.4, 12.1
    """
    illness: str
    confidence_score: float  # 0-1
    severity: Severity
    explanation: Optional[Explanation] = None
    treatment_suggestions: Optional[TreatmentInfo] = None
    
    def validate(self) -> None:
        """Validate prediction fields."""
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError(f"Confidence score must be between 0 and 1, got {self.confidence_score}")
        
        if self.confidence_score < 0.30:
            raise ValueError(f"Confidence score must be at least 0.30, got {self.confidence_score}")
        
        if not self.illness:
            raise ValueError("Illness name cannot be empty")
        
        # Validate nested objects
        if self.explanation:
            self.explanation.validate()
        if self.treatment_suggestions:
            self.treatment_suggestions.validate()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'illness': self.illness,
            'confidence_score': self.confidence_score,
            'severity': self.severity.value,
            'explanation': self.explanation.to_dict() if self.explanation else None,
            'treatment_suggestions': self.treatment_suggestions.to_dict() if self.treatment_suggestions else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Prediction':
        """Deserialize from dictionary."""
        explanation = Explanation.from_dict(data['explanation']) if data.get('explanation') else None
        treatment = TreatmentInfo.from_dict(data['treatment_suggestions']) if data.get('treatment_suggestions') else None
        
        return cls(
            illness=data['illness'],
            confidence_score=data['confidence_score'],
            severity=Severity(data['severity']),
            explanation=explanation,
            treatment_suggestions=treatment,
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Prediction':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class Location:
    """
    Geographic location information.
    Validates: Requirements 16.1, 16.3
    """
    latitude: float
    longitude: float
    address: str = ""
    
    def validate(self) -> None:
        """Validate location coordinates."""
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Latitude must be between -90 and 90, got {self.latitude}")
        
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Longitude must be between -180 and 180, got {self.longitude}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'address': self.address,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Location':
        """Deserialize from dictionary."""
        return cls(
            latitude=data['latitude'],
            longitude=data['longitude'],
            address=data.get('address', ''),
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Location':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class Facility:
    """
    Healthcare facility information.
    Validates: Requirements 16.1, 16.2, 16.3, 16.4
    """
    name: str
    facility_type: str  # 'hospital', 'clinic', 'emergency'
    location: Location
    distance_km: float
    specialties: List[str] = field(default_factory=list)
    contact: str = ""
    rating: float = 0.0
    
    def validate(self) -> None:
        """Validate facility fields."""
        if not self.name:
            raise ValueError("Facility name cannot be empty")
        
        valid_types = ['hospital', 'clinic', 'emergency']
        if self.facility_type not in valid_types:
            raise ValueError(f"Facility type must be one of {valid_types}, got {self.facility_type}")
        
        if self.distance_km < 0:
            raise ValueError(f"Distance cannot be negative, got {self.distance_km}")
        
        if not (0.0 <= self.rating <= 5.0):
            raise ValueError(f"Rating must be between 0 and 5, got {self.rating}")
        
        self.location.validate()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'name': self.name,
            'facility_type': self.facility_type,
            'location': self.location.to_dict(),
            'distance_km': self.distance_km,
            'specialties': self.specialties,
            'contact': self.contact,
            'rating': self.rating,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Facility':
        """Deserialize from dictionary."""
        return cls(
            name=data['name'],
            facility_type=data['facility_type'],
            location=Location.from_dict(data['location']),
            distance_km=data['distance_km'],
            specialties=data.get('specialties', []),
            contact=data.get('contact', ''),
            rating=data.get('rating', 0.0),
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Facility':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class Session:
    """
    User conversation session.
    Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5
    """
    session_id: str
    user_id: str  # anonymized
    channel: str  # 'sms', 'whatsapp', 'web'
    language: str
    created_at: datetime
    last_active: datetime
    status: SessionStatus
    conversation_context: ConversationContext
    symptom_vector: SymptomVector
    
    def validate(self) -> None:
        """Validate session fields."""
        if not self.session_id:
            raise ValueError("Session ID cannot be empty")
        
        if not self.user_id:
            raise ValueError("User ID cannot be empty")
        
        valid_channels = ['sms', 'whatsapp', 'web']
        if self.channel not in valid_channels:
            raise ValueError(f"Channel must be one of {valid_channels}, got {self.channel}")
        
        # Validate nested objects
        self.symptom_vector.validate()
    
    def is_expired(self) -> bool:
        """Check if session is expired (>24 hours inactive)."""
        from datetime import timedelta
        return (datetime.utcnow() - self.last_active) > timedelta(hours=24)
    
    def is_completed(self) -> bool:
        """Check if session is completed."""
        return self.status == SessionStatus.COMPLETED
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'channel': self.channel,
            'language': self.language,
            'created_at': _serialize_datetime(self.created_at),
            'last_active': _serialize_datetime(self.last_active),
            'status': self.status.value,
            'conversation_context': self.conversation_context.to_dict(),
            'symptom_vector': self.symptom_vector.to_dict(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Deserialize from dictionary."""
        return cls(
            session_id=data['session_id'],
            user_id=data['user_id'],
            channel=data['channel'],
            language=data['language'],
            created_at=_deserialize_datetime(data['created_at']),
            last_active=_deserialize_datetime(data['last_active']),
            status=SessionStatus(data['status']),
            conversation_context=ConversationContext.from_dict(data['conversation_context']),
            symptom_vector=SymptomVector.from_dict(data['symptom_vector']),
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Session':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class ClassMetrics:
    """
    Per-class performance metrics.
    Validates: Requirements 8.4
    """
    illness: str
    precision: float
    recall: float
    f1_score: float
    support: int
    
    def validate(self) -> None:
        """Validate class metrics."""
        if not (0.0 <= self.precision <= 1.0):
            raise ValueError(f"Precision must be between 0 and 1, got {self.precision}")
        
        if not (0.0 <= self.recall <= 1.0):
            raise ValueError(f"Recall must be between 0 and 1, got {self.recall}")
        
        if not (0.0 <= self.f1_score <= 1.0):
            raise ValueError(f"F1 score must be between 0 and 1, got {self.f1_score}")
        
        if self.support < 0:
            raise ValueError(f"Support cannot be negative, got {self.support}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'illness': self.illness,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'support': self.support,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClassMetrics':
        """Deserialize from dictionary."""
        return cls(
            illness=data['illness'],
            precision=data['precision'],
            recall=data['recall'],
            f1_score=data['f1_score'],
            support=data['support'],
        )


@dataclass
class ModelMetrics:
    """
    ML model performance metrics.
    Validates: Requirements 5.3, 8.1, 8.4
    """
    model_version: str
    timestamp: datetime
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    top_3_accuracy: Optional[float] = None
    per_class_metrics: Dict[str, ClassMetrics] = field(default_factory=dict)
    
    def validate(self) -> None:
        """Validate model metrics."""
        if not self.model_version:
            raise ValueError("Model version cannot be empty")
        
        if not (0.0 <= self.accuracy <= 1.0):
            raise ValueError(f"Accuracy must be between 0 and 1, got {self.accuracy}")
        
        if not (0.0 <= self.precision <= 1.0):
            raise ValueError(f"Precision must be between 0 and 1, got {self.precision}")
        
        if not (0.0 <= self.recall <= 1.0):
            raise ValueError(f"Recall must be between 0 and 1, got {self.recall}")
        
        if not (0.0 <= self.f1_score <= 1.0):
            raise ValueError(f"F1 score must be between 0 and 1, got {self.f1_score}")
        
        if self.top_3_accuracy is not None and not (0.0 <= self.top_3_accuracy <= 1.0):
            raise ValueError(f"Top-3 accuracy must be between 0 and 1, got {self.top_3_accuracy}")
        
        # Validate per-class metrics
        for class_metrics in self.per_class_metrics.values():
            class_metrics.validate()
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'model_version': self.model_version,
            'timestamp': _serialize_datetime(self.timestamp),
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'top_3_accuracy': self.top_3_accuracy,
            'per_class_metrics': {
                illness: metrics.to_dict()
                for illness, metrics in self.per_class_metrics.items()
            },
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelMetrics':
        """Deserialize from dictionary."""
        per_class = {
            illness: ClassMetrics.from_dict(metrics_dict)
            for illness, metrics_dict in data.get('per_class_metrics', {}).items()
        }
        
        return cls(
            model_version=data['model_version'],
            timestamp=_deserialize_datetime(data['timestamp']),
            accuracy=data['accuracy'],
            precision=data['precision'],
            recall=data['recall'],
            f1_score=data['f1_score'],
            top_3_accuracy=data.get('top_3_accuracy'),
            per_class_metrics=per_class,
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ModelMetrics':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class DriftReport:
    """
    Data drift detection report.
    Validates: Requirements 7.4, 7.5, 17.1, 17.2, 17.3, 17.4, 17.5
    """
    timestamp: datetime
    drift_type: DriftType
    feature_drifts: Dict[str, float]  # feature -> PSI score
    concept_drift_score: float
    recommendation: str
    visualizations: List[str] = field(default_factory=list)
    
    def validate(self) -> None:
        """Validate drift report fields."""
        # Validate PSI scores (should be non-negative)
        for feature, psi_score in self.feature_drifts.items():
            if psi_score < 0:
                raise ValueError(f"PSI score for {feature} cannot be negative, got {psi_score}")
        
        if self.concept_drift_score < 0:
            raise ValueError(f"Concept drift score cannot be negative, got {self.concept_drift_score}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'timestamp': _serialize_datetime(self.timestamp),
            'drift_type': self.drift_type.value,
            'feature_drifts': self.feature_drifts,
            'concept_drift_score': self.concept_drift_score,
            'recommendation': self.recommendation,
            'visualizations': self.visualizations,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DriftReport':
        """Deserialize from dictionary."""
        return cls(
            timestamp=_deserialize_datetime(data['timestamp']),
            drift_type=DriftType(data['drift_type']),
            feature_drifts=data['feature_drifts'],
            concept_drift_score=data['concept_drift_score'],
            recommendation=data['recommendation'],
            visualizations=data.get('visualizations', []),
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'DriftReport':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class UserFeedback:
    """
    User feedback on prediction accuracy.
    Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5
    """
    session_id: str
    prediction_id: str
    correct_illness: Optional[str]
    was_correct: bool
    timestamp: datetime
    additional_comments: Optional[str] = None
    
    def validate(self) -> None:
        """Validate user feedback fields."""
        if not self.session_id:
            raise ValueError("Session ID cannot be empty")
        
        if not self.prediction_id:
            raise ValueError("Prediction ID cannot be empty")
        
        # If was_correct is False, correct_illness should be provided
        if not self.was_correct and not self.correct_illness:
            raise ValueError("Correct illness must be provided when prediction was incorrect")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'session_id': self.session_id,
            'prediction_id': self.prediction_id,
            'correct_illness': self.correct_illness,
            'was_correct': self.was_correct,
            'timestamp': _serialize_datetime(self.timestamp),
            'additional_comments': self.additional_comments,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserFeedback':
        """Deserialize from dictionary."""
        return cls(
            session_id=data['session_id'],
            prediction_id=data['prediction_id'],
            correct_illness=data.get('correct_illness'),
            was_correct=data['was_correct'],
            timestamp=_deserialize_datetime(data['timestamp']),
            additional_comments=data.get('additional_comments'),
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'UserFeedback':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))
