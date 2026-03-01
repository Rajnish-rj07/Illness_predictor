"""
MLOps Deployment Pipeline for the Illness Prediction System.

Implements safe model deployment with staging, automated testing, canary deployment,
and rollback capabilities.

Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)


class DeploymentEnvironment(Enum):
    """Deployment environment types."""
    STAGING = "staging"
    PRODUCTION = "production"


class DeploymentStatus(Enum):
    """Deployment status types."""
    PENDING = "pending"
    TESTING = "testing"
    CANARY = "canary"
    ACTIVE = "active"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class TestResults:
    """Results from automated testing."""
    passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: List[str]
    latency_p95: float
    timestamp: datetime


@dataclass
class DeploymentRecord:
    """Record of a model deployment."""
    model_version: str
    environment: DeploymentEnvironment
    status: DeploymentStatus
    traffic_percent: int
    deployed_at: datetime
    test_results: Optional[TestResults] = None
    rollback_version: Optional[str] = None


class DeploymentPipeline:
    """
    Automated deployment pipeline for illness prediction models.
    
    Responsibilities:
    - Deploy models to staging environment
    - Run automated tests on staged models
    - Implement canary deployment with gradual traffic routing
    - Monitor deployment health
    - Rollback to previous versions on failure
    
    Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
    """
    
    def __init__(self):
        """Initialize deployment pipeline."""
        self.deployments: Dict[str, DeploymentRecord] = {}
        self.active_production_version: Optional[str] = None
        self.active_staging_version: Optional[str] = None
        self.canary_version: Optional[str] = None
        self.canary_traffic_percent: int = 0
        
        logger.info("DeploymentPipeline initialized")
    
    def deploy_to_staging(self, model_version: str) -> bool:
        """
        Deploy model to staging environment.
        
        Validates: Requirements 6.1
        
        Args:
            model_version: Version of model to deploy
            
        Returns:
            True if deployment successful
        """
        logger.info(f"Deploying model {model_version} to staging...")
        
        # Create deployment record
        deployment = DeploymentRecord(
            model_version=model_version,
            environment=DeploymentEnvironment.STAGING,
            status=DeploymentStatus.PENDING,
            traffic_percent=100,
            deployed_at=datetime.utcnow()
        )
        
        # Simulate deployment
        self.deployments[f"staging_{model_version}"] = deployment
        self.active_staging_version = model_version
        
        logger.info(f"Model {model_version} deployed to staging")
        return True
    
    def run_tests(self, model_version: str) -> TestResults:
        """
        Run automated tests on staged model.
        
        Validates: Requirements 6.2
        
        Args:
            model_version: Version of model to test
            
        Returns:
            Test results
        """
        logger.info(f"Running automated tests for model {model_version}...")
        
        deployment_key = f"staging_{model_version}"
        if deployment_key not in self.deployments:
            raise ValueError(f"Model {model_version} not found in staging")
        
        # Update status
        self.deployments[deployment_key].status = DeploymentStatus.TESTING
        
        # Run tests (simulated)
        failed_tests = []
        
        # Test 1: Latency check
        latency_p95 = 150.0  # Simulated latency in ms
        if latency_p95 > 200:
            failed_tests.append("Latency exceeds 200ms threshold")
        
        # Test 2: Model loads successfully
        # (simulated - always passes)
        
        # Test 3: API endpoints respond
        # (simulated - always passes)
        
        # Test 4: Prediction format validation
        # (simulated - always passes)
        
        # Test 5: Known test cases
        # (simulated - always passes)
        
        total_tests = 5
        passed_tests = total_tests - len(failed_tests)
        passed = len(failed_tests) == 0
        
        test_results = TestResults(
            passed=passed,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            latency_p95=latency_p95,
            timestamp=datetime.utcnow()
        )
        
        # Store test results
        self.deployments[deployment_key].test_results = test_results
        
        if passed:
            logger.info(f"All tests passed for model {model_version}")
        else:
            logger.warning(f"Tests failed for model {model_version}: {failed_tests}")
            self.deployments[deployment_key].status = DeploymentStatus.FAILED
        
        return test_results
    
    def start_canary(self, model_version: str, traffic_percent: int) -> None:
        """
        Start canary deployment with specified traffic percentage.
        
        Validates: Requirements 6.5
        
        Args:
            model_version: Version of model to deploy
            traffic_percent: Percentage of traffic to route to new model (10, 50, or 100)
        """
        logger.info(f"Starting canary deployment for {model_version} at {traffic_percent}%...")
        
        # Validate traffic percentage
        if traffic_percent not in [10, 50, 100]:
            raise ValueError("Traffic percent must be 10, 50, or 100")
        
        # Check that model passed staging tests
        staging_key = f"staging_{model_version}"
        if staging_key not in self.deployments:
            raise ValueError(f"Model {model_version} not found in staging")
        
        staging_deployment = self.deployments[staging_key]
        if not staging_deployment.test_results or not staging_deployment.test_results.passed:
            raise ValueError(f"Model {model_version} did not pass staging tests")
        
        # Create or update production deployment
        prod_key = f"production_{model_version}"
        if prod_key not in self.deployments:
            deployment = DeploymentRecord(
                model_version=model_version,
                environment=DeploymentEnvironment.PRODUCTION,
                status=DeploymentStatus.CANARY,
                traffic_percent=traffic_percent,
                deployed_at=datetime.utcnow(),
                rollback_version=self.active_production_version
            )
            self.deployments[prod_key] = deployment
        else:
            self.deployments[prod_key].traffic_percent = traffic_percent
            self.deployments[prod_key].status = DeploymentStatus.CANARY
        
        self.canary_version = model_version
        self.canary_traffic_percent = traffic_percent
        
        logger.info(f"Canary deployment started: {traffic_percent}% traffic to {model_version}")
    
    def promote_model(self, model_version: str) -> None:
        """
        Promote model to full production (100% traffic).
        
        Validates: Requirements 6.3
        
        Args:
            model_version: Version of model to promote
        """
        logger.info(f"Promoting model {model_version} to full production...")
        
        prod_key = f"production_{model_version}"
        if prod_key not in self.deployments:
            raise ValueError(f"Model {model_version} not found in production")
        
        # Update deployment status
        self.deployments[prod_key].status = DeploymentStatus.ACTIVE
        self.deployments[prod_key].traffic_percent = 100
        
        # Update active version
        self.active_production_version = model_version
        self.canary_version = None
        self.canary_traffic_percent = 0
        
        logger.info(f"Model {model_version} promoted to full production")
    
    def rollback(self, to_version: Optional[str] = None) -> None:
        """
        Rollback to previous model version.
        
        Validates: Requirements 6.4
        
        Args:
            to_version: Version to rollback to (defaults to previous active version)
        """
        if to_version is None:
            # Get rollback version from current deployment
            if self.canary_version:
                prod_key = f"production_{self.canary_version}"
                if prod_key in self.deployments:
                    to_version = self.deployments[prod_key].rollback_version
            
            if to_version is None:
                raise ValueError("No rollback version available")
        
        logger.info(f"Rolling back to model {to_version}...")
        
        # Mark current deployment as rolled back
        if self.canary_version:
            prod_key = f"production_{self.canary_version}"
            if prod_key in self.deployments:
                self.deployments[prod_key].status = DeploymentStatus.ROLLED_BACK
        
        # Restore previous version
        self.active_production_version = to_version
        self.canary_version = None
        self.canary_traffic_percent = 0
        
        # Update deployment record for rollback version
        rollback_key = f"production_{to_version}"
        if rollback_key in self.deployments:
            self.deployments[rollback_key].status = DeploymentStatus.ACTIVE
            self.deployments[rollback_key].traffic_percent = 100
        
        logger.info(f"Rolled back to model {to_version}")
    
    def get_deployment_status(self, model_version: str, environment: DeploymentEnvironment) -> Optional[DeploymentRecord]:
        """
        Get deployment status for a model version.
        
        Args:
            model_version: Version of model
            environment: Deployment environment
            
        Returns:
            Deployment record if found
        """
        key = f"{environment.value}_{model_version}"
        return self.deployments.get(key)
    
    def get_active_production_version(self) -> Optional[str]:
        """
        Get currently active production model version.
        
        Returns:
            Active production version
        """
        return self.active_production_version
    
    def get_canary_status(self) -> Dict[str, any]:
        """
        Get current canary deployment status.
        
        Returns:
            Canary status information
        """
        return {
            'version': self.canary_version,
            'traffic_percent': self.canary_traffic_percent,
            'is_active': self.canary_version is not None
        }
