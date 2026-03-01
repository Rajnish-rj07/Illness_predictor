# Illness Prediction System - Operations Runbook

**Version**: 1.0.0  
**Last Updated**: 2024  
**Owner**: Operations Team  
**On-Call**: oncall@illness-prediction.com

## Table of Contents

1. [Overview](#overview)
2. [Deployment Procedures](#deployment-procedures)
3. [Rollback Procedures](#rollback-procedures)
4. [Monitoring and Alerting](#monitoring-and-alerting)
5. [Incident Response](#incident-response)
6. [Common Issues and Resolutions](#common-issues-and-resolutions)
7. [Emergency Contacts](#emergency-contacts)

---

## Overview

This runbook provides operational procedures for deploying, monitoring, and maintaining the Illness Prediction System in production. It covers standard operating procedures (SOPs), troubleshooting guides, and incident response protocols.

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Load Balancer / Ingress                  │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐     ┌────▼────┐    ┌────▼────┐
    │  App    │     │  App    │    │  App    │
    │  Pod 1  │     │  Pod 2  │    │  Pod 3  │
    └────┬────┘     └────┬────┘    └────┬────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐     ┌────▼────┐    ┌────▼────┐
    │PostgreSQL│    │  Redis  │    │ MLflow  │
    └─────────┘     └─────────┘    └─────────┘
```

### Key Components

- **Application Pods**: FastAPI application (3-10 replicas)
- **PostgreSQL**: Primary database for persistent data
- **Redis**: Session cache and temporary storage
- **MLflow**: Model registry and experiment tracking
- **Prometheus**: Metrics collection
- **Grafana**: Visualization and dashboards
- **Alertmanager**: Alert routing and notifications

### Service Level Objectives (SLOs)

- **Availability**: 99.9% uptime (43 minutes downtime/month)
- **Latency**: P95 < 500ms, P99 < 1000ms
- **Error Rate**: < 0.1% of requests
- **Model Accuracy**: > 85% on validation set

---

## Deployment Procedures

### Pre-Deployment Checklist

Before deploying to production, ensure:

- [ ] All CI tests pass (unit, integration, property-based)
- [ ] Code review approved by at least 2 reviewers
- [ ] Staging deployment successful and tested
- [ ] Performance tests completed (load, latency)
- [ ] Database migrations tested (if applicable)
- [ ] Rollback plan documented
- [ ] On-call engineer notified
- [ ] Change request approved (for major releases)
- [ ] Monitoring dashboards reviewed
- [ ] Backup of current deployment configuration saved

### Deployment Methods

#### Method 1: Automated Deployment (Recommended)

**Trigger**: Push tag to GitHub (e.g., `v1.2.0`)

```bash
# Create and push release tag
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0
```

**Process**:
1. GitHub Actions CI/CD pipeline triggers automatically
2. Builds Docker image and pushes to registry
3. Deploys to staging environment
4. Runs integration tests
5. Deploys to production using canary strategy
6. Monitors canary (10% → 50% → 100% traffic)
7. Sends notifications to Slack

**Monitoring**: Watch GitHub Actions workflow at https://github.com/org/repo/actions

#### Method 2: Manual Deployment

**Use Case**: Emergency hotfixes, configuration changes

```bash
# 1. Set up kubectl context
export KUBECONFIG=~/.kube/config-production
kubectl config use-context production

# 2. Verify current state
kubectl get deployments -n illness-prediction
kubectl get pods -n illness-prediction

# 3. Update image
kubectl set image deployment/illness-prediction-app \
  app=ghcr.io/org/illness-prediction:v1.2.0 \
  -n illness-prediction

# 4. Monitor rollout
kubectl rollout status deployment/illness-prediction-app \
  -n illness-prediction \
  --timeout=10m

# 5. Verify deployment
kubectl get pods -n illness-prediction
kubectl logs -f deployment/illness-prediction-app -n illness-prediction
```

#### Method 3: Canary Deployment (Manual)

**Use Case**: High-risk changes, major version updates

```bash
# 1. Deploy canary (10% traffic)
kubectl apply -f k8s/canary-deployment.yaml -n illness-prediction

kubectl set image deployment/illness-prediction-app-canary \
  app=ghcr.io/org/illness-prediction:v1.2.0 \
  -n illness-prediction

# 2. Wait for canary to be ready
kubectl rollout status deployment/illness-prediction-app-canary \
  -n illness-prediction

# 3. Monitor canary for 10 minutes
# - Check Grafana dashboards
# - Monitor error rates
# - Check latency metrics
# - Review logs for errors

# 4. If metrics are good, increase to 50% traffic
kubectl patch virtualservice illness-prediction-vs \
  -n illness-prediction \
  --type merge \
  -p '{"spec":{"http":[{"route":[{"destination":{"host":"illness-prediction-service","subset":"stable"},"weight":50},{"destination":{"host":"illness-prediction-service","subset":"canary"},"weight":50}]}]}}'

# 5. Monitor for another 10 minutes

# 6. If still good, promote to 100%
kubectl set image deployment/illness-prediction-app \
  app=ghcr.io/org/illness-prediction:v1.2.0 \
  -n illness-prediction

kubectl rollout status deployment/illness-prediction-app \
  -n illness-prediction

# 7. Clean up canary
kubectl delete deployment illness-prediction-app-canary -n illness-prediction
```

### Database Migrations

**Process**:

```bash
# 1. Backup database
kubectl exec -n illness-prediction deployment/postgres -- \
  pg_dump -U illness_prediction illness_prediction > backup-$(date +%Y%m%d-%H%M%S).sql

# 2. Apply migrations (using Alembic)
kubectl exec -n illness-prediction deployment/illness-prediction-app -- \
  alembic upgrade head

# 3. Verify migration
kubectl exec -n illness-prediction deployment/postgres -- \
  psql -U illness_prediction -d illness_prediction -c "\dt"
```

### Configuration Updates

**ConfigMap Changes**:

```bash
# 1. Edit ConfigMap
kubectl edit configmap illness-prediction-config -n illness-prediction

# 2. Restart pods to pick up changes
kubectl rollout restart deployment/illness-prediction-app -n illness-prediction

# 3. Verify
kubectl rollout status deployment/illness-prediction-app -n illness-prediction
```

**Secret Changes**:

```bash
# 1. Update secret
kubectl create secret generic illness-prediction-secrets \
  --from-literal=POSTGRES_PASSWORD=new_password \
  --from-literal=ENCRYPTION_KEY=new_key \
  -n illness-prediction \
  --dry-run=client -o yaml | kubectl apply -f -

# 2. Restart pods
kubectl rollout restart deployment/illness-prediction-app -n illness-prediction
```

### Post-Deployment Verification

```bash
# 1. Check pod status
kubectl get pods -n illness-prediction

# 2. Check service endpoints
kubectl get endpoints -n illness-prediction

# 3. Health check
curl https://illness-prediction.example.com/health

# 4. API check
curl https://illness-prediction.example.com/api/v1/health

# 5. Check logs for errors
kubectl logs -f deployment/illness-prediction-app -n illness-prediction --tail=100

# 6. Monitor Grafana dashboards
# - System Health: http://grafana.example.com/d/system-health
# - Prediction Monitoring: http://grafana.example.com/d/prediction-monitoring

# 7. Run smoke tests
pytest tests/smoke_tests.py --env=production
```

### Deployment Notifications

After successful deployment:

1. Post to Slack #deployments channel
2. Update deployment log in Confluence/Wiki
3. Notify stakeholders via email (for major releases)
4. Update status page (if applicable)

---

## Rollback Procedures

### When to Rollback

Rollback immediately if:

- Error rate > 1% for 5 minutes
- P95 latency > 1000ms for 5 minutes
- Critical functionality broken (predictions failing)
- Data corruption detected
- Security vulnerability discovered
- Database connection failures

### Rollback Methods

#### Method 1: Kubernetes Rollout Undo (Fastest)

**Time**: ~2-5 minutes

```bash
# 1. Rollback to previous version
kubectl rollout undo deployment/illness-prediction-app \
  -n illness-prediction

# 2. Monitor rollback
kubectl rollout status deployment/illness-prediction-app \
  -n illness-prediction \
  --timeout=5m

# 3. Verify
kubectl get pods -n illness-prediction
curl https://illness-prediction.example.com/health
```

#### Method 2: Rollback to Specific Version

```bash
# 1. Check rollout history
kubectl rollout history deployment/illness-prediction-app \
  -n illness-prediction

# 2. Rollback to specific revision
kubectl rollout undo deployment/illness-prediction-app \
  --to-revision=3 \
  -n illness-prediction

# 3. Verify
kubectl rollout status deployment/illness-prediction-app \
  -n illness-prediction
```

#### Method 3: Redeploy Previous Image

```bash
# 1. Deploy previous known-good version
kubectl set image deployment/illness-prediction-app \
  app=ghcr.io/org/illness-prediction:v1.1.0 \
  -n illness-prediction

# 2. Monitor
kubectl rollout status deployment/illness-prediction-app \
  -n illness-prediction
```

### Database Rollback

**If migration needs to be reverted**:

```bash
# 1. Restore from backup
kubectl exec -n illness-prediction deployment/postgres -- \
  psql -U illness_prediction -d illness_prediction < backup-20240101-120000.sql

# 2. Or downgrade migration
kubectl exec -n illness-prediction deployment/illness-prediction-app -- \
  alembic downgrade -1
```

### Model Rollback

**If new model version causes issues**:

```bash
# 1. Access MLflow UI or use API
curl -X POST https://mlflow.example.com/api/2.0/mlflow/model-versions/transition-stage \
  -H "Content-Type: application/json" \
  -d '{
    "name": "illness-prediction-model",
    "version": "5",
    "stage": "Production",
    "archive_existing_versions": true
  }'

# 2. Restart application to pick up model change
kubectl rollout restart deployment/illness-prediction-app -n illness-prediction
```

### Post-Rollback Actions

1. **Verify System Health**:
   - Check error rates returned to normal
   - Verify latency metrics
   - Confirm predictions working

2. **Incident Report**:
   - Document what went wrong
   - Root cause analysis
   - Action items to prevent recurrence

3. **Notifications**:
   - Notify team of rollback
   - Update status page
   - Post mortem meeting scheduled

---

## Monitoring and Alerting

### Monitoring Dashboards

#### 1. System Health Dashboard

**URL**: http://grafana.example.com/d/system-health

**Key Metrics**:
- API response times (P50, P95, P99)
- Request rate (requests/second)
- Error rate (%)
- CPU and memory usage
- Database connection pool
- Redis cache hit rate
- Active alerts

**Review Frequency**: Every 15 minutes during business hours

#### 2. Prediction Monitoring Dashboard

**URL**: http://grafana.example.com/d/prediction-monitoring

**Key Metrics**:
- Predictions per second
- Prediction latency
- Confidence score distribution
- Top predicted illnesses
- Active sessions
- Feedback rate

**Review Frequency**: Hourly

#### 3. Model Performance Dashboard

**URL**: http://grafana.example.com/d/model-performance

**Key Metrics**:
- Model accuracy over time
- Per-illness accuracy
- Precision, recall, F1 score
- Feedback-based accuracy
- Model version in use

**Review Frequency**: Daily

#### 4. Drift Detection Dashboard

**URL**: http://grafana.example.com/d/drift-detection

**Key Metrics**:
- Feature drift (PSI scores)
- Concept drift (accuracy trends)
- Drift events timeline
- Retraining recommendations

**Review Frequency**: Daily

### Alert Severity Levels

#### Critical (P1)
- **Response Time**: Immediate (< 5 minutes)
- **Notification**: PagerDuty + Slack + Email
- **Examples**:
  - API down for > 1 minute
  - Error rate > 1%
  - Model accuracy drop > 5%
  - Database unavailable
  - Significant feature drift (PSI > 0.25)

#### Warning (P2)
- **Response Time**: Within 30 minutes
- **Notification**: Slack + Email
- **Examples**:
  - Error rate 0.5-1%
  - P95 latency > 500ms
  - Model accuracy drop 3-5%
  - Moderate feature drift (PSI 0.1-0.25)
  - Low cache hit rate (< 70%)

#### Info (P3)
- **Response Time**: Next business day
- **Notification**: Email only
- **Examples**:
  - Model not retrained in 14 days
  - Low feedback rate
  - Non-critical configuration drift

### Alert Response Procedures

#### High Error Rate Alert

**Alert**: `HighErrorRate` - Error rate > 1%

**Response**:

1. **Acknowledge alert** in PagerDuty/Slack

2. **Check error logs**:
   ```bash
   kubectl logs -f deployment/illness-prediction-app \
     -n illness-prediction \
     --tail=500 | grep ERROR
   ```

3. **Identify error pattern**:
   - Is it a specific endpoint?
   - Is it affecting all users or specific channels?
   - Are there external API failures?

4. **Check dependencies**:
   ```bash
   # Database
   kubectl get pods -n illness-prediction | grep postgres
   
   # Redis
   kubectl get pods -n illness-prediction | grep redis
   
   # External APIs
   curl -I https://api.openai.com/v1/health
   ```

5. **Mitigation**:
   - If database issue: Check connections, restart if needed
   - If external API issue: Enable circuit breaker, use fallback
   - If application bug: Rollback to previous version

6. **Document** in incident channel

#### High Latency Alert

**Alert**: `HighPredictionLatency` - P95 latency > 500ms

**Response**:

1. **Check current latency**:
   - Grafana: Prediction Monitoring dashboard
   - Prometheus: `prediction_latency_seconds{quantile="0.95"}`

2. **Identify bottleneck**:
   ```bash
   # Check pod resources
   kubectl top pods -n illness-prediction
   
   # Check database queries
   kubectl exec -n illness-prediction deployment/postgres -- \
     psql -U illness_prediction -d illness_prediction \
     -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"
   ```

3. **Mitigation**:
   - Scale up pods if CPU/memory high
   - Optimize slow database queries
   - Check model inference time
   - Verify Redis cache working

4. **Scale if needed**:
   ```bash
   kubectl scale deployment/illness-prediction-app \
     --replicas=10 \
     -n illness-prediction
   ```

#### Model Accuracy Degradation Alert

**Alert**: `ModelAccuracyDegradation` - Accuracy drops > 5%

**Response**:

1. **Verify alert**:
   - Check Model Performance dashboard
   - Review recent feedback data

2. **Investigate cause**:
   - Check for data drift (Drift Detection dashboard)
   - Review recent model deployments
   - Analyze failing predictions

3. **Immediate action**:
   - If recent model deployment: Rollback model
   - If data drift: Trigger retraining
   - If data quality issue: Investigate data pipeline

4. **Rollback model if needed**:
   ```bash
   # See Model Rollback section above
   ```

5. **Notify ML team** for investigation

#### Drift Detection Alert

**Alert**: `SignificantFeatureDrift` - PSI > 0.25

**Response**:

1. **Review Drift Detection dashboard**:
   - Which features are drifting?
   - Gradual or sudden drift?
   - Concept drift also present?

2. **Analyze drift**:
   ```bash
   # Check recent drift reports
   kubectl exec -n illness-prediction deployment/illness-prediction-app -- \
     python -m src.mlops.drift_detection_service --report
   ```

3. **Action**:
   - **Significant drift**: Schedule model retraining
   - **Multiple features**: Investigate data source changes
   - **Concept drift**: Urgent retraining needed

4. **Trigger retraining**:
   ```bash
   # Via API or MLflow
   curl -X POST https://api.illness-prediction.example.com/api/v1/mlops/retrain \
     -H "Authorization: Bearer $API_KEY"
   ```

5. **Monitor** retraining progress and new model performance

### Alerting Best Practices

1. **Acknowledge alerts promptly** to prevent duplicate notifications
2. **Document actions** in incident channel for team visibility
3. **Update runbook** if new resolution steps discovered
4. **Tune alert thresholds** based on false positive rate
5. **Review alerts weekly** in team meeting

---

## Incident Response

### Incident Severity Classification

#### Severity 1 (Critical)
- **Impact**: Complete service outage or data loss
- **Examples**: API down, database corruption, security breach
- **Response Time**: Immediate
- **Escalation**: Notify CTO, VP Engineering

#### Severity 2 (High)
- **Impact**: Major functionality degraded
- **Examples**: Predictions failing, high error rate, severe performance degradation
- **Response Time**: < 15 minutes
- **Escalation**: Notify Engineering Manager

#### Severity 3 (Medium)
- **Impact**: Minor functionality affected
- **Examples**: Single feature broken, moderate performance issues
- **Response Time**: < 1 hour
- **Escalation**: Team lead

#### Severity 4 (Low)
- **Impact**: Minimal user impact
- **Examples**: UI glitch, non-critical feature issue
- **Response Time**: Next business day
- **Escalation**: None

### Incident Response Process

#### 1. Detection and Triage (0-5 minutes)

- **Alert received** via PagerDuty/Slack
- **Acknowledge alert** to stop notifications
- **Assess severity** using classification above
- **Create incident channel** in Slack: `#incident-YYYYMMDD-description`
- **Notify team** in incident channel

#### 2. Investigation (5-15 minutes)

- **Gather information**:
  - Check monitoring dashboards
  - Review recent deployments
  - Check error logs
  - Verify dependencies

- **Identify root cause**:
  - Application bug?
  - Infrastructure issue?
  - External dependency failure?
  - Data quality problem?

- **Document findings** in incident channel

#### 3. Mitigation (15-30 minutes)

- **Implement fix**:
  - Rollback deployment if recent change
  - Scale resources if capacity issue
  - Restart services if transient failure
  - Enable circuit breaker if external API issue

- **Verify fix**:
  - Check metrics returned to normal
  - Test affected functionality
  - Monitor for 10 minutes

- **Update status page** (if customer-facing)

#### 4. Resolution (30-60 minutes)

- **Confirm incident resolved**:
  - All metrics normal
  - No errors in logs
  - Functionality restored

- **Close incident channel**
- **Update status page**: "Incident resolved"
- **Thank team** for response

#### 5. Post-Incident Review (Within 48 hours)

- **Schedule post-mortem meeting**
- **Create incident report** with:
  - Timeline of events
  - Root cause analysis
  - Impact assessment
  - Resolution steps
  - Action items to prevent recurrence

- **Share learnings** with team
- **Update runbook** with new procedures

### Incident Communication Templates

#### Initial Notification

```
🚨 INCIDENT DETECTED 🚨

Severity: [P1/P2/P3]
Component: [API/Database/Model/etc.]
Impact: [Description of user impact]
Status: Investigating

Incident Channel: #incident-YYYYMMDD-description
Incident Commander: @username

Updates will be posted every 15 minutes.
```

#### Status Update

```
📊 INCIDENT UPDATE

Time: [HH:MM UTC]
Status: [Investigating/Mitigating/Resolved]
Progress: [What we've learned/done]
Next Steps: [What we're doing next]
ETA: [Estimated resolution time]
```

#### Resolution Notification

```
✅ INCIDENT RESOLVED

Duration: [X hours Y minutes]
Root Cause: [Brief description]
Resolution: [What fixed it]
Impact: [Number of users/requests affected]

Post-mortem scheduled for [Date/Time]
Thank you to @user1 @user2 for quick response!
```

### Common Incident Scenarios

#### Scenario 1: Complete API Outage

**Symptoms**: All health checks failing, 100% error rate

**Response**:

1. Check pod status:
   ```bash
   kubectl get pods -n illness-prediction
   ```

2. If pods crashing, check logs:
   ```bash
   kubectl logs deployment/illness-prediction-app -n illness-prediction --previous
   ```

3. Common causes:
   - Database connection failure
   - Configuration error
   - Resource exhaustion
   - Bad deployment

4. Quick fixes:
   - Rollback deployment
   - Restart pods
   - Scale up resources
   - Fix configuration

#### Scenario 2: Database Connection Exhaustion

**Symptoms**: Intermittent errors, "too many connections"

**Response**:

1. Check active connections:
   ```bash
   kubectl exec -n illness-prediction deployment/postgres -- \
     psql -U illness_prediction -d illness_prediction \
     -c "SELECT count(*) FROM pg_stat_activity;"
   ```

2. Kill idle connections:
   ```bash
   kubectl exec -n illness-prediction deployment/postgres -- \
     psql -U illness_prediction -d illness_prediction \
     -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '5 minutes';"
   ```

3. Increase connection pool:
   - Update ConfigMap: `DB_POOL_SIZE`
   - Restart application

#### Scenario 3: Model Prediction Failures

**Symptoms**: Predictions returning errors or low confidence

**Response**:

1. Check model service:
   ```bash
   kubectl logs deployment/illness-prediction-app -n illness-prediction | grep "model"
   ```

2. Verify model loaded:
   ```bash
   curl https://api.illness-prediction.example.com/api/v1/model/info
   ```

3. Common causes:
   - Model file corrupted
   - Model version mismatch
   - Insufficient memory
   - Feature engineering error

4. Fix:
   - Rollback to previous model version
   - Reload model from MLflow
   - Increase pod memory

#### Scenario 4: External API Failure (LLM, Translation, etc.)

**Symptoms**: Symptom extraction failing, translation errors

**Response**:

1. Check external API status:
   ```bash
   curl -I https://api.openai.com/v1/health
   ```

2. Enable circuit breaker:
   - Update ConfigMap: `CIRCUIT_BREAKER_ENABLED=true`
   - Restart application

3. Use fallback:
   - Simple keyword extraction instead of LLM
   - Default language instead of translation

4. Monitor external API status page

---

## Common Issues and Resolutions

### Issue: Pods in CrashLoopBackOff

**Symptoms**:
```bash
kubectl get pods -n illness-prediction
# NAME                                    READY   STATUS             RESTARTS
# illness-prediction-app-xxx              0/1     CrashLoopBackOff   5
```

**Diagnosis**:
```bash
# Check logs
kubectl logs pod/illness-prediction-app-xxx -n illness-prediction

# Check previous logs
kubectl logs pod/illness-prediction-app-xxx -n illness-prediction --previous

# Describe pod
kubectl describe pod/illness-prediction-app-xxx -n illness-prediction
```

**Common Causes**:
1. **Missing environment variables**: Check secrets and configmaps
2. **Database connection failure**: Verify database is running
3. **Port already in use**: Check port conflicts
4. **Insufficient resources**: Check resource limits

**Resolution**:
```bash
# Fix configuration
kubectl edit configmap illness-prediction-config -n illness-prediction

# Or rollback
kubectl rollout undo deployment/illness-prediction-app -n illness-prediction
```

### Issue: High Memory Usage

**Symptoms**: Pods being OOMKilled, high memory alerts

**Diagnosis**:
```bash
# Check current usage
kubectl top pods -n illness-prediction

# Check memory limits
kubectl describe pod/illness-prediction-app-xxx -n illness-prediction | grep -A 5 "Limits"
```

**Resolution**:
```bash
# Increase memory limits
kubectl patch deployment illness-prediction-app -n illness-prediction \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"app","resources":{"limits":{"memory":"4Gi"}}}]}}}}'

# Or scale horizontally
kubectl scale deployment/illness-prediction-app --replicas=10 -n illness-prediction
```

### Issue: Slow Database Queries

**Symptoms**: High latency, database connection timeouts

**Diagnosis**:
```bash
# Check slow queries
kubectl exec -n illness-prediction deployment/postgres -- \
  psql -U illness_prediction -d illness_prediction \
  -c "SELECT query, calls, total_time, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

**Resolution**:
1. Add database indexes
2. Optimize queries
3. Increase database resources
4. Enable query caching

### Issue: Redis Connection Failures

**Symptoms**: Session errors, cache misses

**Diagnosis**:
```bash
# Check Redis status
kubectl get pods -n illness-prediction | grep redis

# Test connection
kubectl exec -n illness-prediction deployment/redis -- redis-cli ping
```

**Resolution**:
```bash
# Restart Redis
kubectl rollout restart deployment/redis -n illness-prediction

# Or check password
kubectl get secret illness-prediction-secrets -n illness-prediction -o jsonpath='{.data.REDIS_PASSWORD}' | base64 -d
```

### Issue: Certificate Expiration

**Symptoms**: HTTPS errors, certificate warnings

**Diagnosis**:
```bash
# Check certificate expiration
kubectl get certificate -n illness-prediction

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager
```

**Resolution**:
```bash
# Force renewal
kubectl delete certificate illness-prediction-tls -n illness-prediction
kubectl apply -f k8s/ingress.yaml -n illness-prediction

# Verify
kubectl describe certificate illness-prediction-tls -n illness-prediction
```

---

## Emergency Contacts

### On-Call Rotation

- **Primary On-Call**: Check PagerDuty schedule
- **Secondary On-Call**: Check PagerDuty schedule
- **Escalation**: Engineering Manager

### Team Contacts

| Role | Name | Email | Phone | Slack |
|------|------|-------|-------|-------|
| Engineering Manager | [Name] | manager@example.com | +1-XXX-XXX-XXXX | @manager |
| ML Lead | [Name] | ml-lead@example.com | +1-XXX-XXX-XXXX | @ml-lead |
| DevOps Lead | [Name] | devops@example.com | +1-XXX-XXX-XXXX | @devops |
| Database Admin | [Name] | dba@example.com | +1-XXX-XXX-XXXX | @dba |

### External Contacts

| Service | Contact | Support URL |
|---------|---------|-------------|
| Cloud Provider (AWS/GCP/Azure) | Support Portal | https://support.provider.com |
| OpenAI API | support@openai.com | https://help.openai.com |
| Twilio | support@twilio.com | https://support.twilio.com |
| PagerDuty | support@pagerduty.com | https://support.pagerduty.com |

### Slack Channels

- **#incidents**: Active incident coordination
- **#alerts-critical**: Critical alerts
- **#ml-alerts**: ML model and drift alerts
- **#ops-alerts**: Infrastructure alerts
- **#deployments**: Deployment notifications
- **#on-call**: On-call coordination

### Escalation Path

1. **Level 1**: On-call engineer (0-15 minutes)
2. **Level 2**: Team lead (15-30 minutes)
3. **Level 3**: Engineering manager (30-60 minutes)
4. **Level 4**: VP Engineering / CTO (> 60 minutes or critical)

---

## Appendix

### Useful Commands

```bash
# Quick health check
kubectl get all -n illness-prediction

# Check recent events
kubectl get events -n illness-prediction --sort-by='.lastTimestamp' | tail -20

# Port forward for local testing
kubectl port-forward -n illness-prediction service/illness-prediction-service 8080:80

# Execute command in pod
kubectl exec -it deployment/illness-prediction-app -n illness-prediction -- /bin/bash

# Copy files from pod
kubectl cp illness-prediction/pod-name:/path/to/file ./local-file

# View resource usage
kubectl top nodes
kubectl top pods -n illness-prediction

# Check ingress
kubectl get ingress -n illness-prediction
kubectl describe ingress illness-prediction-ingress -n illness-prediction
```

### Monitoring URLs

- **Grafana**: http://grafana.example.com
- **Prometheus**: http://prometheus.example.com
- **Alertmanager**: http://alertmanager.example.com
- **MLflow**: http://mlflow.example.com
- **Status Page**: http://status.illness-prediction.example.com

### Documentation Links

- [Architecture Documentation](../architecture/ARCHITECTURE.md)
- [API Documentation](../api/README.md)
- [Monitoring Guide](../../config/monitoring/README.md)
- [Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [Security Guide](./SECURITY_GUIDE.md)

---

**Document Version**: 1.0.0  
**Last Review**: 2024  
**Next Review**: Quarterly  
**Owner**: Operations Team
