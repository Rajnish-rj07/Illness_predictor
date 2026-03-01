"""
Locust load testing script for the Illness Prediction System.

This script provides advanced load testing capabilities using Locust,
allowing for distributed load testing and real-time monitoring.

Usage:
    # Run with web UI
    locust -f tests/locustfile.py --host=http://localhost:8000

    # Run headless with 1000 users
    locust -f tests/locustfile.py --host=http://localhost:8000 \
           --users 1000 --spawn-rate 50 --run-time 5m --headless

    # Run with specific user behavior
    locust -f tests/locustfile.py --host=http://localhost:8000 \
           --users 500 --spawn-rate 25 --run-time 10m

Requirements:
- Install locust: pip install locust
"""

from locust import HttpUser, task, between, events
import random
import json
from datetime import datetime


class IllnessPredictionUser(HttpUser):
    """
    Simulates a user interacting with the Illness Prediction System.
    
    This user creates a session, reports symptoms, answers questions,
    and receives predictions.
    """
    
    # Wait between 1-3 seconds between tasks (simulating user think time)
    wait_time = between(1, 3)
    
    def on_start(self):
        """Called when a user starts. Initialize user state."""
        self.session_id = None
        self.user_id = f"locust-user-{random.randint(1, 1000000)}"
        self.message_count = 0
        self.max_messages = random.randint(3, 10)
        
        # Create session
        self.create_session()
    
    def create_session(self):
        """Create a new session for the user."""
        languages = ['en', 'es', 'fr', 'hi', 'zh']
        channels = ['web', 'sms', 'whatsapp']
        
        response = self.client.post(
            "/sessions",
            json={
                "channel": random.choice(channels),
                "user_id": self.user_id,
                "language": random.choice(languages)
            },
            name="/sessions [CREATE]"
        )
        
        if response.status_code == 201:
            self.session_id = response.json()["session_id"]
        else:
            print(f"Failed to create session: {response.status_code}")
    
    @task(5)
    def send_symptom_message(self):
        """Send a symptom message (most common task)."""
        if not self.session_id:
            self.create_session()
            return
        
        if self.message_count >= self.max_messages:
            # Start a new session
            self.create_session()
            self.message_count = 0
            return
        
        # Sample symptom messages
        messages = [
            "I have a fever and headache",
            "I've been coughing for 3 days",
            "I feel nauseous and dizzy",
            "I have a sore throat and body aches",
            "yes",
            "no",
            "The pain is severe",
            "It started yesterday",
            "I also have fatigue",
            "The fever is high, around 102F"
        ]
        
        response = self.client.post(
            f"/sessions/{self.session_id}/messages",
            json={"message": random.choice(messages)},
            name="/sessions/{id}/messages [SEND]"
        )
        
        if response.status_code == 200:
            self.message_count += 1
        elif response.status_code == 404:
            # Session not found, create new one
            self.create_session()
            self.message_count = 0
    
    @task(2)
    def get_session_state(self):
        """Get current session state."""
        if not self.session_id:
            return
        
        self.client.get(
            f"/sessions/{self.session_id}",
            name="/sessions/{id} [GET]"
        )
    
    @task(1)
    def check_health(self):
        """Check API health (lightweight request)."""
        self.client.get(
            "/health",
            name="/health [GET]"
        )
    
    def on_stop(self):
        """Called when a user stops. Cleanup."""
        if self.session_id:
            # Delete session (data privacy)
            self.client.delete(
                f"/sessions/{self.session_id}",
                name="/sessions/{id} [DELETE]"
            )


class WebhookUser(HttpUser):
    """
    Simulates users interacting via SMS/WhatsApp webhooks.
    
    This user sends messages through webhook endpoints to test
    multi-channel performance.
    """
    
    wait_time = between(2, 5)
    
    def on_start(self):
        """Initialize webhook user."""
        self.phone_number = f"+1555{random.randint(1000000, 9999999)}"
        self.message_count = 0
    
    @task(3)
    def send_sms_message(self):
        """Send SMS message via webhook."""
        messages = [
            "I have a fever",
            "I've been coughing",
            "yes",
            "no",
            "for 2 days"
        ]
        
        self.client.post(
            "/webhooks/sms",
            data={
                "From": self.phone_number,
                "Body": random.choice(messages)
            },
            name="/webhooks/sms [POST]"
        )
        
        self.message_count += 1
    
    @task(2)
    def send_whatsapp_message(self):
        """Send WhatsApp message via webhook."""
        messages = [
            "I have a headache",
            "I feel sick",
            "yes",
            "no",
            "since yesterday"
        ]
        
        self.client.post(
            "/webhooks/whatsapp",
            json={
                "from": f"whatsapp:{self.phone_number}",
                "body": random.choice(messages)
            },
            name="/webhooks/whatsapp [POST]"
        )
        
        self.message_count += 1


class QuickUser(HttpUser):
    """
    Simulates users who quickly check health and leave.
    
    This represents users who just want to verify the service is available.
    """
    
    wait_time = between(0.5, 1.5)
    
    @task
    def quick_health_check(self):
        """Quick health check."""
        self.client.get("/health")


# Event handlers for custom metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts."""
    print("\n" + "="*80)
    print("LOCUST LOAD TEST STARTING")
    print("="*80)
    print(f"Start time: {datetime.now().isoformat()}")
    print(f"Host: {environment.host}")
    print("="*80 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops."""
    print("\n" + "="*80)
    print("LOCUST LOAD TEST COMPLETED")
    print("="*80)
    print(f"End time: {datetime.now().isoformat()}")
    
    # Print summary statistics
    stats = environment.stats
    print(f"\nTotal requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Min response time: {stats.total.min_response_time:.2f}ms")
    print(f"Max response time: {stats.total.max_response_time:.2f}ms")
    print(f"Median response time: {stats.total.median_response_time:.2f}ms")
    print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"99th percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"Requests per second: {stats.total.total_rps:.2f}")
    print(f"Failure rate: {(stats.total.num_failures / stats.total.num_requests * 100) if stats.total.num_requests > 0 else 0:.2f}%")
    print("="*80 + "\n")


# Custom shape for ramping load
from locust import LoadTestShape

class StepLoadShape(LoadTestShape):
    """
    A step load shape that gradually increases load.
    
    This simulates realistic traffic patterns with gradual ramp-up.
    """
    
    step_time = 60  # seconds per step
    step_load = 100  # users to add per step
    spawn_rate = 10  # users per second
    time_limit = 600  # total test duration in seconds
    
    def tick(self):
        """
        Returns a tuple of (user_count, spawn_rate) at each tick.
        """
        run_time = self.get_run_time()
        
        if run_time > self.time_limit:
            return None
        
        current_step = run_time // self.step_time
        user_count = (current_step + 1) * self.step_load
        
        return (user_count, self.spawn_rate)


class SpikeLoadShape(LoadTestShape):
    """
    A spike load shape that simulates traffic spikes.
    
    This tests how the system handles sudden increases in load.
    """
    
    time_limit = 300  # 5 minutes
    
    def tick(self):
        """
        Returns a tuple of (user_count, spawn_rate) at each tick.
        """
        run_time = self.get_run_time()
        
        if run_time > self.time_limit:
            return None
        
        # Create spikes every 60 seconds
        if (run_time // 60) % 2 == 0:
            # Spike: 500 users
            return (500, 50)
        else:
            # Normal: 100 users
            return (100, 10)


# To use a custom shape, run:
# locust -f tests/locustfile.py --host=http://localhost:8000 --shape=StepLoadShape
# or
# locust -f tests/locustfile.py --host=http://localhost:8000 --shape=SpikeLoadShape
