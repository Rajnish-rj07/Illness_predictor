# Pre-Deployment Verification Checklist

This guide helps you verify the Illness Prediction System is working correctly before deployment.

## Quick Start (5 minutes)

### Option 1: Automated Smoke Test (Recommended)

```bash
# 1. Start the application
docker-compose up -d

# 2. Wait for services to be ready (30 seconds)
sleep 30

# 3. Run the smoke test
python scripts/smoke_test.py
```

If all tests pass ✅, your system is ready!

### Option 2: Manual Verification

```bash
# 1. Start the application
docker-compose up -d

# 2. Check health
curl http://localhost:8000/health

# 3. Test a conversation
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"channel": "web", "language": "en"}'
```

---

## Detailed Verification Steps

### 1. Environment Setup ✓

**Check Prerequisites:**
```bash
# Verify Docker is running
docker --version
docker-compose --version

# Verify Python environment
python --version  # Should be 3.9+
pip list | grep -E "fastapi|pytest"
```

**Set Environment Variables:**
```bash
# Copy example environment file
cp .env.example .env

# Edit .env and set required values:
# - DATABASE_URL
# - REDIS_URL
# - OPENAI_API_KEY (or ANTHROPIC_API_KEY)
# - SECRET_KEY
# - TWILIO credentials (if using SMS)
```

### 2. Start Services ✓

```bash
# Start all services
docker-compose up -d

# Verify all containers are running
docker-compose ps

# Expected output:
# - app (FastAPI application)
# - postgres (Database)
# - redis (Session storage)
```

**Check Logs:**
```bash
# View application logs
docker-compose logs -f app

# Look for:
# ✅ "Application startup complete"
# ✅ "Uvicorn running on http://0.0.0.0:8000"
# ❌ No error messages or stack traces
```

### 3. Run Test Suite ✓

```bash
# Run all tests
pytest tests/ -v --tb=short

# Expected results:
# - 553+ tests passing
# - 0-2 tests skipped (MLflow integration)
# - 0-1 tests failing (performance test with rate limiting)
```

**Run Specific Test Categories:**
```bash
# Core functionality
pytest tests/test_data_models.py -v
pytest tests/test_prediction_service.py -v

# API endpoints
pytest tests/test_api_integration.py -v

# End-to-end flows
pytest tests/test_e2e_integration.py -v

# Property-based tests
pytest tests/ -k "property" -v
```

### 4. API Endpoint Verification ✓

**Health Check:**
```bash
curl http://localhost:8000/health

# Expected: {"status": "healthy"}
```

**Create Session:**
```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "web",
    "language": "en"
  }'

# Expected: {"session_id": "...", "message": "..."}
# Save the session_id for next steps
```

**Send Message:**
```bash
SESSION_ID="<your-session-id>"

curl -X POST http://localhost:8000/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d '{
    "content": "I have a headache and fever"
  }'

# Expected: {"response": "...", "session_id": "..."}
```

**Get Session State:**
```bash
curl http://localhost:8000/sessions/$SESSION_ID

# Expected: Full session object with messages and state
```

**Delete Session:**
```bash
curl -X DELETE http://localhost:8000/sessions/$SESSION_ID

# Expected: {"message": "Session deleted successfully"}
```

### 5. Database Connectivity ✓

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d illness_prediction

# Run queries to verify tables exist
\dt

# Expected tables:
# - sessions
# - predictions
# - feedback
# - metrics
# - drift_reports

# Exit
\q
```

### 6. Redis Connectivity ✓

```bash
# Connect to Redis
docker-compose exec redis redis-cli

# Test basic operations
PING
# Expected: PONG

# Check if sessions are being stored
KEYS session:*

# Exit
exit
```

### 7. Conversation Flow Test ✓

Test a complete conversation flow:

```bash
# 1. Create session
SESSION_ID=$(curl -s -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"channel": "web", "language": "en"}' | jq -r '.session_id')

echo "Session ID: $SESSION_ID"

# 2. Send initial symptom
curl -X POST http://localhost:8000/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "I have a severe headache"}' | jq

# 3. Answer follow-up questions
curl -X POST http://localhost:8000/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "Yes, I also have a high fever"}' | jq

# 4. Continue conversation
curl -X POST http://localhost:8000/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "It started 2 days ago"}' | jq

# 5. Get final prediction
curl -X POST http://localhost:8000/sessions/$SESSION_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "No other symptoms"}' | jq

# 6. Verify session state
curl http://localhost:8000/sessions/$SESSION_ID | jq
```

### 8. Multi-Language Test ✓

```bash
# Test Spanish
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"channel": "web", "language": "es"}' | jq

# Test French
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"channel": "web", "language": "fr"}' | jq
```

### 9. Performance Check ✓

```bash
# Run performance tests
pytest tests/test_performance.py -v

# Or use Locust for load testing
locust -f tests/locustfile.py --headless \
  --users 10 --spawn-rate 2 --run-time 1m \
  --host http://localhost:8000
```

**Expected Metrics:**
- P95 latency < 500ms
- P99 latency < 1000ms
- Success rate > 95%
- No memory leaks

### 10. Security Verification ✓

```bash
# Test rate limiting
for i in {1..20}; do
  curl -X POST http://localhost:8000/sessions \
    -H "Content-Type: application/json" \
    -d '{"channel": "web", "language": "en"}'
done

# Expected: Some requests should return 429 (Too Many Requests)

# Test authentication (if enabled)
curl http://localhost:8000/sessions \
  -H "Authorization: Bearer invalid-token"

# Expected: 401 Unauthorized
```

### 11. Monitoring Setup ✓

```bash
# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Access dashboards:
# - Grafana: http://localhost:3000 (admin/admin)
# - Prometheus: http://localhost:9090
# - Alertmanager: http://localhost:9093

# Verify metrics are being collected
curl http://localhost:8000/metrics
```

### 12. Documentation Review ✓

Verify documentation is complete:

- [ ] API documentation: `docs/api/API_GUIDE.md`
- [ ] OpenAPI spec: `docs/api/openapi.yaml`
- [ ] Deployment guide: `docs/operations/DEPLOYMENT_GUIDE.md`
- [ ] Operations runbook: `docs/operations/OPERATIONS_RUNBOOK.md`
- [ ] Incident response: `docs/operations/INCIDENT_RESPONSE_PLAYBOOK.md`

---

## Common Issues and Solutions

### Issue: "Connection refused" when accessing API

**Solution:**
```bash
# Check if containers are running
docker-compose ps

# Restart services
docker-compose restart

# Check logs for errors
docker-compose logs app
```

### Issue: Database connection errors

**Solution:**
```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Recreate database
docker-compose down -v
docker-compose up -d
```

### Issue: Redis connection errors

**Solution:**
```bash
# Verify Redis is running
docker-compose ps redis

# Test Redis connectivity
docker-compose exec redis redis-cli PING

# Restart Redis
docker-compose restart redis
```

### Issue: Tests failing

**Solution:**
```bash
# Install test dependencies
pip install -r requirements.txt

# Clear pytest cache
pytest --cache-clear

# Run tests with verbose output
pytest tests/ -vv --tb=long
```

### Issue: Slow API responses

**Solution:**
```bash
# Check resource usage
docker stats

# Increase container resources in docker-compose.yml
# Check for database query performance
# Review application logs for bottlenecks
```

---

## Final Checklist

Before deploying to production, ensure:

- [ ] All automated tests pass (553+ tests)
- [ ] Smoke test script passes
- [ ] API endpoints respond correctly
- [ ] Database and Redis are accessible
- [ ] Complete conversation flow works
- [ ] Multi-language support works
- [ ] Rate limiting is active
- [ ] Monitoring dashboards show data
- [ ] Documentation is complete
- [ ] Environment variables are set
- [ ] Secrets are properly configured
- [ ] Backup and recovery procedures are documented
- [ ] Incident response plan is in place

---

## Next Steps

Once all checks pass:

1. **Review the deployment guide:** `docs/operations/DEPLOYMENT_GUIDE.md`
2. **Deploy to staging:** Follow staging deployment procedures
3. **Run smoke tests in staging:** Verify everything works in staging environment
4. **Monitor for 24 hours:** Check logs, metrics, and alerts
5. **Deploy to production:** Follow production deployment procedures

---

## Quick Reference

**Start System:**
```bash
docker-compose up -d
```

**Stop System:**
```bash
docker-compose down
```

**View Logs:**
```bash
docker-compose logs -f app
```

**Run Tests:**
```bash
pytest tests/ -v
```

**Run Smoke Test:**
```bash
python scripts/smoke_test.py
```

**Access API:**
```
http://localhost:8000
```

**Access Docs:**
```
http://localhost:8000/docs
```

---

**Last Updated:** 2024
**Version:** 1.0.0
