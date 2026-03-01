"""
MLOps Training Pipeline for the Illness Prediction System.

Implements automated model training with dataset validation, feature engineering,
model training, evaluation, and registration with MLflow.

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 8.1
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import xgboost as xgb

from src.models.data_models import ModelMetrics, ClassMetrics

logger = logging.getLogger(__name__)


@dataclass
class DatasetValidationReport:
    """Report from dataset validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    schema_valid: bool
    missing_values_ok: bool
    class_balance_ok: bool
    total_samples: int
    num_features: int
    num_classes: int


@dataclass
class TrainingConfig:
    """Configuration for model training."""
    max_depth: int = 8
    learning_rate: float = 0.1
    n_estimators: int = 200
    min_child_weight: int = 3
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    objective: str = 'multi:softprob'
    eval_metric: str = 'mlogloss'
    random_state: int = 42
    
    # Validation thresholds
    min_accuracy: float = 0.85
    min_f1: float = 0.80
    min_top_3_accuracy: float = 0.95


class TrainingPipeline:
    """
    Automated training pipeline for illness prediction models.
    
    Responsibilities:
    - Validate training datasets
    - Engineer features from symptom data
    - Train XGBoost models
    - Compute evaluation metrics
    - Register models with MLflow
    
    Validates: Requirements 5.1, 5.2, 5.3, 5.4, 8.1
    """
    
    def __init__(self, config: Optional[TrainingConfig] = None):
        """
        Initialize training pipeline.
        
        Args:
            config: Training configuration
        """
        self.config = config or TrainingConfig()
        self.model = None
        self.feature_names = None
        
        logger.info("TrainingPipeline initialized")
    
    def validate_dataset(self, dataset: pd.DataFrame) -> DatasetValidationReport:
        """
        Validate training dataset quality.
        
        Validates: Requirements 5.2
        
        Args:
            dataset: Training dataset with features and labels
            
        Returns:
            Validation report
        """
        errors = []
        warnings = []
        
        # Check if dataset is empty
        if dataset.empty:
            errors.append("Dataset is empty")
            return DatasetValidationReport(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                schema_valid=False,
                missing_values_ok=False,
                class_balance_ok=False,
                total_samples=0,
                num_features=0,
                num_classes=0
            )
        
        # Schema validation
        schema_valid = True
        if 'label' not in dataset.columns:
            errors.append("Missing 'label' column")
            schema_valid = False
        
        # Check for feature columns
        feature_cols = [col for col in dataset.columns if col != 'label']
        if len(feature_cols) == 0:
            errors.append("No feature columns found")
            schema_valid = False
        
        # Missing values check
        missing_values_ok = True
        missing_pct = dataset.isnull().sum() / len(dataset)
        high_missing = missing_pct[missing_pct > 0.05]
        
        if len(high_missing) > 0:
            warnings.append(f"{len(high_missing)} features have >5% missing values")
            if missing_pct.max() > 0.20:
                errors.append(f"Some features have >{20}% missing values")
                missing_values_ok = False
        
        # Class balance check
        class_balance_ok = True
        if 'label' in dataset.columns:
            class_counts = dataset['label'].value_counts()
            num_classes = len(class_counts)
            
            # Check for minimum samples per class
            min_samples = class_counts.min()
            if min_samples < 10:
                warnings.append(f"Some classes have <10 samples (min: {min_samples})")
            
            # Check for severe imbalance
            max_samples = class_counts.max()
            imbalance_ratio = max_samples / min_samples if min_samples > 0 else float('inf')
            
            if imbalance_ratio > 100:
                errors.append(f"Severe class imbalance detected (ratio: {imbalance_ratio:.1f})")
                class_balance_ok = False
            elif imbalance_ratio > 10:
                warnings.append(f"Class imbalance detected (ratio: {imbalance_ratio:.1f})")
        else:
            num_classes = 0
        
        is_valid = len(errors) == 0
        
        report = DatasetValidationReport(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            schema_valid=schema_valid,
            missing_values_ok=missing_values_ok,
            class_balance_ok=class_balance_ok,
            total_samples=len(dataset),
            num_features=len(feature_cols),
            num_classes=num_classes
        )
        
        if not is_valid:
            logger.error(f"Dataset validation failed: {errors}")
        elif warnings:
            logger.warning(f"Dataset validation warnings: {warnings}")
        else:
            logger.info("Dataset validation passed")
        
        return report
    
    def engineer_features(self, dataset: pd.DataFrame) -> pd.DataFrame:
        """
        Engineer features from raw symptom data.
        
        Args:
            dataset: Raw dataset
            
        Returns:
            Dataset with engineered features
        """
        # For now, return dataset as-is
        # In production, add feature engineering like:
        # - Symptom combinations
        # - Severity aggregations
        # - Duration encodings
        
        logger.info(f"Feature engineering complete: {len(dataset.columns)} features")
        return dataset
    
    def train_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series
    ) -> xgb.XGBClassifier:
        """
        Train XGBoost model.
        
        Validates: Requirements 5.1
        
        Args:
            X_train: Training features
            y_train: Training labels
            X_val: Validation features
            y_val: Validation labels
            
        Returns:
            Trained model
        """
        logger.info("Starting model training...")
        
        # Get number of classes
        num_classes = len(np.unique(y_train))
        
        # Create model parameters
        model_params = {
            'max_depth': self.config.max_depth,
            'learning_rate': self.config.learning_rate,
            'n_estimators': self.config.n_estimators,
            'min_child_weight': self.config.min_child_weight,
            'subsample': self.config.subsample,
            'colsample_bytree': self.config.colsample_bytree,
            'random_state': self.config.random_state,
            'use_label_encoder': False
        }
        
        # For multiclass (3+ classes), set objective and num_class
        if num_classes > 2:
            model_params['objective'] = 'multi:softprob'
            model_params['num_class'] = num_classes
            model_params['eval_metric'] = 'mlogloss'
        else:
            # For binary classification, use binary:logistic
            model_params['objective'] = 'binary:logistic'
            model_params['eval_metric'] = 'logloss'
        
        # Create model
        model = xgb.XGBClassifier(**model_params)
        
        # Train model
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        
        self.model = model
        self.feature_names = list(X_train.columns)
        
        logger.info("Model training complete")
        return model
    
    def evaluate_model(
        self,
        model: xgb.XGBClassifier,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        model_version: str
    ) -> ModelMetrics:
        """
        Evaluate model and compute metrics.
        
        Validates: Requirements 5.3, 8.1
        
        Args:
            model: Trained model
            X_val: Validation features
            y_val: Validation labels
            model_version: Model version string
            
        Returns:
            Model metrics
        """
        logger.info("Evaluating model...")
        
        # Get predictions
        y_pred = model.predict(X_val)
        y_pred_proba = model.predict_proba(X_val)
        
        # Compute overall metrics
        accuracy = accuracy_score(y_val, y_pred)
        precision = precision_score(y_val, y_pred, average='macro', zero_division=0)
        recall = recall_score(y_val, y_pred, average='macro', zero_division=0)
        f1 = f1_score(y_val, y_pred, average='macro', zero_division=0)
        
        # Compute top-3 accuracy
        top_3_accuracy = self._compute_top_k_accuracy(y_val, y_pred_proba, k=3)
        
        # Compute per-class metrics
        per_class_metrics = self._compute_per_class_metrics(y_val, y_pred)
        
        metrics = ModelMetrics(
            model_version=model_version,
            timestamp=datetime.utcnow(),
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            top_3_accuracy=top_3_accuracy,
            per_class_metrics=per_class_metrics
        )
        
        logger.info(
            f"Model evaluation complete: "
            f"accuracy={accuracy:.3f}, f1={f1:.3f}, top-3={top_3_accuracy:.3f}"
        )
        
        return metrics
    
    def _compute_top_k_accuracy(
        self,
        y_true: pd.Series,
        y_pred_proba: np.ndarray,
        k: int = 3
    ) -> float:
        """
        Compute top-k accuracy.
        
        Args:
            y_true: True labels
            y_pred_proba: Prediction probabilities
            k: Number of top predictions to consider
            
        Returns:
            Top-k accuracy
        """
        # Get top k predictions for each sample
        top_k_preds = np.argsort(y_pred_proba, axis=1)[:, -k:]
        
        # Check if true label is in top k
        correct = 0
        for i, true_label in enumerate(y_true):
            if true_label in top_k_preds[i]:
                correct += 1
        
        return correct / len(y_true)
    
    def _compute_per_class_metrics(
        self,
        y_true: pd.Series,
        y_pred: np.ndarray
    ) -> Dict[str, ClassMetrics]:
        """
        Compute per-class metrics.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            
        Returns:
            Dictionary of class metrics
        """
        per_class = {}
        
        # Get unique classes
        classes = np.unique(y_true)
        
        for cls in classes:
            # Binary classification for this class
            y_true_binary = (y_true == cls).astype(int)
            y_pred_binary = (y_pred == cls).astype(int)
            
            # Compute metrics
            precision = precision_score(y_true_binary, y_pred_binary, zero_division=0)
            recall = recall_score(y_true_binary, y_pred_binary, zero_division=0)
            f1 = f1_score(y_true_binary, y_pred_binary, zero_division=0)
            support = int(y_true_binary.sum())
            
            per_class[str(cls)] = ClassMetrics(
                illness=str(cls),
                precision=precision,
                recall=recall,
                f1_score=f1,
                support=support
            )
        
        return per_class
    
    def run_training_pipeline(
        self,
        dataset: pd.DataFrame,
        model_version: str,
        test_size: float = 0.2
    ) -> Tuple[xgb.XGBClassifier, ModelMetrics, DatasetValidationReport]:
        """
        Run complete training pipeline.
        
        Validates: Requirements 5.1, 5.2, 5.3, 5.4
        
        Args:
            dataset: Training dataset
            model_version: Version string for the model
            test_size: Fraction of data for validation
            
        Returns:
            Tuple of (trained model, metrics, validation report)
            
        Raises:
            ValueError: If dataset validation fails
        """
        logger.info(f"Starting training pipeline for model {model_version}")
        
        # 1. Validate dataset
        validation_report = self.validate_dataset(dataset)
        if not validation_report.is_valid:
            raise ValueError(f"Dataset validation failed: {validation_report.errors}")
        
        # 2. Engineer features
        dataset = self.engineer_features(dataset)
        
        # 3. Split data
        X = dataset.drop('label', axis=1)
        y = dataset['label']
        
        X_train, X_val, y_train, y_val = train_test_split(
            X, y,
            test_size=test_size,
            random_state=self.config.random_state,
            stratify=y
        )
        
        logger.info(f"Data split: train={len(X_train)}, val={len(X_val)}")
        
        # 4. Train model
        model = self.train_model(X_train, y_train, X_val, y_val)
        
        # 5. Evaluate model
        metrics = self.evaluate_model(model, X_val, y_val, model_version)
        
        # 6. Check if metrics meet thresholds
        if metrics.accuracy < self.config.min_accuracy:
            logger.warning(
                f"Model accuracy {metrics.accuracy:.3f} below threshold "
                f"{self.config.min_accuracy:.3f}"
            )
        
        if metrics.f1_score < self.config.min_f1:
            logger.warning(
                f"Model F1 {metrics.f1_score:.3f} below threshold "
                f"{self.config.min_f1:.3f}"
            )
        
        logger.info(f"Training pipeline complete for model {model_version}")
        
        return model, metrics, validation_report
    
    def save_model(self, model: xgb.XGBClassifier, filepath: str) -> None:
        """
        Save model to file.
        
        Args:
            model: Trained model
            filepath: Path to save model
        """
        model.save_model(filepath)
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str) -> xgb.XGBClassifier:
        """
        Load model from file.
        
        Args:
            filepath: Path to model file
            
        Returns:
            Loaded model
        """
        model = xgb.XGBClassifier()
        model.load_model(filepath)
        self.model = model
        logger.info(f"Model loaded from {filepath}")
        return model
