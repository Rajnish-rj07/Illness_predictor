"""
Unit tests for data model classes.
Tests serialization, deserialization, validation, and equality.

Validates: Requirements 1.4, 3.1, 9.2, 10.1, 10.2
"""

import pytest
import json
import numpy as np
from datetime import datetime, timedelta

from src.models.data_models import (
    Session,
    SymptomVector,
    SymptomInfo,
    Prediction,
    Severity,
    Explanation,
    TreatmentInfo,
    Facility,
    Location,
    ModelMetrics,
    ClassMetrics,
    DriftReport,
    DriftType,
    UserFeedback,
    ConversationContext,
    Message,
    SessionStatus,
)


class TestSymptomInfo:
    """Test SymptomInfo dataclass."""
    
    def test_create_symptom_info(self):
        """Test creating a SymptomInfo instance."""
        symptom = SymptomInfo(
            present=True,
            severity=7,
            duration='1-3d',
            description='Mild headache'
        )
        assert symptom.present is True
        assert symptom.severity == 7
        assert symptom.duration == '1-3d'
        assert symptom.description == 'Mild headache'
    
    def test_symptom_info_validation_severity(self):
        """Test severity validation."""
        # Valid severity
        symptom = SymptomInfo(present=True, severity=5)
        symptom.validate()  # Should not raise
        
        # Invalid severity (too low)
        symptom_low = SymptomInfo(present=True, severity=0)
        with pytest.raises(ValueError, match="Severity must be between 1 and 10"):
            symptom_low.validate()
        
        # Invalid severity (too high)
        symptom_high = SymptomInfo(present=True, severity=11)
        with pytest.raises(ValueError, match="Severity must be between 1 and 10"):
            symptom_high.validate()
    
    def test_symptom_info_validation_duration(self):
        """Test duration validation."""
        # Valid duration
        symptom = SymptomInfo(present=True, duration='3-7d')
        symptom.validate()  # Should not raise
        
        # Invalid duration
        symptom_invalid = SymptomInfo(present=True, duration='invalid')
        with pytest.raises(ValueError, match="Duration must be one of"):
            symptom_invalid.validate()
    
    def test_symptom_info_serialization(self):
        """Test SymptomInfo serialization to dict and JSON."""
        symptom = SymptomInfo(
            present=True,
            severity=8,
            duration='1-3d',
            description='Severe headache'
        )
        
        # Test to_dict
        data = symptom.to_dict()
        assert data['present'] is True
        assert data['severity'] == 8
        assert data['duration'] == '1-3d'
        assert data['description'] == 'Severe headache'
        
        # Test to_json
        json_str = symptom.to_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed['severity'] == 8
    
    def test_symptom_info_deserialization(self):
        """Test SymptomInfo deserialization from dict and JSON."""
        data = {
            'present': True,
            'severity': 6,
            'duration': '3-7d',
            'description': 'Moderate fever'
        }
        
        # Test from_dict
        symptom = SymptomInfo.from_dict(data)
        assert symptom.present is True
        assert symptom.severity == 6
        assert symptom.duration == '3-7d'
        assert symptom.description == 'Moderate fever'
        
        # Test from_json
        json_str = json.dumps(data)
        symptom2 = SymptomInfo.from_json(json_str)
        assert symptom2.severity == 6
    
    def test_symptom_info_round_trip(self):
        """Test serialization round-trip preserves data."""
        original = SymptomInfo(
            present=True,
            severity=9,
            duration='>7d',
            description='Persistent cough'
        )
        
        # Round-trip through dict
        restored = SymptomInfo.from_dict(original.to_dict())
        assert restored.present == original.present
        assert restored.severity == original.severity
        assert restored.duration == original.duration
        assert restored.description == original.description
        
        # Round-trip through JSON
        restored_json = SymptomInfo.from_json(original.to_json())
        assert restored_json.severity == original.severity


class TestSymptomVector:
    """Test SymptomVector dataclass."""
    
    def test_create_symptom_vector(self):
        """Test creating a SymptomVector instance."""
        symptoms = {
            'fever': SymptomInfo(present=True, severity=8),
            'cough': SymptomInfo(present=True, severity=6),
        }
        vector = SymptomVector(
            symptoms=symptoms,
            question_count=3,
            confidence_threshold_met=False
        )
        assert len(vector.symptoms) == 2
        assert vector.question_count == 3
        assert vector.confidence_threshold_met is False
    
    def test_symptom_vector_validation(self):
        """Test SymptomVector validation."""
        # Valid vector
        vector = SymptomVector(question_count=10)
        vector.validate()  # Should not raise
        
        # Invalid: negative question count
        vector_neg = SymptomVector(question_count=-1)
        with pytest.raises(ValueError, match="Question count cannot be negative"):
            vector_neg.validate()
        
        # Invalid: exceeds max questions
        vector_max = SymptomVector(question_count=16)
        with pytest.raises(ValueError, match="Question count cannot exceed 15"):
            vector_max.validate()
    
    def test_symptom_vector_serialization(self):
        """Test SymptomVector serialization."""
        symptoms = {
            'fever': SymptomInfo(present=True, severity=7, duration='1-3d'),
        }
        vector = SymptomVector(symptoms=symptoms, question_count=5)
        
        data = vector.to_dict()
        assert 'symptoms' in data
        assert 'fever' in data['symptoms']
        assert data['question_count'] == 5
        
        json_str = vector.to_json()
        assert isinstance(json_str, str)
    
    def test_symptom_vector_deserialization(self):
        """Test SymptomVector deserialization."""
        data = {
            'symptoms': {
                'headache': {
                    'present': True,
                    'severity': 8,
                    'duration': '3-7d',
                    'description': 'Throbbing pain'
                }
            },
            'question_count': 7,
            'confidence_threshold_met': True
        }
        
        vector = SymptomVector.from_dict(data)
        assert 'headache' in vector.symptoms
        assert vector.symptoms['headache'].severity == 8
        assert vector.question_count == 7
        assert vector.confidence_threshold_met is True
    
    def test_symptom_vector_round_trip(self):
        """Test SymptomVector round-trip serialization."""
        symptoms = {
            'fever': SymptomInfo(present=True, severity=9, duration='>7d'),
            'fatigue': SymptomInfo(present=True, severity=7, duration='3-7d'),
        }
        original = SymptomVector(symptoms=symptoms, question_count=12)
        
        restored = SymptomVector.from_dict(original.to_dict())
        assert len(restored.symptoms) == len(original.symptoms)
        assert restored.question_count == original.question_count


class TestPrediction:
    """Test Prediction dataclass."""
    
    def test_create_prediction(self):
        """Test creating a Prediction instance."""
        prediction = Prediction(
            illness='influenza',
            confidence_score=0.85,
            severity=Severity.MODERATE
        )
        assert prediction.illness == 'influenza'
        assert prediction.confidence_score == 0.85
        assert prediction.severity == Severity.MODERATE
    
    def test_prediction_validation_confidence(self):
        """Test confidence score validation."""
        # Valid confidence
        prediction = Prediction(illness='flu', confidence_score=0.75, severity=Severity.LOW)
        prediction.validate()  # Should not raise
        
        # Invalid: below minimum threshold
        prediction_low = Prediction(illness='flu', confidence_score=0.25, severity=Severity.LOW)
        with pytest.raises(ValueError, match="Confidence score must be at least 0.30"):
            prediction_low.validate()
        
        # Invalid: above 1.0
        prediction_high = Prediction(illness='flu', confidence_score=1.5, severity=Severity.LOW)
        with pytest.raises(ValueError, match="Confidence score must be between 0 and 1"):
            prediction_high.validate()
    
    def test_prediction_validation_illness(self):
        """Test illness name validation."""
        prediction = Prediction(illness='', confidence_score=0.80, severity=Severity.LOW)
        with pytest.raises(ValueError, match="Illness name cannot be empty"):
            prediction.validate()
    
    def test_prediction_serialization(self):
        """Test Prediction serialization."""
        explanation = Explanation(
            top_contributors=[('fever', 0.5), ('cough', 0.3)],
            explanation_text='Based on fever and cough'
        )
        treatment = TreatmentInfo(
            medications=['ibuprofen'],
            non_medication=['rest', 'hydration'],
            disclaimer='Consult a doctor',
            seek_professional=True
        )
        
        prediction = Prediction(
            illness='common cold',
            confidence_score=0.72,
            severity=Severity.LOW,
            explanation=explanation,
            treatment_suggestions=treatment
        )
        
        data = prediction.to_dict()
        assert data['illness'] == 'common cold'
        assert data['confidence_score'] == 0.72
        assert data['severity'] == 'low'
        assert data['explanation'] is not None
        assert data['treatment_suggestions'] is not None
    
    def test_prediction_deserialization(self):
        """Test Prediction deserialization."""
        data = {
            'illness': 'bronchitis',
            'confidence_score': 0.68,
            'severity': 'moderate',
            'explanation': None,
            'treatment_suggestions': None
        }
        
        prediction = Prediction.from_dict(data)
        assert prediction.illness == 'bronchitis'
        assert prediction.confidence_score == 0.68
        assert prediction.severity == Severity.MODERATE
    
    def test_prediction_round_trip(self):
        """Test Prediction round-trip serialization."""
        original = Prediction(
            illness='pneumonia',
            confidence_score=0.91,
            severity=Severity.HIGH
        )
        
        restored = Prediction.from_dict(original.to_dict())
        assert restored.illness == original.illness
        assert restored.confidence_score == original.confidence_score
        assert restored.severity == original.severity


class TestLocation:
    """Test Location dataclass."""
    
    def test_create_location(self):
        """Test creating a Location instance."""
        location = Location(
            latitude=37.7749,
            longitude=-122.4194,
            address='San Francisco, CA'
        )
        assert location.latitude == 37.7749
        assert location.longitude == -122.4194
        assert location.address == 'San Francisco, CA'
    
    def test_location_validation(self):
        """Test location coordinate validation."""
        # Valid location
        location = Location(latitude=0, longitude=0)
        location.validate()  # Should not raise
        
        # Invalid latitude (too low)
        location_lat_low = Location(latitude=-91, longitude=0)
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            location_lat_low.validate()
        
        # Invalid latitude (too high)
        location_lat_high = Location(latitude=91, longitude=0)
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            location_lat_high.validate()
        
        # Invalid longitude (too low)
        location_lon_low = Location(latitude=0, longitude=-181)
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            location_lon_low.validate()
        
        # Invalid longitude (too high)
        location_lon_high = Location(latitude=0, longitude=181)
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            location_lon_high.validate()
    
    def test_location_round_trip(self):
        """Test Location round-trip serialization."""
        original = Location(latitude=40.7128, longitude=-74.0060, address='New York, NY')
        
        restored = Location.from_dict(original.to_dict())
        assert restored.latitude == original.latitude
        assert restored.longitude == original.longitude
        assert restored.address == original.address


class TestFacility:
    """Test Facility dataclass."""
    
    def test_create_facility(self):
        """Test creating a Facility instance."""
        location = Location(latitude=37.7749, longitude=-122.4194)
        facility = Facility(
            name='General Hospital',
            facility_type='hospital',
            location=location,
            distance_km=2.5,
            specialties=['emergency', 'cardiology'],
            contact='555-1234',
            rating=4.5
        )
        assert facility.name == 'General Hospital'
        assert facility.facility_type == 'hospital'
        assert facility.distance_km == 2.5
        assert facility.rating == 4.5
    
    def test_facility_validation(self):
        """Test facility validation."""
        location = Location(latitude=0, longitude=0)
        
        # Valid facility
        facility = Facility(
            name='Clinic',
            facility_type='clinic',
            location=location,
            distance_km=1.0
        )
        facility.validate()  # Should not raise
        
        # Invalid: empty name
        facility_no_name = Facility(
            name='',
            facility_type='clinic',
            location=location,
            distance_km=1.0
        )
        with pytest.raises(ValueError, match="Facility name cannot be empty"):
            facility_no_name.validate()
        
        # Invalid: wrong facility type
        facility_bad_type = Facility(
            name='Test',
            facility_type='invalid',
            location=location,
            distance_km=1.0
        )
        with pytest.raises(ValueError, match="Facility type must be one of"):
            facility_bad_type.validate()
        
        # Invalid: negative distance
        facility_neg_dist = Facility(
            name='Test',
            facility_type='hospital',
            location=location,
            distance_km=-1.0
        )
        with pytest.raises(ValueError, match="Distance cannot be negative"):
            facility_neg_dist.validate()
        
        # Invalid: rating out of range
        facility_bad_rating = Facility(
            name='Test',
            facility_type='hospital',
            location=location,
            distance_km=1.0,
            rating=6.0
        )
        with pytest.raises(ValueError, match="Rating must be between 0 and 5"):
            facility_bad_rating.validate()
    
    def test_facility_round_trip(self):
        """Test Facility round-trip serialization."""
        location = Location(latitude=34.0522, longitude=-118.2437)
        original = Facility(
            name='Emergency Center',
            facility_type='emergency',
            location=location,
            distance_km=0.8,
            specialties=['trauma'],
            contact='555-9999',
            rating=4.8
        )
        
        restored = Facility.from_dict(original.to_dict())
        assert restored.name == original.name
        assert restored.facility_type == original.facility_type
        assert restored.distance_km == original.distance_km


class TestSession:
    """Test Session dataclass."""
    
    def test_create_session(self):
        """Test creating a Session instance."""
        now = datetime.utcnow()
        context = ConversationContext()
        vector = SymptomVector()
        
        session = Session(
            session_id='test-123',
            user_id='user-456',
            channel='web',
            language='en',
            created_at=now,
            last_active=now,
            status=SessionStatus.ACTIVE,
            conversation_context=context,
            symptom_vector=vector
        )
        assert session.session_id == 'test-123'
        assert session.channel == 'web'
        assert session.status == SessionStatus.ACTIVE
    
    def test_session_validation(self):
        """Test session validation."""
        now = datetime.utcnow()
        context = ConversationContext()
        vector = SymptomVector()
        
        # Valid session
        session = Session(
            session_id='valid-id',
            user_id='user-123',
            channel='sms',
            language='en',
            created_at=now,
            last_active=now,
            status=SessionStatus.ACTIVE,
            conversation_context=context,
            symptom_vector=vector
        )
        session.validate()  # Should not raise
        
        # Invalid: empty session_id
        session_no_id = Session(
            session_id='',
            user_id='user-123',
            channel='web',
            language='en',
            created_at=now,
            last_active=now,
            status=SessionStatus.ACTIVE,
            conversation_context=context,
            symptom_vector=vector
        )
        with pytest.raises(ValueError, match="Session ID cannot be empty"):
            session_no_id.validate()
        
        # Invalid: wrong channel
        session_bad_channel = Session(
            session_id='test-id',
            user_id='user-123',
            channel='invalid',
            language='en',
            created_at=now,
            last_active=now,
            status=SessionStatus.ACTIVE,
            conversation_context=context,
            symptom_vector=vector
        )
        with pytest.raises(ValueError, match="Channel must be one of"):
            session_bad_channel.validate()
    
    def test_session_is_expired(self):
        """Test session expiration check."""
        now = datetime.utcnow()
        old_time = now - timedelta(hours=25)
        context = ConversationContext()
        vector = SymptomVector()
        
        # Expired session
        expired_session = Session(
            session_id='expired',
            user_id='user-123',
            channel='web',
            language='en',
            created_at=old_time,
            last_active=old_time,
            status=SessionStatus.ACTIVE,
            conversation_context=context,
            symptom_vector=vector
        )
        assert expired_session.is_expired() is True
        
        # Active session
        active_session = Session(
            session_id='active',
            user_id='user-123',
            channel='web',
            language='en',
            created_at=now,
            last_active=now,
            status=SessionStatus.ACTIVE,
            conversation_context=context,
            symptom_vector=vector
        )
        assert active_session.is_expired() is False
    
    def test_session_is_completed(self):
        """Test session completion check."""
        now = datetime.utcnow()
        context = ConversationContext()
        vector = SymptomVector()
        
        completed_session = Session(
            session_id='completed',
            user_id='user-123',
            channel='web',
            language='en',
            created_at=now,
            last_active=now,
            status=SessionStatus.COMPLETED,
            conversation_context=context,
            symptom_vector=vector
        )
        assert completed_session.is_completed() is True
        
        active_session = Session(
            session_id='active',
            user_id='user-123',
            channel='web',
            language='en',
            created_at=now,
            last_active=now,
            status=SessionStatus.ACTIVE,
            conversation_context=context,
            symptom_vector=vector
        )
        assert active_session.is_completed() is False
    
    def test_session_round_trip(self):
        """Test Session round-trip serialization."""
        now = datetime.utcnow()
        context = ConversationContext(
            messages=[Message(role='user', content='I have a fever', timestamp=now)],
            extracted_symptoms=['fever']
        )
        vector = SymptomVector(
            symptoms={'fever': SymptomInfo(present=True, severity=8)},
            question_count=1
        )
        
        original = Session(
            session_id='round-trip-test',
            user_id='user-789',
            channel='whatsapp',
            language='es',
            created_at=now,
            last_active=now,
            status=SessionStatus.ACTIVE,
            conversation_context=context,
            symptom_vector=vector
        )
        
        restored = Session.from_dict(original.to_dict())
        assert restored.session_id == original.session_id
        assert restored.user_id == original.user_id
        assert restored.channel == original.channel
        assert restored.language == original.language
        assert restored.status == original.status
        assert len(restored.conversation_context.messages) == 1
        assert 'fever' in restored.symptom_vector.symptoms


class TestModelMetrics:
    """Test ModelMetrics dataclass."""
    
    def test_create_model_metrics(self):
        """Test creating a ModelMetrics instance."""
        now = datetime.utcnow()
        metrics = ModelMetrics(
            model_version='v1.0.0',
            timestamp=now,
            accuracy=0.85,
            precision=0.82,
            recall=0.88,
            f1_score=0.85,
            top_3_accuracy=0.95
        )
        assert metrics.model_version == 'v1.0.0'
        assert metrics.accuracy == 0.85
        assert metrics.top_3_accuracy == 0.95
    
    def test_model_metrics_validation(self):
        """Test model metrics validation."""
        now = datetime.utcnow()
        
        # Valid metrics
        metrics = ModelMetrics(
            model_version='v1.0.0',
            timestamp=now,
            accuracy=0.90,
            precision=0.88,
            recall=0.92,
            f1_score=0.90
        )
        metrics.validate()  # Should not raise
        
        # Invalid: accuracy out of range
        metrics_bad_acc = ModelMetrics(
            model_version='v1.0.0',
            timestamp=now,
            accuracy=1.5,
            precision=0.88,
            recall=0.92,
            f1_score=0.90
        )
        with pytest.raises(ValueError, match="Accuracy must be between 0 and 1"):
            metrics_bad_acc.validate()
    
    def test_model_metrics_with_per_class(self):
        """Test ModelMetrics with per-class metrics."""
        now = datetime.utcnow()
        per_class = {
            'flu': ClassMetrics(
                illness='flu',
                precision=0.85,
                recall=0.88,
                f1_score=0.86,
                support=100
            ),
            'cold': ClassMetrics(
                illness='cold',
                precision=0.82,
                recall=0.80,
                f1_score=0.81,
                support=150
            )
        }
        
        metrics = ModelMetrics(
            model_version='v1.0.0',
            timestamp=now,
            accuracy=0.84,
            precision=0.83,
            recall=0.84,
            f1_score=0.83,
            per_class_metrics=per_class
        )
        
        metrics.validate()  # Should not raise
        assert len(metrics.per_class_metrics) == 2
        assert 'flu' in metrics.per_class_metrics
    
    def test_model_metrics_round_trip(self):
        """Test ModelMetrics round-trip serialization."""
        now = datetime.utcnow()
        original = ModelMetrics(
            model_version='v2.1.0',
            timestamp=now,
            accuracy=0.92,
            precision=0.90,
            recall=0.93,
            f1_score=0.91,
            top_3_accuracy=0.98
        )
        
        restored = ModelMetrics.from_dict(original.to_dict())
        assert restored.model_version == original.model_version
        assert restored.accuracy == original.accuracy
        assert restored.top_3_accuracy == original.top_3_accuracy


class TestDriftReport:
    """Test DriftReport dataclass."""
    
    def test_create_drift_report(self):
        """Test creating a DriftReport instance."""
        now = datetime.utcnow()
        report = DriftReport(
            timestamp=now,
            drift_type=DriftType.FEATURE_DRIFT,
            feature_drifts={'fever': 0.15, 'cough': 0.08},
            concept_drift_score=0.02,
            recommendation='Monitor feature drift',
            visualizations=['drift_plot.png']
        )
        assert report.drift_type == DriftType.FEATURE_DRIFT
        assert report.feature_drifts['fever'] == 0.15
    
    def test_drift_report_validation(self):
        """Test drift report validation."""
        now = datetime.utcnow()
        
        # Valid report
        report = DriftReport(
            timestamp=now,
            drift_type=DriftType.NO_DRIFT,
            feature_drifts={},
            concept_drift_score=0.01,
            recommendation='No action needed'
        )
        report.validate()  # Should not raise
        
        # Invalid: negative PSI score
        report_neg_psi = DriftReport(
            timestamp=now,
            drift_type=DriftType.FEATURE_DRIFT,
            feature_drifts={'symptom1': -0.1},
            concept_drift_score=0.01,
            recommendation='Test'
        )
        with pytest.raises(ValueError, match="PSI score.*cannot be negative"):
            report_neg_psi.validate()
        
        # Invalid: negative concept drift score
        report_neg_concept = DriftReport(
            timestamp=now,
            drift_type=DriftType.CONCEPT_DRIFT,
            feature_drifts={},
            concept_drift_score=-0.05,
            recommendation='Test'
        )
        with pytest.raises(ValueError, match="Concept drift score cannot be negative"):
            report_neg_concept.validate()
    
    def test_drift_report_round_trip(self):
        """Test DriftReport round-trip serialization."""
        now = datetime.utcnow()
        original = DriftReport(
            timestamp=now,
            drift_type=DriftType.BOTH,
            feature_drifts={'fever': 0.28, 'headache': 0.32},
            concept_drift_score=0.07,
            recommendation='Retrain model immediately',
            visualizations=['drift1.png', 'drift2.png']
        )
        
        restored = DriftReport.from_dict(original.to_dict())
        assert restored.drift_type == original.drift_type
        assert restored.feature_drifts == original.feature_drifts
        assert restored.concept_drift_score == original.concept_drift_score


class TestUserFeedback:
    """Test UserFeedback dataclass."""
    
    def test_create_user_feedback(self):
        """Test creating a UserFeedback instance."""
        now = datetime.utcnow()
        feedback = UserFeedback(
            session_id='session-123',
            prediction_id='pred-456',
            correct_illness='pneumonia',
            was_correct=False,
            timestamp=now,
            additional_comments='Diagnosis was different'
        )
        assert feedback.session_id == 'session-123'
        assert feedback.was_correct is False
        assert feedback.correct_illness == 'pneumonia'
    
    def test_user_feedback_validation(self):
        """Test user feedback validation."""
        now = datetime.utcnow()
        
        # Valid feedback (correct prediction)
        feedback_correct = UserFeedback(
            session_id='session-123',
            prediction_id='pred-456',
            correct_illness=None,
            was_correct=True,
            timestamp=now
        )
        feedback_correct.validate()  # Should not raise
        
        # Valid feedback (incorrect prediction with correct illness)
        feedback_incorrect = UserFeedback(
            session_id='session-123',
            prediction_id='pred-456',
            correct_illness='bronchitis',
            was_correct=False,
            timestamp=now
        )
        feedback_incorrect.validate()  # Should not raise
        
        # Invalid: incorrect prediction without correct illness
        feedback_missing = UserFeedback(
            session_id='session-123',
            prediction_id='pred-456',
            correct_illness=None,
            was_correct=False,
            timestamp=now
        )
        with pytest.raises(ValueError, match="Correct illness must be provided"):
            feedback_missing.validate()
    
    def test_user_feedback_round_trip(self):
        """Test UserFeedback round-trip serialization."""
        now = datetime.utcnow()
        original = UserFeedback(
            session_id='session-789',
            prediction_id='pred-012',
            correct_illness='strep throat',
            was_correct=False,
            timestamp=now,
            additional_comments='Confirmed by doctor'
        )
        
        restored = UserFeedback.from_dict(original.to_dict())
        assert restored.session_id == original.session_id
        assert restored.prediction_id == original.prediction_id
        assert restored.was_correct == original.was_correct
        assert restored.correct_illness == original.correct_illness


class TestExplanation:
    """Test Explanation dataclass."""
    
    def test_create_explanation(self):
        """Test creating an Explanation instance."""
        explanation = Explanation(
            top_contributors=[('fever', 0.45), ('cough', 0.32), ('fatigue', 0.18)],
            explanation_text='The prediction is based primarily on fever symptoms',
            shap_values=np.array([0.45, 0.32, 0.18, 0.05])
        )
        assert len(explanation.top_contributors) == 3
        assert explanation.top_contributors[0][0] == 'fever'
        assert explanation.shap_values is not None
    
    def test_explanation_validation(self):
        """Test explanation validation."""
        # Valid explanation (3 contributors)
        explanation = Explanation(
            top_contributors=[('s1', 0.5), ('s2', 0.3), ('s3', 0.2)]
        )
        explanation.validate()  # Should not raise
        
        # Invalid: too many contributors
        explanation_too_many = Explanation(
            top_contributors=[('s1', 0.4), ('s2', 0.3), ('s3', 0.2), ('s4', 0.1)]
        )
        with pytest.raises(ValueError, match="Top contributors should be at most 3"):
            explanation_too_many.validate()
    
    def test_explanation_with_numpy_round_trip(self):
        """Test Explanation serialization with numpy arrays."""
        shap_vals = np.array([0.5, 0.3, 0.15, 0.05])
        original = Explanation(
            top_contributors=[('fever', 0.5), ('cough', 0.3)],
            explanation_text='Test explanation',
            shap_values=shap_vals
        )
        
        # Serialize and deserialize
        data = original.to_dict()
        assert isinstance(data['shap_values'], list)
        
        restored = Explanation.from_dict(data)
        assert isinstance(restored.shap_values, np.ndarray)
        assert np.array_equal(restored.shap_values, shap_vals)


class TestTreatmentInfo:
    """Test TreatmentInfo dataclass."""
    
    def test_create_treatment_info(self):
        """Test creating a TreatmentInfo instance."""
        treatment = TreatmentInfo(
            medications=['acetaminophen', 'ibuprofen'],
            non_medication=['rest', 'hydration', 'warm compress'],
            disclaimer='This is not medical advice. Consult a healthcare professional.',
            seek_professional=True
        )
        assert len(treatment.medications) == 2
        assert len(treatment.non_medication) == 3
        assert treatment.seek_professional is True
    
    def test_treatment_info_round_trip(self):
        """Test TreatmentInfo round-trip serialization."""
        original = TreatmentInfo(
            medications=['aspirin'],
            non_medication=['rest', 'fluids'],
            disclaimer='Consult your doctor',
            seek_professional=True
        )
        
        restored = TreatmentInfo.from_dict(original.to_dict())
        assert restored.medications == original.medications
        assert restored.non_medication == original.non_medication
        assert restored.seek_professional == original.seek_professional


class TestConversationContext:
    """Test ConversationContext dataclass."""
    
    def test_create_conversation_context(self):
        """Test creating a ConversationContext instance."""
        now = datetime.utcnow()
        messages = [
            Message(role='user', content='I have a fever', timestamp=now),
            Message(role='assistant', content='How long have you had the fever?', timestamp=now)
        ]
        context = ConversationContext(
            messages=messages,
            extracted_symptoms=['fever']
        )
        assert len(context.messages) == 2
        assert len(context.extracted_symptoms) == 1
    
    def test_conversation_context_round_trip(self):
        """Test ConversationContext round-trip serialization."""
        now = datetime.utcnow()
        messages = [
            Message(role='user', content='I feel sick', timestamp=now),
            Message(role='assistant', content='Can you describe your symptoms?', timestamp=now)
        ]
        original = ConversationContext(
            messages=messages,
            extracted_symptoms=['fever', 'cough']
        )
        
        restored = ConversationContext.from_dict(original.to_dict())
        assert len(restored.messages) == len(original.messages)
        assert restored.messages[0].role == 'user'
        assert restored.extracted_symptoms == original.extracted_symptoms


class TestClassMetrics:
    """Test ClassMetrics dataclass."""
    
    def test_create_class_metrics(self):
        """Test creating a ClassMetrics instance."""
        metrics = ClassMetrics(
            illness='influenza',
            precision=0.88,
            recall=0.85,
            f1_score=0.86,
            support=120
        )
        assert metrics.illness == 'influenza'
        assert metrics.precision == 0.88
        assert metrics.support == 120
    
    def test_class_metrics_validation(self):
        """Test class metrics validation."""
        # Valid metrics
        metrics = ClassMetrics(
            illness='cold',
            precision=0.90,
            recall=0.88,
            f1_score=0.89,
            support=100
        )
        metrics.validate()  # Should not raise
        
        # Invalid: precision out of range
        metrics_bad_prec = ClassMetrics(
            illness='cold',
            precision=1.5,
            recall=0.88,
            f1_score=0.89,
            support=100
        )
        with pytest.raises(ValueError, match="Precision must be between 0 and 1"):
            metrics_bad_prec.validate()
        
        # Invalid: negative support
        metrics_neg_support = ClassMetrics(
            illness='cold',
            precision=0.90,
            recall=0.88,
            f1_score=0.89,
            support=-10
        )
        with pytest.raises(ValueError, match="Support cannot be negative"):
            metrics_neg_support.validate()
    
    def test_class_metrics_round_trip(self):
        """Test ClassMetrics round-trip serialization."""
        original = ClassMetrics(
            illness='pneumonia',
            precision=0.92,
            recall=0.89,
            f1_score=0.90,
            support=85
        )
        
        restored = ClassMetrics.from_dict(original.to_dict())
        assert restored.illness == original.illness
        assert restored.precision == original.precision
        assert restored.support == original.support


# ============================================================================
# Property-Based Tests
# ============================================================================

from hypothesis import given, strategies as st
from hypothesis.strategies import composite


# Custom strategies for generating test data
@composite
def symptom_info_strategy(draw):
    """Generate valid SymptomInfo instances."""
    return SymptomInfo(
        present=draw(st.booleans()),
        severity=draw(st.one_of(st.none(), st.integers(min_value=1, max_value=10))),
        duration=draw(st.one_of(st.none(), st.sampled_from(['<1d', '1-3d', '3-7d', '>7d']))),
        description=draw(st.text(min_size=0, max_size=200))
    )


@composite
def symptom_vector_strategy(draw):
    """Generate valid SymptomVector instances."""
    num_symptoms = draw(st.integers(min_value=0, max_value=10))
    symptoms = {}
    for i in range(num_symptoms):
        symptom_name = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(min_codepoint=97, max_codepoint=122)))
        symptoms[symptom_name] = draw(symptom_info_strategy())
    
    return SymptomVector(
        symptoms=symptoms,
        question_count=draw(st.integers(min_value=0, max_value=15)),
        confidence_threshold_met=draw(st.booleans())
    )


@composite
def location_strategy(draw):
    """Generate valid Location instances."""
    return Location(
        latitude=draw(st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False)),
        longitude=draw(st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False)),
        address=draw(st.text(min_size=0, max_size=200))
    )


@composite
def explanation_strategy(draw):
    """Generate valid Explanation instances."""
    num_contributors = draw(st.integers(min_value=0, max_value=3))
    top_contributors = [
        (draw(st.text(min_size=1, max_size=50)), draw(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False)))
        for _ in range(num_contributors)
    ]
    
    # Generate numpy array or None
    shap_values = None
    if draw(st.booleans()):
        arr_size = draw(st.integers(min_value=1, max_value=20))
        shap_values = np.array([draw(st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False)) for _ in range(arr_size)])
    
    return Explanation(
        top_contributors=top_contributors,
        explanation_text=draw(st.text(min_size=0, max_size=500)),
        shap_values=shap_values
    )


@composite
def treatment_info_strategy(draw):
    """Generate valid TreatmentInfo instances."""
    return TreatmentInfo(
        medications=draw(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=5)),
        non_medication=draw(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=5)),
        disclaimer=draw(st.text(min_size=0, max_size=500)),
        seek_professional=draw(st.booleans())
    )


@composite
def prediction_strategy(draw):
    """Generate valid Prediction instances."""
    explanation = draw(st.one_of(st.none(), explanation_strategy()))
    treatment = draw(st.one_of(st.none(), treatment_info_strategy()))
    
    return Prediction(
        illness=draw(st.text(min_size=1, max_size=100)),
        confidence_score=draw(st.floats(min_value=0.30, max_value=1.0, allow_nan=False, allow_infinity=False)),
        severity=draw(st.sampled_from([Severity.LOW, Severity.MODERATE, Severity.HIGH, Severity.CRITICAL])),
        explanation=explanation,
        treatment_suggestions=treatment
    )


@composite
def facility_strategy(draw):
    """Generate valid Facility instances."""
    return Facility(
        name=draw(st.text(min_size=1, max_size=100)),
        facility_type=draw(st.sampled_from(['hospital', 'clinic', 'emergency'])),
        location=draw(location_strategy()),
        distance_km=draw(st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False)),
        specialties=draw(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=10)),
        contact=draw(st.text(min_size=0, max_size=50)),
        rating=draw(st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False))
    )


@composite
def message_strategy(draw):
    """Generate valid Message instances."""
    # Generate a datetime within a reasonable range
    days_offset = draw(st.integers(min_value=-365, max_value=0))
    timestamp = datetime.utcnow() + timedelta(days=days_offset)
    
    return Message(
        role=draw(st.sampled_from(['user', 'assistant'])),
        content=draw(st.text(min_size=1, max_size=500)),
        timestamp=timestamp
    )


@composite
def conversation_context_strategy(draw):
    """Generate valid ConversationContext instances."""
    num_messages = draw(st.integers(min_value=0, max_value=10))
    messages = [draw(message_strategy()) for _ in range(num_messages)]
    
    return ConversationContext(
        messages=messages,
        extracted_symptoms=draw(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=10))
    )


@composite
def session_strategy(draw):
    """Generate valid Session instances."""
    # Generate timestamps
    days_offset = draw(st.integers(min_value=-30, max_value=0))
    created_at = datetime.utcnow() + timedelta(days=days_offset)
    hours_offset = draw(st.integers(min_value=0, max_value=48))
    last_active = created_at + timedelta(hours=hours_offset)
    
    return Session(
        session_id=draw(st.text(min_size=1, max_size=100)),
        user_id=draw(st.text(min_size=1, max_size=100)),
        channel=draw(st.sampled_from(['sms', 'whatsapp', 'web'])),
        language=draw(st.text(min_size=2, max_size=10)),
        created_at=created_at,
        last_active=last_active,
        status=draw(st.sampled_from([SessionStatus.ACTIVE, SessionStatus.COMPLETED, SessionStatus.EXPIRED])),
        conversation_context=draw(conversation_context_strategy()),
        symptom_vector=draw(symptom_vector_strategy())
    )


@composite
def class_metrics_strategy(draw):
    """Generate valid ClassMetrics instances."""
    return ClassMetrics(
        illness=draw(st.text(min_size=1, max_size=100)),
        precision=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        recall=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        f1_score=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        support=draw(st.integers(min_value=0, max_value=10000))
    )


@composite
def model_metrics_strategy(draw):
    """Generate valid ModelMetrics instances."""
    days_offset = draw(st.integers(min_value=-365, max_value=0))
    timestamp = datetime.utcnow() + timedelta(days=days_offset)
    
    # Generate per-class metrics
    num_classes = draw(st.integers(min_value=0, max_value=5))
    per_class = {}
    for i in range(num_classes):
        illness_name = draw(st.text(min_size=1, max_size=50))
        per_class[illness_name] = draw(class_metrics_strategy())
    
    return ModelMetrics(
        model_version=draw(st.text(min_size=1, max_size=50)),
        timestamp=timestamp,
        accuracy=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        precision=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        recall=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        f1_score=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        top_3_accuracy=draw(st.one_of(st.none(), st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))),
        per_class_metrics=per_class
    )


@composite
def drift_report_strategy(draw):
    """Generate valid DriftReport instances."""
    days_offset = draw(st.integers(min_value=-365, max_value=0))
    timestamp = datetime.utcnow() + timedelta(days=days_offset)
    
    # Generate feature drifts (non-negative PSI scores)
    num_features = draw(st.integers(min_value=0, max_value=10))
    feature_drifts = {}
    for i in range(num_features):
        feature_name = draw(st.text(min_size=1, max_size=50))
        feature_drifts[feature_name] = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    
    return DriftReport(
        timestamp=timestamp,
        drift_type=draw(st.sampled_from([DriftType.NO_DRIFT, DriftType.FEATURE_DRIFT, DriftType.CONCEPT_DRIFT, DriftType.BOTH])),
        feature_drifts=feature_drifts,
        concept_drift_score=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)),
        recommendation=draw(st.text(min_size=0, max_size=500)),
        visualizations=draw(st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=5))
    )


@composite
def user_feedback_strategy(draw):
    """Generate valid UserFeedback instances."""
    days_offset = draw(st.integers(min_value=-365, max_value=0))
    timestamp = datetime.utcnow() + timedelta(days=days_offset)
    
    was_correct = draw(st.booleans())
    # If was_correct is False, we need to provide correct_illness
    correct_illness = None
    if not was_correct:
        correct_illness = draw(st.text(min_size=1, max_size=100))
    
    return UserFeedback(
        session_id=draw(st.text(min_size=1, max_size=100)),
        prediction_id=draw(st.text(min_size=1, max_size=100)),
        correct_illness=correct_illness,
        was_correct=was_correct,
        timestamp=timestamp,
        additional_comments=draw(st.one_of(st.none(), st.text(min_size=0, max_size=500)))
    )


# ============================================================================
# Property-Based Test: Serialization Round-Trip
# **Validates: Requirements 10.2, 10.3**
# ============================================================================

class TestSerializationRoundTrip:
    """
    Property-based tests for data model serialization round-trip.
    
    Property: Serialization round-trip
    For any data model instance, serializing then deserializing should produce
    an equivalent object with all fields preserved.
    
    Validates: Requirements 10.2, 10.3
    """
    
    @given(symptom_info=symptom_info_strategy())
    def test_property_symptom_info_round_trip(self, symptom_info):
        """
        **Validates: Requirements 10.2, 10.3**
        Test that SymptomInfo serialization round-trip preserves all data.
        """
        # Serialize to dict and deserialize
        restored = SymptomInfo.from_dict(symptom_info.to_dict())
        
        assert restored.present == symptom_info.present
        assert restored.severity == symptom_info.severity
        assert restored.duration == symptom_info.duration
        assert restored.description == symptom_info.description
        
        # Serialize to JSON and deserialize
        restored_json = SymptomInfo.from_json(symptom_info.to_json())
        
        assert restored_json.present == symptom_info.present
        assert restored_json.severity == symptom_info.severity
        assert restored_json.duration == symptom_info.duration
        assert restored_json.description == symptom_info.description
    
    @given(symptom_vector=symptom_vector_strategy())
    def test_property_symptom_vector_round_trip(self, symptom_vector):
        """
        **Validates: Requirements 10.2, 10.3**
        Test that SymptomVector serialization round-trip preserves all data.
        """
        # Serialize to dict and deserialize
        restored = SymptomVector.from_dict(symptom_vector.to_dict())
        
        assert len(restored.symptoms) == len(symptom_vector.symptoms)
        assert restored.question_count == symptom_vector.question_count
        assert restored.confidence_threshold_met == symptom_vector.confidence_threshold_met
        
        # Check each symptom is preserved
        for symptom_name, symptom_info in symptom_vector.symptoms.items():
            assert symptom_name in restored.symptoms
            assert restored.symptoms[symptom_name].present == symptom_info.present
            assert restored.symptoms[symptom_name].severity == symptom_info.severity
            assert restored.symptoms[symptom_name].duration == symptom_info.duration
        
        # Serialize to JSON and deserialize
        restored_json = SymptomVector.from_json(symptom_vector.to_json())
        assert len(restored_json.symptoms) == len(symptom_vector.symptoms)
        assert restored_json.question_count == symptom_vector.question_count
    
    @given(location=location_strategy())
    def test_property_location_round_trip(self, location):
        """
        **Validates: Requirements 10.2, 10.3**
        Test that Location serialization round-trip preserves all data.
        """
        # Serialize to dict and deserialize
        restored = Location.from_dict(location.to_dict())
        
        assert restored.latitude == location.latitude
        assert restored.longitude == location.longitude
        assert restored.address == location.address
        
        # Serialize to JSON and deserialize
        restored_json = Location.from_json(location.to_json())
        
        assert restored_json.latitude == location.latitude
        assert restored_json.longitude == location.longitude
        assert restored_json.address == location.address
    
    @given(explanation=explanation_strategy())
    def test_property_explanation_round_trip(self, explanation):
        """
        **Validates: Requirements 10.2, 10.3**
        Test that Explanation serialization round-trip preserves all data.
        """
        # Serialize to dict and deserialize
        restored = Explanation.from_dict(explanation.to_dict())
        
        assert len(restored.top_contributors) == len(explanation.top_contributors)
        assert restored.explanation_text == explanation.explanation_text
        
        # Check numpy array preservation
        if explanation.shap_values is not None:
            assert restored.shap_values is not None
            assert np.array_equal(restored.shap_values, explanation.shap_values)
        else:
            assert restored.shap_values is None
        
        # Serialize to JSON and deserialize
        restored_json = Explanation.from_json(explanation.to_json())
        assert len(restored_json.top_contributors) == len(explanation.top_contributors)
    
    @given(treatment=treatment_info_strategy())
    def test_property_treatment_info_round_trip(self, treatment):
        """
        **Validates: Requirements 10.2, 10.3**
        Test that TreatmentInfo serialization round-trip preserves all data.
        """
        # Serialize to dict and deserialize
        restored = TreatmentInfo.from_dict(treatment.to_dict())
        
        assert restored.medications == treatment.medications
        assert restored.non_medication == treatment.non_medication
        assert restored.disclaimer == treatment.disclaimer
        assert restored.seek_professional == treatment.seek_professional
        
        # Serialize to JSON and deserialize
        restored_json = TreatmentInfo.from_json(treatment.to_json())
        
        assert restored_json.medications == treatment.medications
        assert restored_json.seek_professional == treatment.seek_professional
    
    @given(prediction=prediction_strategy())
    def test_property_prediction_round_trip(self, prediction):
        """
        **Validates: Requirements 10.2, 10.3**
        Test that Prediction serialization round-trip preserves all data.
        """
        # Serialize to dict and deserialize
        restored = Prediction.from_dict(prediction.to_dict())
        
        assert restored.illness == prediction.illness
        assert restored.confidence_score == prediction.confidence_score
        assert restored.severity == prediction.severity
        
        # Check nested objects
        if prediction.explanation is not None:
            assert restored.explanation is not None
            assert len(restored.explanation.top_contributors) == len(prediction.explanation.top_contributors)
        else:
            assert restored.explanation is None
        
        if prediction.treatment_suggestions is not None:
            assert restored.treatment_suggestions is not None
            assert restored.treatment_suggestions.seek_professional == prediction.treatment_suggestions.seek_professional
        else:
            assert restored.treatment_suggestions is None
        
        # Serialize to JSON and deserialize
        restored_json = Prediction.from_json(prediction.to_json())
        
        assert restored_json.illness == prediction.illness
        assert restored_json.confidence_score == prediction.confidence_score
        assert restored_json.severity == prediction.severity
    
    @given(facility=facility_strategy())
    def test_property_facility_round_trip(self, facility):
        """
        **Validates: Requirements 10.2, 10.3**
        Test that Facility serialization round-trip preserves all data.
        """
        # Serialize to dict and deserialize
        restored = Facility.from_dict(facility.to_dict())
        
        assert restored.name == facility.name
        assert restored.facility_type == facility.facility_type
        assert restored.distance_km == facility.distance_km
        assert restored.specialties == facility.specialties
        assert restored.contact == facility.contact
        assert restored.rating == facility.rating
        assert restored.location.latitude == facility.location.latitude
        assert restored.location.longitude == facility.location.longitude
        
        # Serialize to JSON and deserialize
        restored_json = Facility.from_json(facility.to_json())
        
        assert restored_json.name == facility.name
        assert restored_json.facility_type == facility.facility_type
    
    @given(session=session_strategy())
    def test_property_session_round_trip(self, session):
        """
        **Validates: Requirements 10.2, 10.3**
        Test that Session serialization round-trip preserves all data.
        """
        # Serialize to dict and deserialize
        restored = Session.from_dict(session.to_dict())
        
        assert restored.session_id == session.session_id
        assert restored.user_id == session.user_id
        assert restored.channel == session.channel
        assert restored.language == session.language
        assert restored.status == session.status
        
        # Check timestamps (compare as ISO strings to avoid microsecond precision issues)
        assert restored.created_at.isoformat() == session.created_at.isoformat()
        assert restored.last_active.isoformat() == session.last_active.isoformat()
        
        # Check nested objects
        assert len(restored.conversation_context.messages) == len(session.conversation_context.messages)
        assert len(restored.symptom_vector.symptoms) == len(session.symptom_vector.symptoms)
        assert restored.symptom_vector.question_count == session.symptom_vector.question_count
        
        # Serialize to JSON and deserialize
        restored_json = Session.from_json(session.to_json())
        
        assert restored_json.session_id == session.session_id
        assert restored_json.user_id == session.user_id
        assert restored_json.channel == session.channel
    
    @given(class_metrics=class_metrics_strategy())
    def test_property_class_metrics_round_trip(self, class_metrics):
        """
        **Validates: Requirements 10.2, 10.3**
        Test that ClassMetrics serialization round-trip preserves all data.
        """
        # Serialize to dict and deserialize
        restored = ClassMetrics.from_dict(class_metrics.to_dict())
        
        assert restored.illness == class_metrics.illness
        assert restored.precision == class_metrics.precision
        assert restored.recall == class_metrics.recall
        assert restored.f1_score == class_metrics.f1_score
        assert restored.support == class_metrics.support
    
    @given(model_metrics=model_metrics_strategy())
    def test_property_model_metrics_round_trip(self, model_metrics):
        """
        **Validates: Requirements 10.2, 10.3**
        Test that ModelMetrics serialization round-trip preserves all data.
        """
        # Serialize to dict and deserialize
        restored = ModelMetrics.from_dict(model_metrics.to_dict())
        
        assert restored.model_version == model_metrics.model_version
        assert restored.accuracy == model_metrics.accuracy
        assert restored.precision == model_metrics.precision
        assert restored.recall == model_metrics.recall
        assert restored.f1_score == model_metrics.f1_score
        assert restored.top_3_accuracy == model_metrics.top_3_accuracy
        
        # Check per-class metrics
        assert len(restored.per_class_metrics) == len(model_metrics.per_class_metrics)
        for illness, metrics in model_metrics.per_class_metrics.items():
            assert illness in restored.per_class_metrics
            assert restored.per_class_metrics[illness].precision == metrics.precision
        
        # Serialize to JSON and deserialize
        restored_json = ModelMetrics.from_json(model_metrics.to_json())
        
        assert restored_json.model_version == model_metrics.model_version
        assert restored_json.accuracy == model_metrics.accuracy
    
    @given(drift_report=drift_report_strategy())
    def test_property_drift_report_round_trip(self, drift_report):
        """
        **Validates: Requirements 10.2, 10.3**
        Test that DriftReport serialization round-trip preserves all data.
        """
        # Serialize to dict and deserialize
        restored = DriftReport.from_dict(drift_report.to_dict())
        
        assert restored.drift_type == drift_report.drift_type
        assert restored.feature_drifts == drift_report.feature_drifts
        assert restored.concept_drift_score == drift_report.concept_drift_score
        assert restored.recommendation == drift_report.recommendation
        assert restored.visualizations == drift_report.visualizations
        
        # Serialize to JSON and deserialize
        restored_json = DriftReport.from_json(drift_report.to_json())
        
        assert restored_json.drift_type == drift_report.drift_type
        assert restored_json.concept_drift_score == drift_report.concept_drift_score
    
    @given(user_feedback=user_feedback_strategy())
    def test_property_user_feedback_round_trip(self, user_feedback):
        """
        **Validates: Requirements 10.2, 10.3**
        Test that UserFeedback serialization round-trip preserves all data.
        """
        # Serialize to dict and deserialize
        restored = UserFeedback.from_dict(user_feedback.to_dict())
        
        assert restored.session_id == user_feedback.session_id
        assert restored.prediction_id == user_feedback.prediction_id
        assert restored.correct_illness == user_feedback.correct_illness
        assert restored.was_correct == user_feedback.was_correct
        assert restored.additional_comments == user_feedback.additional_comments
        
        # Serialize to JSON and deserialize
        restored_json = UserFeedback.from_json(user_feedback.to_json())
        
        assert restored_json.session_id == user_feedback.session_id
        assert restored_json.was_correct == user_feedback.was_correct
