# Performance Testing Guide

This document describes the performance testing strategy and tools for the Illness Prediction System.

## Overview

The performance testing suite validates that the system meets the following requirements:
- **Load Capacity**: Handle 1000 concurrent users
- **Prediction Latency**: P95 < 500ms, P99 < 1000ms
- **Model Inference**: < 200ms per prediction
- **Session Retrieval**: < 50ms
- **Throughput**: >= 100 requests/second
- **System Stability**: Maintain performance under sustained load
- **Error Rate**: < 1% under normal load

## Testing Tools

### 1. Pytest-based Performance Tests (`test_performance.py`)

Comprehensive performance tests integrated with the existing pytest suite.

**Features:**
- Concurrent user simulation using ThreadPoolExecutor
- Detailed latency measurements (P50, P95, P99)
- Throughput testing
- System stability testing
- Memory leak detection
- Error recovery testing

**Run all performance tests:**
```bash
pytest tests/test_performance.py -v -s
```

**Run specific test classes:**
```bash
# Load performance tests
pytest tests/test_performance.py::TestLoadPerformance -v -s

# Prediction latency tests
pytest tests/test_performance.py::TestPredictionLatency -v -s

# Throughput tests
pytest tests/test_performance.py::TestThroughputRequirements -v -s

# Stability tests
pytest tests/test_performance.py::TestSystemStability -v -s
```

**Run specific tests:**
```bash
# Test 1000 concurrent users
pytest tests/test_performance.py::TestLoadPerformance::test_concurrent_users_load -v -s

# Test sustained load
pytest tests/test_performance.py::TestLoadPerformance::test_sustained_load_stability -v -s

# Test prediction latency
pytest tests/test_performance.py::TestPredictionLatency::test_prediction_latency_p95_p99 -v -s
```

### 2. Locust Load Testing (`locustfile.py`)

Advanced distributed load testing with real-time monitoring and web UI.

**Features:**
- Distributed load testing across multiple machines
- Real-time web UI for monitoring
- Custom load shapes (step load, spike load)
- Multiple user behaviors (web users, webhook users, quick users)
- Detailed statistics and reports

**Install Locust:**
```bash
pip install locust
```

**Run with Web UI:**
```bash
# Start Locust with web interface
locust -f tests/locustfile.py --host=http://localhost:8000

# Open browser to http://localhost:8089
# Configure number of users and spawn rate in the UI
```

**Run Headless (No UI):**
```bash
# Run with 1000 users, spawn rate 50/sec, for 5 minutes
locust -f tests/locustfile.py --host=http://localhost:8000 \
       --users 1000 --spawn-rate 50 --run-time 5m --headless

# Run with 500 users for 10 minutes
locust -f tests/locustfile.py --host=http://localhost:8000 \
       --users 500 --spawn-rate 25 --run-time 10m --headless

# Generate CSV reports
locust -f tests/locustfile.py --host=http://localhost:8000 \
       --users 1000 --spawn-rate 50 --run-time 5m --headless \
       --csv=results/performance_test
```

**Run with Custom Load Shapes:**
```bash
# Step load (gradual ramp-up)
locust -f tests/locustfile.py --host=http://localhost:8000 \
       --shape=StepLoadShape --headless

# Spike load (traffic spikes)
locust -f tests/locustfile.py --host=http://localhost:8000 \
       --shape=SpikeLoadShape --headless
```

**Distributed Load Testing:**
```bash
# On master machine
locust -f tests/locustfile.py --host=http://localhost:8000 --master

# On worker machines (run multiple)
locust -f tests/locustfile.py --host=http://localhost:8000 --worker --master-host=<master-ip>
```

## Test Scenarios

### Scenario 1: Baseline Performance Test
**Objective**: Establish baseline performance metrics

```bash
# Run pytest performance tests
pytest tests/test_performance.py -v -s

# Expected Results:
# - P95 latency < 1.0s
# - P99 latency < 2.0s
# - Throughput >= 100 req/s
# - Error rate < 5%
```

### Scenario 2: Peak Load Test
**Objective**: Verify system handles peak load (1000 concurrent users)

```bash
# Using pytest
pytest tests/test_performance.py::TestLoadPerformance::test_concurrent_users_load -v -s

# Using Locust
locust -f tests/locustfile.py --host=http://localhost:8000 \
       --users 1000 --spawn-rate 50 --run-time 5m --headless

# Expected Results:
# - Success rate >= 95%
# - P95 latency < 1.0s
# - P99 latency < 2.0s
# - Error rate < 5%
```

### Scenario 3: Sustained Load Test
**Objective**: Verify system stability under sustained load

```bash
# Using pytest (30 seconds)
pytest tests/test_performance.py::TestLoadPerformance::test_sustained_load_stability -v -s

# Using Locust (10 minutes)
locust -f tests/locustfile.py --host=http://localhost:8000 \
       --users 200 --spawn-rate 20 --run-time 10m --headless

# Expected Results:
# - No performance degradation over time
# - Consistent latency
# - Error rate < 5%
# - No memory leaks
```

### Scenario 4: Spike Load Test
**Objective**: Verify system handles traffic spikes

```bash
# Using Locust with spike shape
locust -f tests/locustfile.py --host=http://localhost:8000 \
       --shape=SpikeLoadShape --headless

# Expected Results:
# - System recovers from spikes
# - No cascading failures
# - Error rate < 10% during spikes
```

### Scenario 5: Prediction Latency Test
**Objective**: Verify prediction service meets latency requirements

```bash
# Test prediction latency
pytest tests/test_performance.py::TestPredictionLatency::test_prediction_latency_p95_p99 -v -s

# Test model inference latency
pytest tests/test_performance.py::TestPredictionLatency::test_model_inference_latency -v -s

# Expected Results:
# - Prediction P95 < 500ms
# - Prediction P99 < 1000ms
# - Model inference P95 < 200ms
```

### Scenario 6: Multi-Channel Performance
**Objective**: Verify performance across all channels (Web, SMS, WhatsApp)

```bash
# Using Locust with webhook users
locust -f tests/locustfile.py --host=http://localhost:8000 \
       --users 500 --spawn-rate 25 --run-time 5m --headless

# Expected Results:
# - Consistent performance across channels
# - No channel-specific bottlenecks
```

## Performance Metrics

### Key Metrics to Monitor

1. **Latency Metrics**
   - Mean response time
   - P50 (Median)
   - P95 (95th percentile)
   - P99 (99th percentile)
   - Min/Max response time

2. **Throughput Metrics**
   - Requests per second (RPS)
   - Successful requests
   - Failed requests
   - Error rate

3. **System Metrics**
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network I/O

4. **Application Metrics**
   - Session creation rate
   - Message processing rate
   - Prediction generation rate
   - Database query time
   - Cache hit rate

### Performance Thresholds

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| P95 Latency | < 500ms | > 500ms | > 1000ms |
| P99 Latency | < 1000ms | > 1000ms | > 2000ms |
| Throughput | >= 100 req/s | < 100 req/s | < 50 req/s |
| Error Rate | < 1% | > 1% | > 5% |
| CPU Usage | < 70% | > 70% | > 90% |
| Memory Usage | < 80% | > 80% | > 95% |

## Interpreting Results

### Good Performance Indicators
- ✅ P95 latency < 500ms
- ✅ P99 latency < 1000ms
- ✅ Error rate < 1%
- ✅ Throughput >= 100 req/s
- ✅ Consistent performance over time
- ✅ No memory leaks

### Performance Issues
- ⚠️ P95 latency > 500ms but < 1000ms
- ⚠️ Error rate > 1% but < 5%
- ⚠️ Throughput < 100 req/s but > 50 req/s
- ⚠️ Gradual performance degradation

### Critical Issues
- ❌ P95 latency > 1000ms
- ❌ P99 latency > 2000ms
- ❌ Error rate > 5%
- ❌ Throughput < 50 req/s
- ❌ System crashes or hangs
- ❌ Memory leaks

## Troubleshooting Performance Issues

### High Latency

**Possible Causes:**
- Database query performance
- ML model inference time
- Network latency
- Insufficient resources

**Investigation Steps:**
1. Check database query times
2. Profile ML model inference
3. Monitor network latency
4. Check CPU/Memory usage
5. Review application logs

**Solutions:**
- Optimize database queries
- Add database indexes
- Cache frequently accessed data
- Optimize ML model
- Scale horizontally
- Increase resources

### High Error Rate

**Possible Causes:**
- Rate limiting
- Resource exhaustion
- Database connection pool exhaustion
- Application bugs

**Investigation Steps:**
1. Check error logs
2. Monitor resource usage
3. Check database connections
4. Review rate limiting configuration

**Solutions:**
- Increase rate limits
- Increase connection pool size
- Fix application bugs
- Scale resources

### Low Throughput

**Possible Causes:**
- Synchronous processing
- Database bottlenecks
- CPU/Memory constraints
- Network bottlenecks

**Investigation Steps:**
1. Profile application code
2. Check database performance
3. Monitor system resources
4. Analyze network traffic

**Solutions:**
- Implement async processing
- Optimize database queries
- Add caching layer
- Scale horizontally
- Optimize code

## Best Practices

1. **Run Tests Regularly**
   - Run performance tests before each release
   - Run nightly performance regression tests
   - Monitor production performance continuously

2. **Establish Baselines**
   - Record baseline performance metrics
   - Compare new results against baseline
   - Track performance trends over time

3. **Test Realistic Scenarios**
   - Use realistic user behaviors
   - Test with production-like data
   - Simulate real traffic patterns

4. **Monitor System Resources**
   - Track CPU, memory, disk, network
   - Identify resource bottlenecks
   - Plan capacity accordingly

5. **Isolate Performance Tests**
   - Run on dedicated test environment
   - Avoid interference from other processes
   - Use consistent hardware

6. **Document Results**
   - Record all test results
   - Document any issues found
   - Track improvements over time

## Continuous Performance Testing

### CI/CD Integration

Add performance tests to your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
name: Performance Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Run nightly at 2 AM
  workflow_dispatch:  # Allow manual trigger

jobs:
  performance-test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Start application
        run: |
          uvicorn src.api.app:app --host 0.0.0.0 --port 8000 &
          sleep 10
      
      - name: Run performance tests
        run: |
          pytest tests/test_performance.py -v -s
      
      - name: Run Locust tests
        run: |
          locust -f tests/locustfile.py --host=http://localhost:8000 \
                 --users 500 --spawn-rate 25 --run-time 5m --headless \
                 --csv=results/performance
      
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: performance-results
          path: results/
```

## Reporting

### Generate Performance Report

After running tests, generate a comprehensive report:

```bash
# Run tests and save output
pytest tests/test_performance.py -v -s > performance_report.txt

# Run Locust and generate CSV
locust -f tests/locustfile.py --host=http://localhost:8000 \
       --users 1000 --spawn-rate 50 --run-time 5m --headless \
       --csv=results/performance_test \
       --html=results/performance_report.html
```

### Report Contents

A good performance report should include:
1. Test configuration (users, duration, environment)
2. Summary metrics (latency, throughput, error rate)
3. Detailed statistics (percentiles, min/max)
4. Graphs and visualizations
5. Issues identified
6. Recommendations

## Conclusion

Regular performance testing ensures the Illness Prediction System meets its performance requirements and provides a good user experience. Use the tools and scenarios described in this guide to validate system performance before each release and monitor for performance regressions.

For questions or issues, contact the development team.
