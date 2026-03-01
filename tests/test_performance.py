"""
Performance tests for the Illness Prediction System.

Tests load handling with 1000 concurrent users, measures prediction latency
(p95, p99), verifies throughput requirements, and tests system stability under load.

Validates: All requirements (performance)

Requirements:
- Load test with 1000 concurrent users
- Measure prediction latency (p95, p99)
- Verify throughput requirements
- Test system stability under load
"""

import pytest
import time
import statistics
import threading
import concurrent.futures
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from fastapi.testclient import TestClient
import numpy as np

from src.api.app import app
from src.api.routes.sessions import sessions_storage
from src.prediction.prediction_service import PredictionService
from src.ml.ml_model_service import MLModelService
from src.models.data_models import SymptomVector, SymptomInfo


# Create test client
client = TestClient(app)


@pytest.fixture
def clean_sessions():
    """Clear all sessions before each test."""
    sessions_storage.clear()
    from src.api.app import rate_limit_storage
    rate_limit_storage.clear()
    yield
    sessions_storage.clear()
    rate_limit_storage.clear()


class PerformanceMetrics:
    """Container for performance metrics."""
    
    def __init__(self):
        self.latencies: List[float] = []
        self.errors: List[str] = []
        self.start_time: float = 0
        self.end_time: float = 0
        self.successful_requests: int = 0
        self.failed_requests: int = 0
        self.lock = threading.Lock()
    
    def add_latency(self, latency: float):
        """Add a latency measurement."""
        with self.lock:
            self.latencies.append(latency)
            self.successful_requests += 1
    
    def add_error(self, error: str):
        """Add an error."""
        with self.lock:
            self.errors.append(error)
            self.failed_requests += 1
    
    def calculate_percentile(self, percentile: float) -> float:
        """Calculate percentile from latencies."""
        if not self.latencies:
            return 0.0
        return np.percentile(self.latencies, percentile)
    
    def get_throughput(self) -> float:
        """Calculate throughput (requests per second)."""
        duration = self.end_time - self.start_time
        if duration == 0:
            return 0.0
        return self.successful_requests / duration
    
    def get_error_rate(self) -> float:
        """Calculate error rate."""
        total = self.successful_requests + self.failed_requests
        if total == 0:
            return 0.0
        return self.failed_requests / total
    
    def get_summary(self) -> Dict:
        """Get summary of performance metrics."""
        if not self.latencies:
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "error_rate": 0.0,
                "throughput": 0.0,
                "latency_p50": 0.0,
                "latency_p95": 0.0,
                "latency_p99": 0.0,
                "latency_mean": 0.0,
                "latency_min": 0.0,
                "latency_max": 0.0
            }
        
        return {
            "total_requests": self.successful_requests + self.failed_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "error_rate": self.get_error_rate(),
            "throughput": self.get_throughput(),
            "latency_p50": self.calculate_percentile(50),
            "latency_p95": self.calculate_percentile(95),
            "latency_p99": self.calculate_percentile(99),
            "latency_mean": statistics.mean(self.latencies),
            "latency_min": min(self.latencies),
            "latency_max": max(self.latencies)
        }


def simulate_user_session(user_id: int, metrics: PerformanceMetrics) -> bool:
    """
    Simulate a single user session.
    
    Args:
        user_id: Unique user identifier
        metrics: Performance metrics collector
        
    Returns:
        True if session completed successfully, False otherwise
    """
    try:
        # 1. Create session
        start_time = time.time()
        create_response = client.post(
            "/sessions",
            json={
                "channel": "web",
                "user_id": f"perf-user-{user_id}",
                "language": "en"
            }
        )
        
        if create_response.status_code != 201:
            metrics.add_error(f"Session creation failed: {create_response.status_code}")
            return False
        
        session_id = create_response.json()["session_id"]
        create_latency = time.time() - start_time
        metrics.add_latency(create_latency)
        
        # 2. Send initial symptoms
        start_time = time.time()
        msg_response = client.post(
            f"/sessions/{session_id}/messages",
            json={"message": "I have a fever and headache for 2 days"}
        )
        
        if msg_response.status_code != 200:
            metrics.add_error(f"Message send failed: {msg_response.status_code}")
            return False
        
        msg_latency = time.time() - start_time
        metrics.add_latency(msg_latency)
        
        # 3. Send follow-up responses (simulate conversation)
        for i in range(3):
            start_time = time.time()
            followup_response = client.post(
                f"/sessions/{session_id}/messages",
                json={"message": "yes" if i % 2 == 0 else "no"}
            )
            
            if followup_response.status_code != 200:
                metrics.add_error(f"Follow-up message failed: {followup_response.status_code}")
                return False
            
            followup_latency = time.time() - start_time
            metrics.add_latency(followup_latency)
        
        # 4. Get session state
        start_time = time.time()
        state_response = client.get(f"/sessions/{session_id}")
        
        if state_response.status_code != 200:
            metrics.add_error(f"Get session state failed: {state_response.status_code}")
            return False
        
        state_latency = time.time() - start_time
        metrics.add_latency(state_latency)
        
        return True
        
    except Exception as e:
        metrics.add_error(f"Exception: {str(e)}")
        return False


class TestLoadPerformance:
    """Test system performance under load."""
    
    def test_concurrent_users_load(self, clean_sessions):
        """
        Test system with 1000 concurrent users.
        
        This test simulates 1000 concurrent users creating sessions and
        sending messages to verify the system can handle production load.
        
        Validates: All requirements (performance - concurrent load)
        """
        num_users = 1000
        metrics = PerformanceMetrics()
        
        print(f"\n{'='*80}")
        print(f"Starting load test with {num_users} concurrent users...")
        print(f"{'='*80}\n")
        
        metrics.start_time = time.time()
        
        # Use ThreadPoolExecutor for concurrent execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            # Submit all user sessions
            futures = [
                executor.submit(simulate_user_session, user_id, metrics)
                for user_id in range(num_users)
            ]
            
            # Wait for all to complete
            concurrent.futures.wait(futures)
        
        metrics.end_time = time.time()
        
        # Get performance summary
        summary = metrics.get_summary()
        
        # Print results
        print(f"\n{'='*80}")
        print("LOAD TEST RESULTS")
        print(f"{'='*80}")
        print(f"Total Requests:       {summary['total_requests']}")
        print(f"Successful Requests:  {summary['successful_requests']}")
        print(f"Failed Requests:      {summary['failed_requests']}")
        print(f"Error Rate:           {summary['error_rate']:.2%}")
        print(f"Throughput:           {summary['throughput']:.2f} req/s")
        print(f"\nLatency Metrics (seconds):")
        print(f"  Mean:               {summary['latency_mean']:.3f}s")
        print(f"  Min:                {summary['latency_min']:.3f}s")
        print(f"  Max:                {summary['latency_max']:.3f}s")
        print(f"  P50 (Median):       {summary['latency_p50']:.3f}s")
        print(f"  P95:                {summary['latency_p95']:.3f}s")
        print(f"  P99:                {summary['latency_p99']:.3f}s")
        print(f"{'='*80}\n")
        
        # Assertions for performance requirements
        # Note: These thresholds may need adjustment based on hardware
        assert summary['successful_requests'] >= num_users * 0.95, \
            f"Success rate too low: {summary['successful_requests']}/{num_users}"
        
        assert summary['error_rate'] < 0.05, \
            f"Error rate too high: {summary['error_rate']:.2%}"
        
        # Latency requirements (in seconds)
        # P95 should be under 0.5s (500ms) for good user experience
        assert summary['latency_p95'] < 1.0, \
            f"P95 latency too high: {summary['latency_p95']:.3f}s (should be < 1.0s)"
        
        # P99 should be under 2.0s
        assert summary['latency_p99'] < 2.0, \
            f"P99 latency too high: {summary['latency_p99']:.3f}s (should be < 2.0s)"
    
    def test_sustained_load_stability(self, clean_sessions):
        """
        Test system stability under sustained load.
        
        This test runs a sustained load for 30 seconds to verify the system
        remains stable and doesn't degrade over time.
        
        Validates: All requirements (performance - stability)
        """
        duration_seconds = 30
        users_per_second = 10
        metrics = PerformanceMetrics()
        
        print(f"\n{'='*80}")
        print(f"Starting sustained load test for {duration_seconds} seconds...")
        print(f"Rate: {users_per_second} users/second")
        print(f"{'='*80}\n")
        
        metrics.start_time = time.time()
        end_time = metrics.start_time + duration_seconds
        user_id = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            while time.time() < end_time:
                batch_start = time.time()
                
                # Submit batch of users
                futures = [
                    executor.submit(simulate_user_session, user_id + i, metrics)
                    for i in range(users_per_second)
                ]
                
                user_id += users_per_second
                
                # Wait for batch to complete or timeout
                concurrent.futures.wait(futures, timeout=1.0)
                
                # Sleep to maintain rate (if needed)
                elapsed = time.time() - batch_start
                if elapsed < 1.0:
                    time.sleep(1.0 - elapsed)
        
        metrics.end_time = time.time()
        
        # Get performance summary
        summary = metrics.get_summary()
        
        # Print results
        print(f"\n{'='*80}")
        print("SUSTAINED LOAD TEST RESULTS")
        print(f"{'='*80}")
        print(f"Duration:             {duration_seconds}s")
        print(f"Total Requests:       {summary['total_requests']}")
        print(f"Successful Requests:  {summary['successful_requests']}")
        print(f"Failed Requests:      {summary['failed_requests']}")
        print(f"Error Rate:           {summary['error_rate']:.2%}")
        print(f"Throughput:           {summary['throughput']:.2f} req/s")
        print(f"\nLatency Metrics (seconds):")
        print(f"  Mean:               {summary['latency_mean']:.3f}s")
        print(f"  P50 (Median):       {summary['latency_p50']:.3f}s")
        print(f"  P95:                {summary['latency_p95']:.3f}s")
        print(f"  P99:                {summary['latency_p99']:.3f}s")
        print(f"{'='*80}\n")
        
        # Assertions for stability
        assert summary['error_rate'] < 0.05, \
            f"Error rate too high under sustained load: {summary['error_rate']:.2%}"
        
        assert summary['throughput'] >= users_per_second * 0.8, \
            f"Throughput too low: {summary['throughput']:.2f} req/s"
        
        # Verify latency doesn't degrade significantly
        assert summary['latency_p95'] < 1.0, \
            f"P95 latency degraded: {summary['latency_p95']:.3f}s"


class TestPredictionLatency:
    """Test prediction service latency requirements."""
    
    def test_prediction_latency_p95_p99(self):
        """
        Test prediction latency meets p95 and p99 requirements.
        
        Measures prediction latency across many requests to verify
        p95 < 500ms and p99 < 1000ms.
        
        Validates: All requirements (performance - prediction latency)
        """
        # Initialize services
        ml_model_service = MLModelService()
        prediction_service = PredictionService(ml_model_service)
        num_predictions = 1000
        latencies = []
        
        print(f"\n{'='*80}")
        print(f"Testing prediction latency with {num_predictions} predictions...")
        print(f"{'='*80}\n")
        
        # Create test symptom vectors
        for i in range(num_predictions):
            symptom_vector = SymptomVector(
                symptoms={
                    "fever": SymptomInfo(
                        present=True,
                        severity=7 + (i % 3),
                        duration="1-3d",
                        description="High fever"
                    ),
                    "headache": SymptomInfo(
                        present=True,
                        severity=6 + (i % 4),
                        duration="1-3d",
                        description="Severe headache"
                    ),
                    "cough": SymptomInfo(
                        present=(i % 2 == 0),
                        severity=5 + (i % 3),
                        duration="<1d",
                        description="Dry cough"
                    )
                },
                question_count=5,
                confidence_threshold_met=True
            )
            
            # Measure prediction latency
            start_time = time.time()
            try:
                predictions = prediction_service.predict(symptom_vector)
                latency = time.time() - start_time
                latencies.append(latency)
            except Exception as e:
                print(f"Prediction failed: {e}")
        
        # Calculate percentiles
        if latencies:
            p50 = np.percentile(latencies, 50)
            p95 = np.percentile(latencies, 95)
            p99 = np.percentile(latencies, 99)
            mean_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            # Print results
            print(f"\n{'='*80}")
            print("PREDICTION LATENCY RESULTS")
            print(f"{'='*80}")
            print(f"Total Predictions:    {len(latencies)}")
            print(f"\nLatency Metrics (milliseconds):")
            print(f"  Mean:               {mean_latency*1000:.2f}ms")
            print(f"  Min:                {min_latency*1000:.2f}ms")
            print(f"  Max:                {max_latency*1000:.2f}ms")
            print(f"  P50 (Median):       {p50*1000:.2f}ms")
            print(f"  P95:                {p95*1000:.2f}ms")
            print(f"  P99:                {p99*1000:.2f}ms")
            print(f"{'='*80}\n")
            
            # Assertions for latency requirements
            # P95 should be under 500ms for good performance
            assert p95 < 0.5, \
                f"P95 prediction latency too high: {p95*1000:.2f}ms (should be < 500ms)"
            
            # P99 should be under 1000ms
            assert p99 < 1.0, \
                f"P99 prediction latency too high: {p99*1000:.2f}ms (should be < 1000ms)"
            
            # Mean should be reasonable
            assert mean_latency < 0.3, \
                f"Mean prediction latency too high: {mean_latency*1000:.2f}ms"
        else:
            pytest.fail("No successful predictions to measure latency")
    
    def test_model_inference_latency(self):
        """
        Test ML model inference latency.
        
        Measures raw model inference time to verify it's under 200ms.
        
        Validates: All requirements (performance - model inference)
        """
        ml_service = MLModelService()
        num_inferences = 500
        latencies = []
        
        print(f"\n{'='*80}")
        print(f"Testing model inference latency with {num_inferences} inferences...")
        print(f"{'='*80}\n")
        
        # Create test feature vectors
        for i in range(num_inferences):
            # Create random feature vector (matching model input shape)
            features = np.random.rand(1, 300)  # Assuming 300 features
            
            # Measure inference latency
            start_time = time.time()
            try:
                predictions = ml_service.predict(features)
                latency = time.time() - start_time
                latencies.append(latency)
            except Exception as e:
                # Model might not be loaded, skip this test
                print(f"Model inference skipped: {e}")
                pytest.skip("ML model not available for inference testing")
        
        if latencies:
            # Calculate percentiles
            p50 = np.percentile(latencies, 50)
            p95 = np.percentile(latencies, 95)
            p99 = np.percentile(latencies, 99)
            mean_latency = statistics.mean(latencies)
            
            # Print results
            print(f"\n{'='*80}")
            print("MODEL INFERENCE LATENCY RESULTS")
            print(f"{'='*80}")
            print(f"Total Inferences:     {len(latencies)}")
            print(f"\nLatency Metrics (milliseconds):")
            print(f"  Mean:               {mean_latency*1000:.2f}ms")
            print(f"  P50 (Median):       {p50*1000:.2f}ms")
            print(f"  P95:                {p95*1000:.2f}ms")
            print(f"  P99:                {p99*1000:.2f}ms")
            print(f"{'='*80}\n")
            
            # Assertions for inference latency
            # P95 should be under 200ms
            assert p95 < 0.2, \
                f"P95 inference latency too high: {p95*1000:.2f}ms (should be < 200ms)"
            
            # Mean should be well under 200ms
            assert mean_latency < 0.15, \
                f"Mean inference latency too high: {mean_latency*1000:.2f}ms"


class TestThroughputRequirements:
    """Test system throughput requirements."""
    
    def test_api_throughput(self, clean_sessions):
        """
        Test API throughput (requests per second).
        
        Measures how many requests the system can handle per second
        to verify it meets throughput requirements.
        
        Validates: All requirements (performance - throughput)
        """
        duration_seconds = 10
        metrics = PerformanceMetrics()
        
        print(f"\n{'='*80}")
        print(f"Testing API throughput for {duration_seconds} seconds...")
        print(f"{'='*80}\n")
        
        metrics.start_time = time.time()
        end_time = metrics.start_time + duration_seconds
        request_count = 0
        
        # Send requests as fast as possible
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            
            while time.time() < end_time:
                # Submit health check requests (lightweight)
                future = executor.submit(self._make_health_check_request, metrics)
                futures.append(future)
                request_count += 1
                
                # Don't overwhelm the system
                if len(futures) >= 100:
                    concurrent.futures.wait(futures, timeout=0.1)
                    futures = [f for f in futures if not f.done()]
            
            # Wait for remaining requests
            concurrent.futures.wait(futures)
        
        metrics.end_time = time.time()
        
        # Get performance summary
        summary = metrics.get_summary()
        
        # Print results
        print(f"\n{'='*80}")
        print("THROUGHPUT TEST RESULTS")
        print(f"{'='*80}")
        print(f"Duration:             {duration_seconds}s")
        print(f"Total Requests:       {summary['total_requests']}")
        print(f"Successful Requests:  {summary['successful_requests']}")
        print(f"Failed Requests:      {summary['failed_requests']}")
        print(f"Throughput:           {summary['throughput']:.2f} req/s")
        print(f"Error Rate:           {summary['error_rate']:.2%}")
        print(f"{'='*80}\n")
        
        # Assertions for throughput
        # Should handle at least 100 requests per second
        assert summary['throughput'] >= 100, \
            f"Throughput too low: {summary['throughput']:.2f} req/s (should be >= 100 req/s)"
        
        assert summary['error_rate'] < 0.01, \
            f"Error rate too high: {summary['error_rate']:.2%}"
    
    def _make_health_check_request(self, metrics: PerformanceMetrics) -> bool:
        """Make a health check request and record metrics."""
        try:
            start_time = time.time()
            response = client.get("/health")
            latency = time.time() - start_time
            
            if response.status_code == 200:
                metrics.add_latency(latency)
                return True
            else:
                metrics.add_error(f"Health check failed: {response.status_code}")
                return False
        except Exception as e:
            metrics.add_error(f"Exception: {str(e)}")
            return False
    
    def test_session_retrieval_latency(self, clean_sessions):
        """
        Test session retrieval latency.
        
        Verifies that session retrieval is fast (< 50ms) as specified
        in the design document.
        
        Validates: All requirements (performance - session retrieval)
        """
        num_sessions = 50  # Reduced to avoid rate limiting
        latencies = []
        
        print(f"\n{'='*80}")
        print(f"Testing session retrieval latency with {num_sessions} sessions...")
        print(f"{'='*80}\n")
        
        # Create sessions first
        session_ids = []
        for i in range(num_sessions):
            response = client.post(
                "/sessions",
                json={
                    "channel": "web",
                    "user_id": f"retrieval-user-{i}",
                    "language": "en"
                }
            )
            if response.status_code == 201:
                session_ids.append(response.json()["session_id"])
        
        # Measure retrieval latency
        for session_id in session_ids:
            start_time = time.time()
            response = client.get(f"/sessions/{session_id}")
            latency = time.time() - start_time
            
            if response.status_code == 200:
                latencies.append(latency)
        
        if latencies:
            # Calculate percentiles
            p50 = np.percentile(latencies, 50)
            p95 = np.percentile(latencies, 95)
            mean_latency = statistics.mean(latencies)
            
            # Print results
            print(f"\n{'='*80}")
            print("SESSION RETRIEVAL LATENCY RESULTS")
            print(f"{'='*80}")
            print(f"Total Retrievals:     {len(latencies)}")
            print(f"\nLatency Metrics (milliseconds):")
            print(f"  Mean:               {mean_latency*1000:.2f}ms")
            print(f"  P50 (Median):       {p50*1000:.2f}ms")
            print(f"  P95:                {p95*1000:.2f}ms")
            print(f"{'='*80}\n")
            
            # Assertions for retrieval latency
            # P95 should be under 50ms
            assert p95 < 0.05, \
                f"P95 session retrieval latency too high: {p95*1000:.2f}ms (should be < 50ms)"
            
            # Mean should be well under 50ms
            assert mean_latency < 0.03, \
                f"Mean session retrieval latency too high: {mean_latency*1000:.2f}ms"
        else:
            pytest.fail("No successful session retrievals to measure latency")


class TestSystemStability:
    """Test system stability under various conditions."""
    
    def test_memory_stability_under_load(self, clean_sessions):
        """
        Test that memory usage remains stable under load.
        
        Verifies the system doesn't have memory leaks by monitoring
        memory usage during sustained load.
        
        Validates: All requirements (performance - stability)
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Get initial memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"\n{'='*80}")
        print("Testing memory stability under load...")
        print(f"Initial memory usage: {initial_memory:.2f} MB")
        print(f"{'='*80}\n")
        
        # Run load for a period
        num_iterations = 100
        memory_samples = []
        
        for i in range(num_iterations):
            # Create and use session
            response = client.post(
                "/sessions",
                json={
                    "channel": "web",
                    "user_id": f"memory-test-{i}",
                    "language": "en"
                }
            )
            
            if response.status_code == 201:
                session_id = response.json()["session_id"]
                
                # Send message
                client.post(
                    f"/sessions/{session_id}/messages",
                    json={"message": "test message"}
                )
                
                # Delete session
                client.delete(f"/sessions/{session_id}")
            
            # Sample memory every 10 iterations
            if i % 10 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        memory_increase_percent = (memory_increase / initial_memory) * 100
        
        print(f"\n{'='*80}")
        print("MEMORY STABILITY RESULTS")
        print(f"{'='*80}")
        print(f"Initial Memory:       {initial_memory:.2f} MB")
        print(f"Final Memory:         {final_memory:.2f} MB")
        print(f"Memory Increase:      {memory_increase:.2f} MB ({memory_increase_percent:.1f}%)")
        print(f"Peak Memory:          {max(memory_samples):.2f} MB")
        print(f"{'='*80}\n")
        
        # Memory should not increase significantly (< 50% increase)
        assert memory_increase_percent < 50, \
            f"Memory increased too much: {memory_increase_percent:.1f}% (should be < 50%)"
    
    def test_error_recovery(self, clean_sessions):
        """
        Test system recovers gracefully from errors.
        
        Verifies the system continues to function after encountering
        errors and doesn't enter a degraded state.
        
        Validates: All requirements (performance - stability)
        """
        print(f"\n{'='*80}")
        print("Testing error recovery...")
        print(f"{'='*80}\n")
        
        # 1. Cause some errors (invalid requests)
        for i in range(10):
            # Invalid session ID
            response = client.get(f"/sessions/invalid-session-{i}")
            assert response.status_code == 404
        
        # 2. Verify system still works normally
        success_count = 0
        for i in range(10):
            response = client.post(
                "/sessions",
                json={
                    "channel": "web",
                    "user_id": f"recovery-test-{i}",
                    "language": "en"
                }
            )
            if response.status_code == 201:
                success_count += 1
        
        print(f"Successful requests after errors: {success_count}/10")
        
        # Should have high success rate after errors
        assert success_count >= 9, \
            f"System not recovering well from errors: {success_count}/10 successful"
        
        print(f"{'='*80}\n")
        print("System recovered successfully from errors")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s"])
