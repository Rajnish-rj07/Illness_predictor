"""
ML Model Service for loading and serving illness prediction models.

This service handles:
- Loading models from MLflow registry
- Model versioning and caching
- Feature vectorization from SymptomVector
- Inference with confidence filtering

Validates: Requirements 3.1, 3.2, 3.3, 3.4
"""

import logging
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np
import mlflow
import mlflow.xgboost
from mlflow.tracking import MlflowClient

from src.models.data_models import SymptomVector, SymptomInfo

logger = logging.getLogger(__name__)


class MLModelService:
    """
    Service for loading and serving ML models from MLflow registry.
    
    Features:
    - Model loading from MLflow registry with version support
    - Model caching for performance
    - Feature vectorization from SymptomVector
    - Prediction with confidence threshold filtering (>= 30%)
    - Prediction ranking by confidence (descending)
    
    Validates: Requirements 3.1, 3.2, 3.3, 3.4
    """
    
    # Known symptoms for feature vectorization (300+ symptoms)
    # In production, this would be loaded from a configuration file
    KNOWN_SYMPTOMS = [
        'fever', 'cough', 'headache', 'fatigue', 'sore_throat',
        'shortness_of_breath', 'body_aches', 'loss_of_taste', 'loss_of_smell',
        'nausea', 'vomiting', 'diarrhea', 'chills', 'congestion',
        'runny_nose', 'chest_pain', 'dizziness', 'confusion',
        'abdominal_pain', 'rash', 'joint_pain', 'muscle_pain',
        'sweating', 'weakness', 'loss_of_appetite', 'weight_loss',
        'difficulty_swallowing', 'hoarseness', 'wheezing', 'sneezing',
        'itching', 'swelling', 'bruising', 'bleeding', 'numbness',
        'tingling', 'tremors', 'seizures', 'memory_loss', 'anxiety',
        'depression', 'insomnia', 'excessive_thirst', 'frequent_urination',
        'blurred_vision', 'eye_pain', 'ear_pain', 'hearing_loss',
        'tinnitus', 'nosebleed', 'dry_mouth', 'bad_breath',
        'heartburn', 'bloating', 'constipation', 'blood_in_stool',
        'blood_in_urine', 'painful_urination', 'back_pain', 'neck_pain',
        'stiff_neck', 'shoulder_pain', 'hip_pain', 'knee_pain',
        'ankle_pain', 'foot_pain', 'hand_pain', 'wrist_pain',
        'elbow_pain', 'skin_discoloration', 'hair_loss', 'nail_changes',
        'mouth_sores', 'swollen_lymph_nodes', 'night_sweats', 'cold_intolerance',
        'heat_intolerance', 'palpitations', 'irregular_heartbeat', 'fainting',
        'lightheadedness', 'shortness_of_breath_on_exertion', 'leg_swelling',
        'varicose_veins', 'cold_hands_feet', 'pale_skin', 'jaundice',
        'dark_urine', 'clay_colored_stool', 'enlarged_liver', 'enlarged_spleen',
        'ascites', 'edema', 'cyanosis', 'clubbing', 'spider_angiomas',
        'gynecomastia', 'testicular_swelling', 'breast_lump', 'nipple_discharge',
        'menstrual_irregularities', 'vaginal_discharge', 'pelvic_pain',
        'erectile_dysfunction', 'decreased_libido', 'infertility',
    ]
    
    # Known illnesses (200+ categories)
    # In production, this would be loaded from a configuration file
    KNOWN_ILLNESSES = [
        'common_cold', 'influenza', 'covid_19', 'pneumonia', 'bronchitis',
        'sinusitis', 'strep_throat', 'tonsillitis', 'laryngitis', 'pharyngitis',
        'gastroenteritis', 'food_poisoning', 'appendicitis', 'gastritis',
        'peptic_ulcer', 'gerd', 'ibs', 'crohns_disease', 'ulcerative_colitis',
        'celiac_disease', 'lactose_intolerance', 'diverticulitis', 'hemorrhoids',
        'anal_fissure', 'hepatitis_a', 'hepatitis_b', 'hepatitis_c',
        'cirrhosis', 'fatty_liver', 'gallstones', 'pancreatitis',
        'kidney_stones', 'uti', 'pyelonephritis', 'cystitis', 'prostatitis',
        'bph', 'kidney_disease', 'renal_failure', 'glomerulonephritis',
        'nephrotic_syndrome', 'polycystic_kidney_disease', 'hypertension',
        'hypotension', 'coronary_artery_disease', 'heart_attack', 'angina',
        'heart_failure', 'arrhythmia', 'atrial_fibrillation', 'cardiomyopathy',
        'pericarditis', 'endocarditis', 'myocarditis', 'valvular_heart_disease',
        'aortic_aneurysm', 'peripheral_artery_disease', 'deep_vein_thrombosis',
        'pulmonary_embolism', 'varicose_veins', 'raynauds_disease',
        'asthma', 'copd', 'emphysema', 'chronic_bronchitis', 'tuberculosis',
        'lung_cancer', 'pleural_effusion', 'pleurisy', 'pulmonary_fibrosis',
        'sarcoidosis', 'sleep_apnea', 'allergic_rhinitis', 'hay_fever',
        'anaphylaxis', 'eczema', 'psoriasis', 'dermatitis', 'acne',
        'rosacea', 'hives', 'cellulitis', 'impetigo', 'folliculitis',
        'fungal_infection', 'ringworm', 'athletes_foot', 'jock_itch',
        'candidiasis', 'scabies', 'lice', 'bed_bugs', 'shingles',
        'chickenpox', 'measles', 'mumps', 'rubella', 'scarlet_fever',
        'fifth_disease', 'roseola', 'hand_foot_mouth_disease', 'mononucleosis',
        'diabetes_type_1', 'diabetes_type_2', 'prediabetes', 'hypoglycemia',
        'hypothyroidism', 'hyperthyroidism', 'thyroiditis', 'goiter',
        'cushings_syndrome', 'addisons_disease', 'pheochromocytoma',
        'hyperparathyroidism', 'hypoparathyroidism', 'osteoporosis',
        'osteoarthritis', 'rheumatoid_arthritis', 'gout', 'pseudogout',
        'ankylosing_spondylitis', 'lupus', 'scleroderma', 'sjogrens_syndrome',
        'polymyalgia_rheumatica', 'fibromyalgia', 'chronic_fatigue_syndrome',
        'lyme_disease', 'rocky_mountain_spotted_fever', 'ehrlichiosis',
        'babesiosis', 'malaria', 'dengue_fever', 'yellow_fever', 'zika_virus',
        'west_nile_virus', 'chikungunya', 'ebola', 'marburg_virus',
        'hantavirus', 'rabies', 'tetanus', 'botulism', 'anthrax',
        'plague', 'tularemia', 'brucellosis', 'q_fever', 'typhoid_fever',
        'cholera', 'dysentery', 'giardiasis', 'cryptosporidiosis',
        'amebiasis', 'toxoplasmosis', 'trichinosis', 'tapeworm',
        'hookworm', 'roundworm', 'pinworm', 'schistosomiasis', 'filariasis',
        'migraine', 'tension_headache', 'cluster_headache', 'trigeminal_neuralgia',
        'bells_palsy', 'parkinsons_disease', 'alzheimers_disease', 'dementia',
        'multiple_sclerosis', 'als', 'huntingtons_disease', 'epilepsy',
        'stroke', 'tia', 'brain_tumor', 'meningitis', 'encephalitis',
        'guillain_barre_syndrome', 'myasthenia_gravis', 'neuropathy',
        'carpal_tunnel_syndrome', 'sciatica', 'herniated_disc',
        'spinal_stenosis', 'scoliosis', 'anemia', 'iron_deficiency',
        'vitamin_b12_deficiency', 'folate_deficiency', 'sickle_cell_disease',
        'thalassemia', 'hemophilia', 'von_willebrand_disease', 'leukemia',
        'lymphoma', 'multiple_myeloma', 'polycythemia_vera',
        'essential_thrombocythemia', 'myelofibrosis', 'aplastic_anemia',
        'hemolytic_anemia', 'pernicious_anemia', 'anxiety_disorder',
        'panic_disorder', 'phobia', 'ocd', 'ptsd', 'depression',
        'bipolar_disorder', 'schizophrenia', 'adhd', 'autism',
        'eating_disorder', 'anorexia', 'bulimia', 'binge_eating_disorder',
    ]
    
    # Duration encoding
    DURATION_ENCODING = {
        '<1d': 0,
        '1-3d': 1,
        '3-7d': 2,
        '>7d': 3,
    }
    
    def __init__(
        self,
        mlflow_tracking_uri: Optional[str] = None,
        model_name: str = "illness_prediction_model",
        default_version: Optional[str] = None,
    ):
        """
        Initialize the ML Model Service.
        
        Args:
            mlflow_tracking_uri: MLflow tracking server URI. If None, uses MLFLOW_TRACKING_URI env var
            model_name: Name of the model in MLflow registry
            default_version: Default model version to load. If None, loads latest production version
        """
        self.model_name = model_name
        self.default_version = default_version
        
        # Set up MLflow tracking
        if mlflow_tracking_uri:
            mlflow.set_tracking_uri(mlflow_tracking_uri)
        elif os.getenv('MLFLOW_TRACKING_URI'):
            mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI'))
        else:
            # Use local file-based tracking by default
            mlflow.set_tracking_uri("file:./mlruns")
        
        self.client = MlflowClient()
        
        # Model cache: version -> (model, loaded_at)
        self._model_cache: Dict[str, Tuple[any, datetime]] = {}
        
        # Active model version
        self._active_version: Optional[str] = None
        
        logger.info(f"MLModelService initialized with model_name={model_name}")
    
    def load_model(self, version: Optional[str] = None) -> any:
        """
        Load a model from MLflow registry.
        
        Args:
            version: Model version to load. If None, uses default_version or latest production
        
        Returns:
            Loaded model object
        
        Raises:
            ValueError: If model version not found
            Exception: If model loading fails
        """
        # Determine which version to load
        if version is None:
            version = self.default_version or self._get_latest_production_version()
        
        # Check cache first
        if version in self._model_cache:
            model, loaded_at = self._model_cache[version]
            logger.info(f"Using cached model version {version} (loaded at {loaded_at})")
            return model
        
        try:
            # Load model from MLflow
            model_uri = f"models:/{self.model_name}/{version}"
            logger.info(f"Loading model from {model_uri}")
            
            model = mlflow.xgboost.load_model(model_uri)
            
            # Cache the model
            self._model_cache[version] = (model, datetime.utcnow())
            
            logger.info(f"Successfully loaded model version {version}")
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model version {version}: {e}")
            raise
    
    def _get_latest_production_version(self) -> str:
        """
        Get the latest production version of the model.
        
        Returns:
            Version string of the latest production model
        
        Raises:
            ValueError: If no production model found
        """
        try:
            # Get all versions of the model
            versions = self.client.search_model_versions(f"name='{self.model_name}'")
            
            # Filter for production versions
            production_versions = [
                v for v in versions
                if v.current_stage.lower() == 'production'
            ]
            
            if not production_versions:
                # If no production version, get the latest version
                if versions:
                    latest = max(versions, key=lambda v: int(v.version))
                    logger.warning(f"No production version found, using latest version {latest.version}")
                    return latest.version
                else:
                    raise ValueError(f"No versions found for model {self.model_name}")
            
            # Get the latest production version
            latest_production = max(production_versions, key=lambda v: int(v.version))
            return latest_production.version
            
        except Exception as e:
            logger.error(f"Failed to get latest production version: {e}")
            raise ValueError(f"Could not determine model version: {e}")
    
    def get_active_model(self) -> str:
        """
        Get the currently active model version.
        
        Returns:
            Active model version string
        """
        if self._active_version is None:
            self._active_version = self.default_version or self._get_latest_production_version()
        return self._active_version
    
    def set_active_model(self, version: str) -> None:
        """
        Set the active model version.
        
        Args:
            version: Model version to set as active
        
        Raises:
            ValueError: If model version not found
        """
        # Verify the version exists by trying to load it
        self.load_model(version)
        self._active_version = version
        logger.info(f"Active model version set to {version}")
    
    def vectorize_symptoms(self, symptom_vector: SymptomVector) -> np.ndarray:
        """
        Convert a SymptomVector to a feature vector for the ML model.
        
        Feature vector structure:
        - Binary symptom presence indicators (one per known symptom)
        - Symptom severity values (one per known symptom, 0 if not present)
        - Symptom duration encoding (one per known symptom, 0 if not present)
        
        Args:
            symptom_vector: SymptomVector containing user-reported symptoms
        
        Returns:
            numpy array of shape (1, num_features) ready for model inference
        """
        num_symptoms = len(self.KNOWN_SYMPTOMS)
        
        # Initialize feature arrays
        presence = np.zeros(num_symptoms, dtype=np.float32)
        severity = np.zeros(num_symptoms, dtype=np.float32)
        duration = np.zeros(num_symptoms, dtype=np.float32)
        
        # Create symptom name to index mapping
        symptom_to_idx = {symptom: idx for idx, symptom in enumerate(self.KNOWN_SYMPTOMS)}
        
        # Fill in features for reported symptoms
        for symptom_name, symptom_info in symptom_vector.symptoms.items():
            # Normalize symptom name (lowercase, replace spaces with underscores)
            normalized_name = symptom_name.lower().replace(' ', '_')
            
            if normalized_name in symptom_to_idx:
                idx = symptom_to_idx[normalized_name]
                
                # Presence indicator
                presence[idx] = 1.0 if symptom_info.present else 0.0
                
                # Severity (normalized to 0-1 scale)
                if symptom_info.severity is not None:
                    severity[idx] = symptom_info.severity / 10.0
                
                # Duration encoding
                if symptom_info.duration is not None:
                    duration[idx] = self.DURATION_ENCODING.get(symptom_info.duration, 0) / 3.0
        
        # Concatenate all features
        features = np.concatenate([presence, severity, duration])
        
        # Reshape to (1, num_features) for single prediction
        return features.reshape(1, -1)
    
    def predict(
        self,
        symptom_vector: SymptomVector,
        model_version: Optional[str] = None,
        top_k: int = 3,
        confidence_threshold: float = 0.30,
    ) -> List[Tuple[str, float]]:
        """
        Generate illness predictions from a symptom vector.
        
        Args:
            symptom_vector: SymptomVector containing user-reported symptoms
            model_version: Model version to use. If None, uses active version
            top_k: Maximum number of predictions to return (default: 3)
            confidence_threshold: Minimum confidence score (default: 0.30)
        
        Returns:
            List of (illness, confidence_score) tuples, sorted by confidence descending
            Only includes predictions with confidence >= confidence_threshold
            Limited to top_k predictions
        
        Validates: Requirements 3.1, 3.2, 3.3, 3.4
        """
        # Load the model
        if model_version is None:
            model_version = self.get_active_model()
        
        model = self.load_model(model_version)
        
        # Vectorize symptoms
        features = self.vectorize_symptoms(symptom_vector)
        
        # Get predictions (probabilities for each illness)
        try:
            # XGBoost predict_proba returns probabilities for each class
            probabilities = model.predict_proba(features)[0]  # Shape: (num_classes,)
            
            # Create list of (illness, confidence) tuples
            predictions = [
                (illness, float(prob))
                for illness, prob in zip(self.KNOWN_ILLNESSES, probabilities)
            ]
            
            # Filter by confidence threshold (Requirement 3.3)
            predictions = [
                (illness, conf) for illness, conf in predictions
                if conf >= confidence_threshold
            ]
            
            # Sort by confidence descending (Requirement 3.4)
            predictions.sort(key=lambda x: x[1], reverse=True)
            
            # Limit to top_k (Requirement 3.2)
            predictions = predictions[:top_k]
            
            logger.info(
                f"Generated {len(predictions)} predictions for symptom_vector "
                f"with {len(symptom_vector.symptoms)} symptoms using model {model_version}"
            )
            
            return predictions
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise
    
    def clear_cache(self) -> None:
        """Clear the model cache."""
        self._model_cache.clear()
        logger.info("Model cache cleared")
    
    def get_cache_info(self) -> Dict[str, datetime]:
        """
        Get information about cached models.
        
        Returns:
            Dictionary mapping version -> loaded_at timestamp
        """
        return {
            version: loaded_at
            for version, (_, loaded_at) in self._model_cache.items()
        }
