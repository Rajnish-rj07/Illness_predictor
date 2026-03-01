# Illness Prediction System - Incident Response Playbook

**Version**: 1.0.0  
**Last Updated**: 2024  
**Owner**: Operations Team

## Table of Contents

1. [Incident Response Overview](#incident-response-overview)
2. [Severity Classification](#severity-classification)
3. [Response Procedures](#response-procedures)
4. [Incident Scenarios](#incident-scenarios)
5. [Communication Templates](#communication-templates)
6. [Post-Incident Process](#post-incident-process)

---

## Incident Response Overview

### Incident Response Team

| Role | Responsibilities | Contact |
|------|------------------|---------|
| **Incident Commander** | Overall coordination, decision making | On-call engineer |
| **Technical Lead** | Technical investigation, mitigation | Senior engineer |
| **Communications Lead** | Stakeholder updates, status page | Product manager |
| **Subject Matter Expert** | Domain-specific expertise | ML engineer, DBA, etc. |

### Response Timeline

```
Detection → Triage → Investigation → Mitigation → Resolution → Post-Mortem
   ↓          ↓           ↓              ↓            ↓            ↓
  0-5min   5-15min    15-30min       30-60min     60min+      24-48hrs
```

### Incident Lifecycle

1. **Detection**: Alert fires or issue reported
2. **Triage**: Assess severity and impact
3. **Investigation**: Identify root cause
4. **Mitigation**: Implement temporary fix
5. **Resolution**: Permanent fix deployed
6. **Post-Mortem**: Learn and improve

---

## Severity Classification

### Severity 1 (Critical) - P1

**Definition**: Complete service outage or critical functionality unavailable

**Impact**:
- All users unable to access system
- Data loss or corruption
- Security breach
- Revenue impact > $10,000/hour

**Response Time**: Immediate (< 5 minutes)

**Escalation**: 
- Notify: CTO, VP Engineering, Product VP
- PagerDuty: High urgency
- Status Page: Update immediately

**Examples**:
- API completely down
- Database unavailable
- Authentication system failure
- Data breach detected
- All predictions failing

### Severity 2 (High) - P2

**Definition**: Major functionality degraded, significant user impact

**Impact**:
- Core features unavailable or severely degraded
- Affects > 50% of users
- Workaround available but difficult
- Revenue impact $1,000-$10,000/hour

**Response Time**: < 15 minutes

**Escalation**:
- Notify: Engineering Manager, Product Manager
- PagerDuty: Medium urgency
- Status Page: Update within 30 minutes

**Examples**:
- High error rate (> 1%)
- Severe performance degradation (P95 > 1000ms)
- Model accuracy drop > 5%
- SMS/WhatsApp integration down
- Significant feature drift (PSI > 0.25)

### Severity 3 (Medium) - P3

**Definition**: Minor functionality affected, limited user impact

**Impact**:
- Non-critical features unavailable
- Affects < 50% of users
- Easy workaround available
- Minimal revenue impact

**Response Time**: < 1 hour

**Escalation**:
- Notify: Team lead
- No PagerDuty
- Status Page: Optional

**Examples**:
- Single feature broken
- Moderate performance issues (P95 500-1000ms)
- Model accuracy drop 3-5%
- Non-critical external API failure
- Moderate feature drift (PSI 0.1-0.25)

### Severity 4 (Low) - P4

**Definition**: Minimal impact, cosmetic issues

**Impact**:
- Minor inconvenience
- Affects < 10% of users
- No workaround needed
- No revenue impact

**Response Time**: Next business day

**Escalation**: None

**Examples**:
- UI glitch
- Non-critical logging issue
- Documentation error
- Minor configuration drift

---

## Response Procedures

### Phase 1: Detection and Triage (0-5 minutes)

#### Step 1: Acknowledge Alert

```bash
# PagerDuty
- Click "Acknowledge" in PagerDuty app
- Or reply "ack" to PagerDuty SMS

# Slack
- React with 👀 emoji to alert in #alerts-critical
```

#### Step 2: Create Incident Channel

```bash
# Slack command
/incident create [brief-description]

# Example
/incident create api-down-500-errors

# This creates: #incident-20240115-api-down-500-errors
```

#### Step 3: Initial Assessment

**Questions to answer**:
- What is the user-facing impact?
- How many users are affected?
- Is data at risk?
- What changed recently?

**Quick checks**:
```bash
# Check system status
kubectl get pods -n illness-prediction

# Check recent deployments
kubectl rollout history deployment/illness-prediction-app -n illness-prediction

# Check error rate
curl http://prometheus:9090/api/v1/query?query=rate(http_requests_total{status=~"5.."}[5m])

# Check logs
kubectl logs -f deployment/illness-prediction-app -n illness-prediction --tail=100 | grep ERROR
```

#### Step 4: Assign Severity

Use classification above to assign P1-P4 severity.

#### Step 5: Notify Team

```bash
# Post in incident channel
@here Incident detected: [brief description]
Severity: P[1-4]
Impact: [user impact]
Incident Commander: @username
Status: Investigating

# For P1, also notify via phone
```

### Phase 2: Investigation (5-15 minutes)

#### Step 1: Gather Information

**System Health**:
```bash
# Check all pods
kubectl get pods -n illness-prediction

# Check services
kubectl get svc -n illness-prediction

# Check ingress
kubectl get ingress -n illness-prediction

# Check recent events
kubectl get events -n illness-prediction --sort-by='.lastTimestamp' | tail -20
```

**Metrics**:
- Open Grafana dashboards
- Check error rate trends
- Check latency trends
- Check resource usage

**Logs**:
```bash
# Application logs
kubectl logs -f deployment/illness-prediction-app -n illness-prediction --tail=500

# Database logs
kubectl logs -f deployment/postgres -n illness-prediction --tail=200

# Ingress logs
kubectl logs -f -n ingress-nginx deployment/ingress-nginx-controller --tail=200
```

**Recent Changes**:
```bash
# Check recent deployments
kubectl rollout history deployment/illness-prediction-app -n illness-prediction

# Check recent config changes
kubectl get configmap illness-prediction-config -n illness-prediction -o yaml

# Check GitHub commits
git log --oneline --since="2 hours ago"
```

#### Step 2: Form Hypothesis

Based on gathered information, form hypothesis about root cause:
- Recent deployment?
- Configuration change?
- External dependency failure?
- Resource exhaustion?
- Database issue?
- Network problem?

#### Step 3: Test Hypothesis

```bash
# Example: Test if recent deployment caused issue
kubectl rollout undo deployment/illness-prediction-app -n illness-prediction

# Wait 2 minutes and check if issue resolved
```

#### Step 4: Update Team

```bash
# Post in incident channel every 10-15 minutes
Update: [timestamp]
Status: Investigating
Findings: [what we've learned]
Hypothesis: [current theory]
Next steps: [what we're trying next]
```

### Phase 3: Mitigation (15-30 minutes)

#### Step 1: Implement Fix

**Common mitigations**:

1. **Rollback deployment**:
```bash
kubectl rollout undo deployment/illness-prediction-app -n illness-prediction
```

2. **Scale resources**:
```bash
kubectl scale deployment/illness-prediction-app --replicas=10 -n illness-prediction
```

3. **Restart services**:
```bash
kubectl rollout restart deployment/illness-prediction-app -n illness-prediction
```

4. **Update configuration**:
```bash
kubectl edit configmap illness-prediction-config -n illness-prediction
kubectl rollout restart deployment/illness-prediction-app -n illness-prediction
```

5. **Enable circuit breaker**:
```bash
kubectl set env deployment/illness-prediction-app CIRCUIT_BREAKER_ENABLED=true -n illness-prediction
```

6. **Rollback model**:
```bash
kubectl set env deployment/illness-prediction-app MODEL_VERSION=v1.0.0 -n illness-prediction
kubectl rollout restart deployment/illness-prediction-app -n illness-prediction
```

#### Step 2: Verify Fix

```bash
# Check error rate
curl http://prometheus:9090/api/v1/query?query=rate(http_requests_total{status=~"5.."}[5m])

# Check latency
curl http://prometheus:9090/api/v1/query?query=histogram_quantile(0.95,rate(http_request_duration_seconds_bucket[5m]))

# Test endpoints
curl https://illness-prediction.example.com/health
curl https://illness-prediction.example.com/api/v1/health

# Check logs
kubectl logs -f deployment/illness-prediction-app -n illness-prediction --tail=100
```

#### Step 3: Monitor

Monitor for 10-15 minutes to ensure fix is stable:
- Error rate back to normal (< 0.1%)
- Latency back to normal (P95 < 500ms)
- No errors in logs
- User reports resolved

### Phase 4: Resolution (30-60 minutes)

#### Step 1: Confirm Resolution

```bash
# All metrics normal for 15+ minutes
# No errors in logs
# User reports resolved
# Functionality verified
```

#### Step 2: Update Status

```bash
# Post in incident channel
✅ INCIDENT RESOLVED

Duration: [X hours Y minutes]
Root Cause: [brief description]
Resolution: [what fixed it]
Impact: [number of users/requests affected]

Post-mortem scheduled for [date/time]
Thank you @user1 @user2 @user3 for quick response!
```

#### Step 3: Update Status Page

```
Incident Resolved

We have resolved the issue affecting [service/feature].
All systems are now operating normally.

Duration: [start time] - [end time]
Impact: [brief description]

We apologize for any inconvenience.
```

#### Step 4: Close Incident

```bash
# PagerDuty
- Click "Resolve" in PagerDuty app

# Slack
- Archive incident channel (after 24 hours)
```

---

## Incident Scenarios

### Scenario 1: Complete API Outage (P1)

**Symptoms**:
- All health checks failing
- 100% error rate
- Users cannot access system

**Investigation**:
```bash
# Check pod status
kubectl get pods -n illness-prediction
# If pods are CrashLoopBackOff or Error

# Check logs
kubectl logs deployment/illness-prediction-app -n illness-prediction --previous
# Look for startup errors

# Check recent changes
kubectl rollout history deployment/illness-prediction-app -n illness-prediction
```

**Common Causes**:
1. Bad deployment
2. Database connection failure
3. Configuration error
4. Resource exhaustion

**Resolution**:

**If bad deployment**:
```bash
kubectl rollout undo deployment/illness-prediction-app -n illness-prediction
kubectl rollout status deployment/illness-prediction-app -n illness-prediction
```

**If database issue**:
```bash
# Check database
kubectl get pods -n illness-prediction | grep postgres

# Restart database if needed
kubectl rollout restart deployment/postgres -n illness-prediction

# Verify connection
kubectl exec -n illness-prediction deployment/postgres -- pg_isready
```

**If configuration error**:
```bash
# Restore previous config
kubectl rollout undo deployment/illness-prediction-app -n illness-prediction

# Or fix config
kubectl edit configmap illness-prediction-config -n illness-prediction
kubectl rollout restart deployment/illness-prediction-app -n illness-prediction
```

**Timeline**: 5-15 minutes to resolve

### Scenario 2: High Error Rate (P2)

**Symptoms**:
- Error rate > 1%
- Some requests failing
- Users reporting intermittent issues

**Investigation**:
```bash
# Check error rate by endpoint
kubectl logs deployment/illness-prediction-app -n illness-prediction | grep ERROR | cut -d' ' -f5 | sort | uniq -c

# Check external dependencies
curl -I https://api.openai.com/v1/health
curl -I https://api.twilio.com/health

# Check database connections
kubectl exec -n illness-prediction deployment/postgres -- \
  psql -U illness_prediction -d illness_prediction \
  -c "SELECT count(*) FROM pg_stat_activity;"
```

**Common Causes**:
1. External API failure
2. Database connection pool exhaustion
3. Rate limiting
4. Memory leak

**Resolution**:

**If external API failure**:
```bash
# Enable circuit breaker
kubectl set env deployment/illness-prediction-app \
  CIRCUIT_BREAKER_ENABLED=true \
  CIRCUIT_BREAKER_THRESHOLD=5 \
  -n illness-prediction

# Or use fallback
kubectl set env deployment/illness-prediction-app \
  USE_FALLBACK_LLM=true \
  -n illness-prediction
```

**If connection pool exhaustion**:
```bash
# Increase pool size
kubectl set env deployment/illness-prediction-app \
  DB_POOL_SIZE=20 \
  -n illness-prediction

# Kill idle connections
kubectl exec -n illness-prediction deployment/postgres -- \
  psql -U illness_prediction -d illness_prediction \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '5 minutes';"
```

**If memory leak**:
```bash
# Restart pods one by one
kubectl rollout restart deployment/illness-prediction-app -n illness-prediction

# Increase memory limit
kubectl patch deployment illness-prediction-app -n illness-prediction \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"app","resources":{"limits":{"memory":"4Gi"}}}]}}}}'
```

**Timeline**: 15-30 minutes to resolve

### Scenario 3: High Latency (P2)

**Symptoms**:
- P95 latency > 500ms
- Users reporting slow responses
- Timeouts occurring

**Investigation**:
```bash
# Check latency by endpoint
kubectl logs deployment/illness-prediction-app -n illness-prediction | grep "request_duration" | awk '{print $NF}' | sort -n | tail -20

# Check resource usage
kubectl top pods -n illness-prediction

# Check database queries
kubectl exec -n illness-prediction deployment/postgres -- \
  psql -U illness_prediction -d illness_prediction \
  -c "SELECT query, calls, total_time, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Check model inference time
kubectl logs deployment/illness-prediction-app -n illness-prediction | grep "model_inference_time"
```

**Common Causes**:
1. High load
2. Slow database queries
3. Model inference slow
4. External API latency

**Resolution**:

**If high load**:
```bash
# Scale up
kubectl scale deployment/illness-prediction-app --replicas=10 -n illness-prediction

# Or enable HPA
kubectl autoscale deployment illness-prediction-app \
  --min=3 --max=10 --cpu-percent=70 \
  -n illness-prediction
```

**If slow queries**:
```bash
# Add database indexes
kubectl exec -n illness-prediction deployment/postgres -- \
  psql -U illness_prediction -d illness_prediction \
  -c "CREATE INDEX idx_sessions_user_id ON sessions(user_id);"

# Or optimize queries in code
```

**If model slow**:
```bash
# Use smaller model
kubectl set env deployment/illness-prediction-app MODEL_VERSION=v1.0.0-lite -n illness-prediction

# Or increase model server resources
kubectl patch deployment illness-prediction-app -n illness-prediction \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"app","resources":{"limits":{"cpu":"4000m"}}}]}}}}'
```

**Timeline**: 20-40 minutes to resolve

### Scenario 4: Model Accuracy Degradation (P2)

**Symptoms**:
- Model accuracy drops > 5%
- Users reporting incorrect predictions
- Feedback showing low accuracy

**Investigation**:
```bash
# Check Model Performance dashboard in Grafana

# Check recent model deployments
kubectl get configmap model-config -n illness-prediction -o yaml

# Check for data drift
kubectl logs deployment/illness-prediction-app -n illness-prediction | grep "drift_detected"

# Analyze recent predictions
kubectl exec -n illness-prediction deployment/postgres -- \
  psql -U illness_prediction -d illness_prediction \
  -c "SELECT illness, confidence_score, was_correct FROM predictions JOIN feedback ON predictions.id = feedback.prediction_id WHERE created_at > now() - interval '24 hours';"
```

**Common Causes**:
1. Data drift
2. Bad model deployment
3. Feature engineering bug
4. Data quality issue

**Resolution**:

**If bad model deployment**:
```bash
# Rollback model
kubectl set env deployment/illness-prediction-app MODEL_VERSION=v1.0.0 -n illness-prediction
kubectl rollout restart deployment/illness-prediction-app -n illness-prediction
```

**If data drift**:
```bash
# Trigger retraining
curl -X POST https://api.illness-prediction.example.com/api/v1/mlops/retrain \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"reason": "data_drift", "priority": "high"}'

# Monitor retraining
kubectl logs -f deployment/illness-prediction-app -n illness-prediction | grep "training"
```

**If feature bug**:
```bash
# Rollback code
kubectl rollout undo deployment/illness-prediction-app -n illness-prediction

# Fix bug and redeploy
```

**Timeline**: 30-60 minutes to mitigate, 2-4 hours for retraining

### Scenario 5: Database Unavailable (P1)

**Symptoms**:
- All database operations failing
- "Connection refused" errors
- Pods unable to start

**Investigation**:
```bash
# Check database pod
kubectl get pods -n illness-prediction | grep postgres

# Check database logs
kubectl logs deployment/postgres -n illness-prediction --tail=200

# Check PVC
kubectl get pvc -n illness-prediction

# Check database service
kubectl get svc -n illness-prediction | grep postgres
```

**Common Causes**:
1. Pod crashed
2. Disk full
3. Corrupted data
4. Network issue

**Resolution**:

**If pod crashed**:
```bash
# Restart database
kubectl rollout restart deployment/postgres -n illness-prediction

# Wait for ready
kubectl wait --for=condition=ready pod -l app=postgres -n illness-prediction --timeout=300s

# Verify
kubectl exec -n illness-prediction deployment/postgres -- pg_isready
```

**If disk full**:
```bash
# Check disk usage
kubectl exec -n illness-prediction deployment/postgres -- df -h

# Increase PVC size
kubectl patch pvc postgres-pvc -n illness-prediction \
  -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'

# Or clean up old data
kubectl exec -n illness-prediction deployment/postgres -- \
  psql -U illness_prediction -d illness_prediction \
  -c "DELETE FROM predictions WHERE created_at < now() - interval '90 days';"
```

**If corrupted data**:
```bash
# Restore from backup
kubectl exec -i -n illness-prediction deployment/postgres -- \
  psql -U illness_prediction -d illness_prediction < backup-latest.sql

# Verify
kubectl exec -n illness-prediction deployment/postgres -- \
  psql -U illness_prediction -d illness_prediction -c "\dt"
```

**Timeline**: 10-30 minutes to resolve

### Scenario 6: Security Breach (P1)

**Symptoms**:
- Unauthorized access detected
- Suspicious activity in logs
- Security alert triggered

**Investigation**:
```bash
# Check access logs
kubectl logs deployment/illness-prediction-app -n illness-prediction | grep "unauthorized"

# Check recent API calls
kubectl exec -n illness-prediction deployment/postgres -- \
  psql -U illness_prediction -d illness_prediction \
  -c "SELECT * FROM api_logs WHERE created_at > now() - interval '1 hour' ORDER BY created_at DESC LIMIT 100;"

# Check for data exfiltration
kubectl logs deployment/illness-prediction-app -n illness-prediction | grep "large_response"
```

**Immediate Actions**:

1. **Isolate system**:
```bash
# Block all external traffic
kubectl patch ingress illness-prediction-ingress -n illness-prediction \
  -p '{"spec":{"rules":[]}}'

# Or scale to 0
kubectl scale deployment/illness-prediction-app --replicas=0 -n illness-prediction
```

2. **Rotate credentials**:
```bash
# Rotate all secrets
kubectl create secret generic illness-prediction-secrets \
  --from-literal=POSTGRES_PASSWORD='new_password' \
  --from-literal=JWT_SECRET_KEY='new_secret' \
  -n illness-prediction \
  --dry-run=client -o yaml | kubectl apply -f -
```

3. **Notify security team**:
```bash
# Email: security@example.com
# Slack: #security-incidents
# Phone: Security on-call
```

4. **Preserve evidence**:
```bash
# Backup logs
kubectl logs deployment/illness-prediction-app -n illness-prediction > incident-logs-$(date +%Y%m%d-%H%M%S).log

# Backup database
kubectl exec -n illness-prediction deployment/postgres -- \
  pg_dump -U illness_prediction illness_prediction > incident-db-backup-$(date +%Y%m%d-%H%M%S).sql
```

5. **Investigate and remediate**:
- Work with security team
- Identify vulnerability
- Patch vulnerability
- Verify no data loss
- Restore service

**Timeline**: 1-4 hours to contain, days to fully investigate

---

## Communication Templates

### Initial Incident Notification

**Slack (#incident-channel)**:
```
🚨 INCIDENT DETECTED 🚨

Severity: P[1/2/3]
Component: [API/Database/Model/etc.]
Impact: [Brief description of user impact]
Affected Users: [Estimated number or percentage]
Status: Investigating

Incident Commander: @username
Technical Lead: @username

Timeline:
- [HH:MM UTC] Incident detected
- [HH:MM UTC] Team notified
- [HH:MM UTC] Investigation started

Next update in 15 minutes.

Incident Channel: #incident-YYYYMMDD-description
```

**Status Page**:
```
Investigating - [Service Name]

We are investigating reports of [brief description].
We will provide updates as we learn more.

Posted: [timestamp]
```

### Status Update

**Slack**:
```
📊 INCIDENT UPDATE - [HH:MM UTC]

Status: [Investigating/Mitigating/Monitoring]

Progress:
- [What we've learned]
- [What we've tried]
- [Current hypothesis]

Next Steps:
- [What we're doing next]

ETA: [Estimated resolution time or "Unknown"]

Next update in 15 minutes.
```

**Status Page**:
```
Update - [Service Name]

We have identified the issue as [brief description].
We are working on a fix and expect resolution within [timeframe].

Impact: [Updated impact description]

Posted: [timestamp]
```

### Resolution Notification

**Slack**:
```
✅ INCIDENT RESOLVED

Duration: [X hours Y minutes]
Root Cause: [Brief description]
Resolution: [What fixed it]

Impact:
- Affected Users: [Number or percentage]
- Affected Requests: [Number]
- Duration: [Start time] - [End time]

Timeline:
- [HH:MM UTC] Incident detected
- [HH:MM UTC] Root cause identified
- [HH:MM UTC] Fix implemented
- [HH:MM UTC] Incident resolved

Post-mortem scheduled for [date/time]

Thank you to @user1 @user2 @user3 for quick response! 🎉
```

**Status Page**:
```
Resolved - [Service Name]

The issue affecting [service/feature] has been resolved.
All systems are now operating normally.

Root Cause: [Brief description]
Resolution: [What fixed it]

Duration: [start time] - [end time]

We apologize for any inconvenience this may have caused.

Posted: [timestamp]
```

### Customer Communication (Email)

**Subject**: [Resolved] Service Disruption - [Date]

```
Dear Valued Customer,

We want to inform you about a service disruption that occurred on [date] from [start time] to [end time] UTC.

What Happened:
[Brief description of the incident and impact]

What We Did:
[Brief description of how we resolved it]

Impact:
[Description of what features/functionality were affected]

What We're Doing to Prevent This:
[Brief description of preventive measures]

We sincerely apologize for any inconvenience this may have caused. If you have any questions or concerns, please don't hesitate to contact our support team at support@example.com.

Thank you for your patience and understanding.

Best regards,
[Company Name] Team
```

---

## Post-Incident Process

### Post-Mortem Meeting

**Schedule**: Within 48 hours of incident resolution

**Attendees**:
- Incident Commander
- Technical Lead
- All responders
- Engineering Manager
- Product Manager (for P1/P2)

**Agenda**:
1. Timeline review (10 min)
2. Root cause analysis (15 min)
3. What went well (10 min)
4. What could be improved (15 min)
5. Action items (10 min)

### Post-Mortem Document

**Template**:

```markdown
# Post-Mortem: [Incident Title]

**Date**: [YYYY-MM-DD]
**Severity**: P[1/2/3]
**Duration**: [X hours Y minutes]
**Impact**: [Brief description]

## Summary

[2-3 sentence summary of what happened]

## Timeline

| Time (UTC) | Event |
|------------|-------|
| HH:MM | Incident detected |
| HH:MM | Team notified |
| HH:MM | Investigation started |
| HH:MM | Root cause identified |
| HH:MM | Fix implemented |
| HH:MM | Incident resolved |

## Root Cause

[Detailed explanation of what caused the incident]

## Impact

- **Users Affected**: [Number or percentage]
- **Requests Affected**: [Number]
- **Revenue Impact**: [If applicable]
- **Duration**: [Start time] - [End time]

## Detection

- **How Detected**: [Alert, user report, monitoring, etc.]
- **Time to Detect**: [Time from incident start to detection]

## Response

- **Time to Acknowledge**: [Time from detection to acknowledgment]
- **Time to Mitigate**: [Time from acknowledgment to mitigation]
- **Time to Resolve**: [Time from mitigation to full resolution]

## What Went Well

1. [Thing that went well]
2. [Thing that went well]
3. [Thing that went well]

## What Could Be Improved

1. [Thing to improve]
2. [Thing to improve]
3. [Thing to improve]

## Action Items

| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Action item 1] | @user | YYYY-MM-DD | Open |
| [Action item 2] | @user | YYYY-MM-DD | Open |
| [Action item 3] | @user | YYYY-MM-DD | Open |

## Lessons Learned

[Key takeaways from this incident]

## Related Incidents

- [Link to similar past incidents]

---

**Document Owner**: [Name]
**Reviewed By**: [Names]
**Date**: [YYYY-MM-DD]
```

### Action Item Tracking

- Create tickets for all action items
- Assign owners and due dates
- Track in weekly team meetings
- Review in next post-mortem

### Runbook Updates

- Update runbook with new procedures learned
- Add new scenarios if encountered
- Update troubleshooting steps
- Share updates with team

---

**Document Version**: 1.0.0  
**Last Review**: 2024  
**Next Review**: Quarterly  
**Owner**: Operations Team
