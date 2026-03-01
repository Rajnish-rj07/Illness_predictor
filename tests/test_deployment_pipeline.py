"""
Unit tests for DeploymentPipeline.

Tests deployment workflow, staging, canary deployment, and rollback functionality.
"""

import pytest
from datetime import datetime
from src.mlops.deployment_pipeline import (
    DeploymentPipeline,
    DeploymentEnvironment,
    DeploymentStatus,
    TestResults
)


class TestStagingDeployment:
    """Tests for staging deployment functionality."""
    
    def test_deploy_to_staging_success(self):
        """Test successful deployment to staging."""
        pipeline = DeploymentPipeline()
        
        result = pipeline.deploy_to_staging("v1.0.0")
        
        assert result is True
        assert pipeline.active_staging_version == "v1.0.0"
        
        # Check deployment record
        deployment = pipeline.get_deployment_status("v1.0.0", DeploymentEnvironment.STAGING)
        assert deployment is not None
        assert deployment.model_version == "v1.0.0"
        assert deployment.environment == DeploymentEnvironment.STAGING
        assert deployment.status == DeploymentStatus.PENDING
        assert deployment.traffic_percent == 100
    
    def test_deploy_multiple_versions_to_staging(self):
        """Test deploying multiple versions to staging."""
        pipeline = DeploymentPipeline()
        
        pipeline.deploy_to_staging("v1.0.0")
        pipeline.deploy_to_staging("v1.1.0")
        
        # Latest version should be active
        assert pipeline.active_staging_version == "v1.1.0"
        
        # Both deployments should exist
        assert pipeline.get_deployment_status("v1.0.0", DeploymentEnvironment.STAGING) is not None
        assert pipeline.get_deployment_status("v1.1.0", DeploymentEnvironment.STAGING) is not None


class TestAutomatedTesting:
    """Tests for automated testing functionality."""
    
    def test_run_tests_on_staged_model(self):
        """Test running automated tests on staged model."""
        pipeline = DeploymentPipeline()
        pipeline.deploy_to_staging("v1.0.0")
        
        test_results = pipeline.run_tests("v1.0.0")
        
        assert isinstance(test_results, TestResults)
        assert test_results.total_tests == 5
        assert test_results.passed is True
        assert test_results.passed_tests == 5
        assert len(test_results.failed_tests) == 0
        assert test_results.latency_p95 < 200  # Should meet latency requirement
    
    def test_run_tests_on_non_staged_model(self):
        """Test running tests on model not in staging."""
        pipeline = DeploymentPipeline()
        
        with pytest.raises(ValueError, match="not found in staging"):
            pipeline.run_tests("v1.0.0")
    
    def test_test_results_stored_in_deployment(self):
        """Test that test results are stored in deployment record."""
        pipeline = DeploymentPipeline()
        pipeline.deploy_to_staging("v1.0.0")
        
        test_results = pipeline.run_tests("v1.0.0")
        
        deployment = pipeline.get_deployment_status("v1.0.0", DeploymentEnvironment.STAGING)
        assert deployment.test_results is not None
        assert deployment.test_results.passed == test_results.passed


class TestCanaryDeployment:
    """Tests for canary deployment functionality."""
    
    def test_start_canary_at_10_percent(self):
        """Test starting canary deployment at 10% traffic."""
        pipeline = DeploymentPipeline()
        pipeline.deploy_to_staging("v1.0.0")
        pipeline.run_tests("v1.0.0")
        
        pipeline.start_canary("v1.0.0", 10)
        
        canary_status = pipeline.get_canary_status()
        assert canary_status['version'] == "v1.0.0"
        assert canary_status['traffic_percent'] == 10
        assert canary_status['is_active'] is True
        
        # Check production deployment
        deployment = pipeline.get_deployment_status("v1.0.0", DeploymentEnvironment.PRODUCTION)
        assert deployment is not None
        assert deployment.status == DeploymentStatus.CANARY
        assert deployment.traffic_percent == 10
    
    def test_increase_canary_traffic_to_50_percent(self):
        """Test increasing canary traffic to 50%."""
        pipeline = DeploymentPipeline()
        pipeline.deploy_to_staging("v1.0.0")
        pipeline.run_tests("v1.0.0")
        
        pipeline.start_canary("v1.0.0", 10)
        pipeline.start_canary("v1.0.0", 50)
        
        canary_status = pipeline.get_canary_status()
        assert canary_status['traffic_percent'] == 50
        
        deployment = pipeline.get_deployment_status("v1.0.0", DeploymentEnvironment.PRODUCTION)
        assert deployment.traffic_percent == 50
    
    def test_canary_without_staging_tests_fails(self):
        """Test that canary deployment fails without passing staging tests."""
        pipeline = DeploymentPipeline()
        pipeline.deploy_to_staging("v1.0.0")
        
        # Try to start canary without running tests
        with pytest.raises(ValueError, match="did not pass staging tests"):
            pipeline.start_canary("v1.0.0", 10)
    
    def test_canary_with_invalid_traffic_percent(self):
        """Test that invalid traffic percentages are rejected."""
        pipeline = DeploymentPipeline()
        pipeline.deploy_to_staging("v1.0.0")
        pipeline.run_tests("v1.0.0")
        
        with pytest.raises(ValueError, match="Traffic percent must be"):
            pipeline.start_canary("v1.0.0", 25)
    
    def test_canary_stores_rollback_version(self):
        """Test that canary deployment stores rollback version."""
        pipeline = DeploymentPipeline()
        
        # Deploy and promote first version
        pipeline.deploy_to_staging("v1.0.0")
        pipeline.run_tests("v1.0.0")
        pipeline.start_canary("v1.0.0", 10)
        pipeline.promote_model("v1.0.0")
        
        # Deploy new version
        pipeline.deploy_to_staging("v1.1.0")
        pipeline.run_tests("v1.1.0")
        pipeline.start_canary("v1.1.0", 10)
        
        # Check rollback version is stored
        deployment = pipeline.get_deployment_status("v1.1.0", DeploymentEnvironment.PRODUCTION)
        assert deployment.rollback_version == "v1.0.0"


class TestModelPromotion:
    """Tests for model promotion functionality."""
    
    def test_promote_model_to_full_production(self):
        """Test promoting model to 100% traffic."""
        pipeline = DeploymentPipeline()
        pipeline.deploy_to_staging("v1.0.0")
        pipeline.run_tests("v1.0.0")
        pipeline.start_canary("v1.0.0", 10)
        
        pipeline.promote_model("v1.0.0")
        
        assert pipeline.get_active_production_version() == "v1.0.0"
        
        deployment = pipeline.get_deployment_status("v1.0.0", DeploymentEnvironment.PRODUCTION)
        assert deployment.status == DeploymentStatus.ACTIVE
        assert deployment.traffic_percent == 100
        
        # Canary should be cleared
        canary_status = pipeline.get_canary_status()
        assert canary_status['is_active'] is False
    
    def test_promote_non_deployed_model_fails(self):
        """Test that promoting non-deployed model fails."""
        pipeline = DeploymentPipeline()
        
        with pytest.raises(ValueError, match="not found in production"):
            pipeline.promote_model("v1.0.0")


class TestRollback:
    """Tests for rollback functionality."""
    
    def test_rollback_to_previous_version(self):
        """Test rolling back to previous version."""
        pipeline = DeploymentPipeline()
        
        # Deploy and promote first version
        pipeline.deploy_to_staging("v1.0.0")
        pipeline.run_tests("v1.0.0")
        pipeline.start_canary("v1.0.0", 10)
        pipeline.promote_model("v1.0.0")
        
        # Deploy new version
        pipeline.deploy_to_staging("v1.1.0")
        pipeline.run_tests("v1.1.0")
        pipeline.start_canary("v1.1.0", 10)
        
        # Rollback
        pipeline.rollback()
        
        assert pipeline.get_active_production_version() == "v1.0.0"
        
        # New version should be marked as rolled back
        deployment = pipeline.get_deployment_status("v1.1.0", DeploymentEnvironment.PRODUCTION)
        assert deployment.status == DeploymentStatus.ROLLED_BACK
        
        # Canary should be cleared
        canary_status = pipeline.get_canary_status()
        assert canary_status['is_active'] is False
    
    def test_rollback_to_specific_version(self):
        """Test rolling back to specific version."""
        pipeline = DeploymentPipeline()
        
        # Deploy multiple versions
        for version in ["v1.0.0", "v1.1.0", "v1.2.0"]:
            pipeline.deploy_to_staging(version)
            pipeline.run_tests(version)
            pipeline.start_canary(version, 10)
            pipeline.promote_model(version)
        
        # Rollback to v1.0.0
        pipeline.rollback("v1.0.0")
        
        assert pipeline.get_active_production_version() == "v1.0.0"
    
    def test_rollback_without_previous_version_fails(self):
        """Test that rollback fails without previous version."""
        pipeline = DeploymentPipeline()
        
        with pytest.raises(ValueError, match="No rollback version available"):
            pipeline.rollback()


class TestDeploymentWorkflow:
    """Tests for complete deployment workflow."""
    
    def test_full_deployment_workflow(self):
        """Test complete deployment workflow from staging to production."""
        pipeline = DeploymentPipeline()
        
        # Stage 1: Deploy to staging
        assert pipeline.deploy_to_staging("v1.0.0") is True
        
        # Stage 2: Run tests
        test_results = pipeline.run_tests("v1.0.0")
        assert test_results.passed is True
        
        # Stage 3: Start canary at 10%
        pipeline.start_canary("v1.0.0", 10)
        assert pipeline.get_canary_status()['traffic_percent'] == 10
        
        # Stage 4: Increase to 50%
        pipeline.start_canary("v1.0.0", 50)
        assert pipeline.get_canary_status()['traffic_percent'] == 50
        
        # Stage 5: Promote to 100%
        pipeline.promote_model("v1.0.0")
        assert pipeline.get_active_production_version() == "v1.0.0"
        assert pipeline.get_canary_status()['is_active'] is False
    
    def test_deployment_with_rollback(self):
        """Test deployment workflow with rollback."""
        pipeline = DeploymentPipeline()
        
        # Deploy v1.0.0
        pipeline.deploy_to_staging("v1.0.0")
        pipeline.run_tests("v1.0.0")
        pipeline.start_canary("v1.0.0", 10)
        pipeline.promote_model("v1.0.0")
        
        # Deploy v1.1.0
        pipeline.deploy_to_staging("v1.1.0")
        pipeline.run_tests("v1.1.0")
        pipeline.start_canary("v1.1.0", 10)
        
        # Rollback due to issues
        pipeline.rollback()
        
        # Should be back to v1.0.0
        assert pipeline.get_active_production_version() == "v1.0.0"
