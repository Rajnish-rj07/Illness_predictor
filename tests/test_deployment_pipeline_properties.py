"""
Property-based tests for DeploymentPipeline.

Tests universal correctness properties for model deployment using hypothesis.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from src.mlops.deployment_pipeline import (
    DeploymentPipeline,
    DeploymentEnvironment,
    DeploymentStatus
)


# Custom strategies
@st.composite
def model_versions(draw):
    """Generate valid model version strings."""
    major = draw(st.integers(min_value=1, max_value=5))
    minor = draw(st.integers(min_value=0, max_value=10))
    patch = draw(st.integers(min_value=0, max_value=20))
    return f"v{major}.{minor}.{patch}"


class TestProperty45StagingBeforeProduction:
    """
    Property 45: Staging deployment before production
    
    For any model being deployed to production, it should first be deployed
    to staging and pass automated tests.
    
    Validates: Requirements 6.1, 6.2
    """
    
    @given(version=model_versions())
    @settings(max_examples=10, deadline=None)
    def test_production_requires_staging_success(self, version):
        """Test that production deployment requires staging success."""
        pipeline = DeploymentPipeline()
        
        # Try to start canary without staging - should fail
        with pytest.raises(ValueError):
            pipeline.start_canary(version, 10)
        
        # Deploy to staging
        pipeline.deploy_to_staging(version)
        
        # Try to start canary without tests - should fail
        with pytest.raises(ValueError):
            pipeline.start_canary(version, 10)
        
        # Run tests
        test_results = pipeline.run_tests(version)
        
        # Now canary should work
        if test_results.passed:
            pipeline.start_canary(version, 10)
            
            # Verify production deployment exists
            prod_deployment = pipeline.get_deployment_status(version, DeploymentEnvironment.PRODUCTION)
            assert prod_deployment is not None
            assert prod_deployment.status == DeploymentStatus.CANARY
    
    @given(version=model_versions())
    @settings(max_examples=10, deadline=None)
    def test_staging_deployment_always_precedes_production(self, version):
        """Test that staging deployment always happens before production."""
        pipeline = DeploymentPipeline()
        
        # Deploy to staging
        pipeline.deploy_to_staging(version)
        staging_deployment = pipeline.get_deployment_status(version, DeploymentEnvironment.STAGING)
        
        # Run tests
        pipeline.run_tests(version)
        
        # Start canary
        pipeline.start_canary(version, 10)
        prod_deployment = pipeline.get_deployment_status(version, DeploymentEnvironment.PRODUCTION)
        
        # Staging deployment should have been created before production
        assert staging_deployment is not None
        assert prod_deployment is not None
        assert staging_deployment.deployed_at <= prod_deployment.deployed_at
    
    @given(version=model_versions())
    @settings(max_examples=10, deadline=None)
    def test_tests_must_pass_before_production(self, version):
        """Test that tests must pass before production deployment."""
        pipeline = DeploymentPipeline()
        
        # Deploy to staging and run tests
        pipeline.deploy_to_staging(version)
        test_results = pipeline.run_tests(version)
        
        # Get staging deployment
        staging_deployment = pipeline.get_deployment_status(version, DeploymentEnvironment.STAGING)
        
        # Test results should be stored
        assert staging_deployment.test_results is not None
        assert staging_deployment.test_results.passed == test_results.passed
        
        # If tests passed, production deployment should be possible
        if test_results.passed:
            pipeline.start_canary(version, 10)
            prod_deployment = pipeline.get_deployment_status(version, DeploymentEnvironment.PRODUCTION)
            assert prod_deployment is not None


class TestProperty46CanaryDeploymentTrafficRouting:
    """
    Property 46: Canary deployment traffic routing
    
    For any new model deployed to production, traffic should be routed
    gradually: 10% → 50% → 100%, with monitoring at each stage.
    
    Validates: Requirements 6.5
    """
    
    @given(version=model_versions())
    @settings(max_examples=10, deadline=None)
    def test_canary_traffic_increases_gradually(self, version):
        """Test that canary traffic increases in steps: 10% → 50% → 100%."""
        pipeline = DeploymentPipeline()
        
        # Deploy and test
        pipeline.deploy_to_staging(version)
        pipeline.run_tests(version)
        
        # Start at 10%
        pipeline.start_canary(version, 10)
        assert pipeline.get_canary_status()['traffic_percent'] == 10
        
        # Increase to 50%
        pipeline.start_canary(version, 50)
        assert pipeline.get_canary_status()['traffic_percent'] == 50
        
        # Promote to 100%
        pipeline.promote_model(version)
        prod_deployment = pipeline.get_deployment_status(version, DeploymentEnvironment.PRODUCTION)
        assert prod_deployment.traffic_percent == 100
    
    @given(version=model_versions())
    @settings(max_examples=10, deadline=None)
    def test_only_valid_traffic_percentages_allowed(self, version):
        """Test that only 10%, 50%, or 100% traffic is allowed."""
        pipeline = DeploymentPipeline()
        
        # Deploy and test
        pipeline.deploy_to_staging(version)
        pipeline.run_tests(version)
        
        # Valid percentages should work
        for percent in [10, 50, 100]:
            pipeline.start_canary(version, percent)
            assert pipeline.get_canary_status()['traffic_percent'] == percent
    
    @given(version=model_versions(), invalid_percent=st.integers(min_value=1, max_value=100))
    @settings(max_examples=10, deadline=None)
    def test_invalid_traffic_percentages_rejected(self, version, invalid_percent):
        """Test that invalid traffic percentages are rejected."""
        assume(invalid_percent not in [10, 50, 100])
        
        pipeline = DeploymentPipeline()
        
        # Deploy and test
        pipeline.deploy_to_staging(version)
        pipeline.run_tests(version)
        
        # Invalid percentage should fail
        with pytest.raises(ValueError, match="Traffic percent must be"):
            pipeline.start_canary(version, invalid_percent)
    
    @given(version=model_versions())
    @settings(max_examples=10, deadline=None)
    def test_canary_status_tracked_correctly(self, version):
        """Test that canary status is tracked correctly."""
        pipeline = DeploymentPipeline()
        
        # Initially no canary
        assert pipeline.get_canary_status()['is_active'] is False
        
        # Deploy and test
        pipeline.deploy_to_staging(version)
        pipeline.run_tests(version)
        
        # Start canary
        pipeline.start_canary(version, 10)
        canary_status = pipeline.get_canary_status()
        assert canary_status['is_active'] is True
        assert canary_status['version'] == version
        assert canary_status['traffic_percent'] == 10
        
        # Promote to full production
        pipeline.promote_model(version)
        assert pipeline.get_canary_status()['is_active'] is False


class TestProperty47RollbackCapability:
    """
    Property 47: Rollback capability
    
    For any deployment, the system should be able to rollback to the
    previous version if issues occur.
    
    Validates: Requirements 6.4
    """
    
    @given(v1=model_versions(), v2=model_versions())
    @settings(max_examples=10, deadline=None)
    def test_rollback_restores_previous_version(self, v1, v2):
        """Test that rollback restores the previous active version."""
        assume(v1 != v2)
        
        pipeline = DeploymentPipeline()
        
        # Deploy v1
        pipeline.deploy_to_staging(v1)
        pipeline.run_tests(v1)
        pipeline.start_canary(v1, 10)
        pipeline.promote_model(v1)
        
        assert pipeline.get_active_production_version() == v1
        
        # Deploy v2
        pipeline.deploy_to_staging(v2)
        pipeline.run_tests(v2)
        pipeline.start_canary(v2, 10)
        
        # Rollback
        pipeline.rollback()
        
        # Should be back to v1
        assert pipeline.get_active_production_version() == v1
    
    @given(v1=model_versions(), v2=model_versions())
    @settings(max_examples=10, deadline=None)
    def test_rollback_clears_canary(self, v1, v2):
        """Test that rollback clears canary deployment."""
        assume(v1 != v2)
        
        pipeline = DeploymentPipeline()
        
        # Deploy v1
        pipeline.deploy_to_staging(v1)
        pipeline.run_tests(v1)
        pipeline.start_canary(v1, 10)
        pipeline.promote_model(v1)
        
        # Deploy v2 as canary
        pipeline.deploy_to_staging(v2)
        pipeline.run_tests(v2)
        pipeline.start_canary(v2, 10)
        
        assert pipeline.get_canary_status()['is_active'] is True
        
        # Rollback
        pipeline.rollback()
        
        # Canary should be cleared
        assert pipeline.get_canary_status()['is_active'] is False
    
    @given(v1=model_versions(), v2=model_versions())
    @settings(max_examples=10, deadline=None)
    def test_rollback_marks_deployment_as_rolled_back(self, v1, v2):
        """Test that rollback marks the deployment as rolled back."""
        assume(v1 != v2)
        
        pipeline = DeploymentPipeline()
        
        # Deploy v1
        pipeline.deploy_to_staging(v1)
        pipeline.run_tests(v1)
        pipeline.start_canary(v1, 10)
        pipeline.promote_model(v1)
        
        # Deploy v2
        pipeline.deploy_to_staging(v2)
        pipeline.run_tests(v2)
        pipeline.start_canary(v2, 10)
        
        # Rollback
        pipeline.rollback()
        
        # v2 should be marked as rolled back
        v2_deployment = pipeline.get_deployment_status(v2, DeploymentEnvironment.PRODUCTION)
        assert v2_deployment.status == DeploymentStatus.ROLLED_BACK
    
    @given(versions=st.lists(model_versions(), min_size=3, max_size=5, unique=True))
    @settings(max_examples=5, deadline=None)
    def test_rollback_to_specific_version(self, versions):
        """Test rollback to a specific version."""
        pipeline = DeploymentPipeline()
        
        # Deploy all versions
        for version in versions:
            pipeline.deploy_to_staging(version)
            pipeline.run_tests(version)
            pipeline.start_canary(version, 10)
            pipeline.promote_model(version)
        
        # Rollback to first version
        target_version = versions[0]
        pipeline.rollback(target_version)
        
        assert pipeline.get_active_production_version() == target_version


class TestDeploymentPipelineInvariants:
    """Test invariants that should always hold for deployment pipeline."""
    
    @given(version=model_versions())
    @settings(max_examples=10, deadline=None)
    def test_active_production_version_is_always_valid(self, version):
        """Test that active production version is always valid."""
        pipeline = DeploymentPipeline()
        
        # Initially no active version
        assert pipeline.get_active_production_version() is None
        
        # Deploy and promote
        pipeline.deploy_to_staging(version)
        pipeline.run_tests(version)
        pipeline.start_canary(version, 10)
        pipeline.promote_model(version)
        
        # Active version should be set
        active_version = pipeline.get_active_production_version()
        assert active_version is not None
        assert active_version == version
        
        # Active version should have a deployment record
        deployment = pipeline.get_deployment_status(active_version, DeploymentEnvironment.PRODUCTION)
        assert deployment is not None
        assert deployment.status == DeploymentStatus.ACTIVE
    
    @given(version=model_versions())
    @settings(max_examples=10, deadline=None)
    def test_deployment_timestamps_are_monotonic(self, version):
        """Test that deployment timestamps increase monotonically."""
        pipeline = DeploymentPipeline()
        
        # Deploy to staging
        pipeline.deploy_to_staging(version)
        staging_deployment = pipeline.get_deployment_status(version, DeploymentEnvironment.STAGING)
        staging_time = staging_deployment.deployed_at
        
        # Run tests (updates deployment)
        pipeline.run_tests(version)
        
        # Deploy to production
        pipeline.start_canary(version, 10)
        prod_deployment = pipeline.get_deployment_status(version, DeploymentEnvironment.PRODUCTION)
        prod_time = prod_deployment.deployed_at
        
        # Production deployment should be after staging
        assert prod_time >= staging_time
    
    @given(v1=model_versions(), v2=model_versions())
    @settings(max_examples=10, deadline=None)
    def test_only_one_canary_at_a_time(self, v1, v2):
        """Test that only one canary deployment can be active at a time."""
        assume(v1 != v2)
        
        pipeline = DeploymentPipeline()
        
        # Deploy v1 as canary
        pipeline.deploy_to_staging(v1)
        pipeline.run_tests(v1)
        pipeline.start_canary(v1, 10)
        
        assert pipeline.get_canary_status()['version'] == v1
        
        # Deploy v2 as canary
        pipeline.deploy_to_staging(v2)
        pipeline.run_tests(v2)
        pipeline.start_canary(v2, 10)
        
        # Only v2 should be canary now
        canary_status = pipeline.get_canary_status()
        assert canary_status['version'] == v2
        assert canary_status['version'] != v1
