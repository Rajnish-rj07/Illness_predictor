# Illness Prediction System - Monitoring and Alerting Guide

**Version**: 1.0.0  
**Last Updated**: 2024  
**Owner**: Operations Team

## Table of Contents

1. [Overview](#overview)
2. [Monitoring Stack](#monitoring-stack)
3. [Key Metrics](#key-metrics)
4. [Dashboards](#dashboards)
5. [Alert Rules](#alert-rules)
6. [Alert Response](#alert-response)
7. [Maintenance](#maintenance)

---

## Overview

This guide provides comprehensive information about monitoring and alerting for the Illness Prediction System, including metrics collection, dashboard usage, alert configuration, and response procedures.

### Monitoring Philosophy

- **Proactive**: Detect issues before users report them
- **Actionable**: Every alert should have a clear response
- **Comprehensive**: Monitor all layers (application, infrastructure, business)
- **Efficient**: Minimize false positives and alert fatigue

### Monitoring Layers

```
┌─────────────────────────────────────────────────────────┐
│                    Business Metrics                      │
│  (Predictions/sec, Accuracy, User Satisfaction)         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                 Application Metrics                      │
│  (Latency, Error Rate, Throughput, Model Performance)   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Infrastructure Metrics                      │
│  (CPU, Memory, Disk, Network, Database)                 │
└─────────────────────────────────────────────────────────┘
```

---

## Monitoring Stack

### Components

| Component | Purpose | Port | URL |
|-----------|---------|------|-----|
| **Prometheus** | Metrics collection and storage | 9090 | http://prometheus.example.com |
| **Grafana** | Visualization and dashboards | 3000 | http://grafana.example.com |
| **Alertmanager** | Alert routing and notifications | 9093 | http://alertmanager.example.com |
| **Node Exporter** | Host metrics | 9100 | - |
| **Postgres Exporter** | Database metrics | 9187 | - |
| **Redis Exporter** | Cache metrics | 9121 | - |

### Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Application  │────▶│  Prometheus  │────▶│   Grafana    │
│  /metrics    │     │   (Scrape)   │     │ (Visualize)  │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                            │ Evaluate Rules
                            ▼
                     ┌──────────────┐
                     │ Alertmanager │
                     │   (Route)    │
                     └──────┬───────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
    ┌────────┐         ┌────────┐        ┌────────┐
    │ Email  │         │ Slack  │        │PagerDuty│
    └────────┘         └────────┘        └────────┘
```

### Metrics Endpoints

| Service | Endpoint | Metrics |
|---------|----------|---------|
| Application | `/metrics` | HTTP requests, latency, predictions, model metrics |
| PostgreSQL | `:9187/metrics` | Connections, queries, locks, replication |
| Redis | `:9121/metrics` | Commands, memory, keys, hit rate |
| Node | `:9100/metrics` | CPU, memory, disk, network |

---

## Key Metrics

### Application Metrics

#### HTTP Metrics

**Request Rate**:
```promql
# Total requests per second
rate(http_requests_total[5m])

# Requests per second by endpoint
rate(http_requests_total[5m]) by (endpoint)

# Requests per second by status code
rate(http_requests_total[5m]) by (status)
```

**Error Rate**:
```promql
# Error rate (5xx errors)
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# Error rate by endpoint
rate(http_requests_total{status=~"5.."}[5m]) by (endpoint) / rate(http_requests_total[5m]) by (endpoint)
```

**Latency**:
```promql
# P50 latency
histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# P99 latency
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# Average latency by endpoint
rate(http_request_duration_seconds_sum[5m]) by (endpoint) / rate(http_request_duration_seconds_count[5m]) by (endpoint)
```

#### Prediction Metrics

**Prediction Rate**:
```promql
# Predictions per second
rate(predictions_total[5m])

# Predictions by illness
rate(predictions_total[5m]) by (illness)
```

**Prediction Confidence**:
```promql
# Average confidence score
rate(prediction_confidence_sum[5m]) / rate(prediction_confidence_count[5m])

# Confidence distribution
histogram_quantile(0.50, rate(prediction_confidence_bucket[5m]))
histogram_quantile(0.95, rate(prediction_confidence_bucket[5m]))
```

**Model Performance**:
```promql
# Model accuracy (from feedback)
rate(predictions_correct_total[24h]) / rate(predictions_with_feedback_total[24h])

# Accuracy by illness
rate(predictions_correct_total[24h]) by (illness) / rate(predictions_with_feedback_total[24h]) by (illness)

# Model inference time
histogram_quantile(0.95, rate(model_inference_duration_seconds_bucket[5m]))
```

#### Session Metrics

**Active Sessions**:
```promql
# Current active sessions
active_sessions

# Sessions created per minute
rate(sessions_created_total[1m])

# Session duration
histogram_quantile(0.95, rate(session_duration_seconds_bucket[5m]))
```

**Question Metrics**:
```promql
# Average questions per session
rate(questions_asked_total[5m]) / rate(sessions_completed_total[5m])

# Questions per second
rate(questions_asked_total[5m])
```

#### Drift Metrics

**Feature Drift**:
```promql
# PSI score by feature
feature_drift_psi by (feature)

# Number of drifting features
count(feature_drift_psi > 0.1)

# Maximum PSI score
max(feature_drift_psi)
```

**Concept Drift**:
```promql
# Accuracy trend (7-day window)
rate(predictions_correct_total[7d]) / rate(predictions_with_feedback_total[7d])

# Accuracy change
(rate(predictions_correct_total[1d]) / rate(predictions_with_feedback_total[1d])) - 
(rate(predictions_correct_total[7d]) / rate(predictions_with_feedback_total[7d]))
```

### Infrastructure Metrics

#### CPU and Memory

**CPU Usage**:
```promql
# CPU usage by pod
rate(container_cpu_usage_seconds_total[5m]) by (pod)

# CPU usage percentage
100 * rate(container_cpu_usage_seconds_total[5m]) / container_spec_cpu_quota * container_spec_cpu_period
```

**Memory Usage**:
```promql
# Memory usage by pod
container_memory_usage_bytes by (pod)

# Memory usage percentage
100 * container_memory_usage_bytes / container_spec_memory_limit_bytes
```

#### Database Metrics

**Connections**:
```promql
# Active connections
pg_stat_activity_count

# Connection pool usage
pg_stat_database_numbackends / pg_settings_max_connections
```

**Query Performance**:
```promql
# Slow queries (> 1 second)
pg_stat_statements_mean_time_seconds > 1

# Query rate
rate(pg_stat_database_xact_commit[5m])
```

**Locks**:
```promql
# Lock waits
pg_locks_count by (mode)

# Deadlocks
rate(pg_stat_database_deadlocks[5m])
```

#### Redis Metrics

**Memory**:
```promql
# Memory usage
redis_memory_used_bytes

# Memory fragmentation
redis_memory_fragmentation_ratio
```

**Cache Performance**:
```promql
# Hit rate
rate(redis_keyspace_hits_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))

# Commands per second
rate(redis_commands_processed_total[5m])
```

---

## Dashboards

### 1. System Health Dashboard

**URL**: http://grafana.example.com/d/system-health

**Panels**:

1. **Overview**:
   - System status (UP/DOWN)
   - Active alerts count
   - Request rate
   - Error rate
   - P95 latency

2. **HTTP Metrics**:
   - Requests per second (by endpoint)
   - Error rate (by status code)
   - Latency percentiles (P50, P95, P99)
   - Status code distribution

3. **Resource Usage**:
   - CPU usage (by pod)
   - Memory usage (by pod)
   - Disk usage
   - Network I/O

4. **Dependencies**:
   - Database connection pool
   - Redis cache hit rate
   - External API latency
   - External API error rate

**Usage**:
- Check every 15 minutes during business hours
- Review before and after deployments
- Use for incident investigation

### 2. Prediction Monitoring Dashboard

**URL**: http://grafana.example.com/d/prediction-monitoring

**Panels**:

1. **Prediction Volume**:
   - Predictions per second
   - Predictions per hour (trend)
   - Top 10 predicted illnesses
   - Predictions by channel (SMS, WhatsApp, Web)

2. **Prediction Quality**:
   - Average confidence score
   - Confidence distribution
   - Low confidence predictions (< 30%)
   - High confidence predictions (> 80%)

3. **Session Metrics**:
   - Active sessions
   - Sessions created per minute
   - Average questions per session
   - Session completion rate

4. **Feedback**:
   - Feedback rate
   - Feedback sentiment
   - Correct predictions percentage
   - Incorrect predictions (flagged)

**Usage**:
- Monitor prediction quality hourly
- Review feedback daily
- Identify prediction patterns

### 3. Model Performance Dashboard

**URL**: http://grafana.example.com/d/model-performance

**Panels**:

1. **Accuracy Metrics**:
   - Overall accuracy (24h, 7d, 30d)
   - Accuracy trend (7-day moving average)
   - Per-illness accuracy (top 20)
   - Accuracy by confidence bucket

2. **Model Metrics**:
   - Precision, Recall, F1 Score
   - Confusion matrix heatmap
   - Top-3 accuracy
   - Model version in use

3. **Inference Performance**:
   - Model inference time (P95, P99)
   - Model load time
   - Feature extraction time
   - SHAP computation time

4. **Training History**:
   - Training runs (last 30 days)
   - Training duration
   - Validation metrics
   - Model size

**Usage**:
- Review daily for accuracy trends
- Check after model deployments
- Use for model comparison

### 4. Drift Detection Dashboard

**URL**: http://grafana.example.com/d/drift-detection

**Panels**:

1. **Feature Drift**:
   - PSI scores (by feature)
   - Drifting features count
   - Feature distribution comparison
   - KS test statistics

2. **Concept Drift**:
   - Accuracy over time (7-day window)
   - Accuracy change rate
   - Prediction distribution shift
   - Confidence score trend

3. **Drift Events**:
   - Drift events timeline
   - Drift type distribution
   - Retraining recommendations
   - Model staleness

4. **Data Quality**:
   - Missing values rate
   - Outlier frequency
   - Feature correlation changes
   - Data volume trend

**Usage**:
- Review daily for drift signals
- Check before retraining
- Monitor after data source changes

---

## Alert Rules

### Critical Alerts (P1)

#### API Down

**Rule**:
```yaml
- alert: APIDown
  expr: up{job="illness-prediction-app"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "API is down"
    description: "The illness prediction API has been down for more than 1 minute."
```

**Response**: See [Incident Response Playbook](./INCIDENT_RESPONSE_PLAYBOOK.md#scenario-1-complete-api-outage-p1)

#### High Error Rate

**Rule**:
```yaml
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.01
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High error rate detected"
    description: "Error rate is {{ $value | humanizePercentage }} (threshold: 1%)"
```

**Response**: See [Incident Response Playbook](./INCIDENT_RESPONSE_PLAYBOOK.md#scenario-2-high-error-rate-p2)

#### Model Accuracy Degradation

**Rule**:
```yaml
- alert: ModelAccuracyDegradation
  expr: |
    (rate(predictions_correct_total[24h]) / rate(predictions_with_feedback_total[24h])) < 0.80
  for: 1h
  labels:
    severity: critical
  annotations:
    summary: "Model accuracy has degraded significantly"
    description: "Model accuracy is {{ $value | humanizePercentage }} (threshold: 85%)"
```

**Response**: See [Incident Response Playbook](./INCIDENT_RESPONSE_PLAYBOOK.md#scenario-4-model-accuracy-degradation-p2)

#### Database Unavailable

**Rule**:
```yaml
- alert: DatabaseUnavailable
  expr: up{job="postgres"} == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Database is unavailable"
    description: "PostgreSQL database has been down for more than 1 minute."
```

**Response**: See [Incident Response Playbook](./INCIDENT_RESPONSE_PLAYBOOK.md#scenario-5-database-unavailable-p1)

#### Significant Feature Drift

**Rule**:
```yaml
- alert: SignificantFeatureDrift
  expr: max(feature_drift_psi) > 0.25
  for: 30m
  labels:
    severity: critical
  annotations:
    summary: "Significant feature drift detected"
    description: "Maximum PSI score is {{ $value }} (threshold: 0.25)"
```

**Response**: See [Alert Response](#drift-detection-alert)

### Warning Alerts (P2)

#### Elevated Error Rate

**Rule**:
```yaml
- alert: ElevatedErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.005
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Elevated error rate"
    description: "Error rate is {{ $value | humanizePercentage }} (threshold: 0.5%)"
```

#### High Prediction Latency

**Rule**:
```yaml
- alert: HighPredictionLatency
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{endpoint="/predict"}[5m])) > 0.5
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High prediction latency"
    description: "P95 latency is {{ $value }}s (threshold: 500ms)"
```

#### Low Cache Hit Rate

**Rule**:
```yaml
- alert: LowCacheHitRate
  expr: |
    rate(redis_keyspace_hits_total[5m]) / 
    (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m])) < 0.70
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Low Redis cache hit rate"
    description: "Cache hit rate is {{ $value | humanizePercentage }} (threshold: 70%)"
```

#### High CPU Usage

**Rule**:
```yaml
- alert: HighCPUUsage
  expr: |
    100 * rate(container_cpu_usage_seconds_total[5m]) / 
    (container_spec_cpu_quota / container_spec_cpu_period) > 80
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "High CPU usage on {{ $labels.pod }}"
    description: "CPU usage is {{ $value }}% (threshold: 80%)"
```

#### High Memory Usage

**Rule**:
```yaml
- alert: HighMemoryUsage
  expr: |
    100 * container_memory_usage_bytes / container_spec_memory_limit_bytes > 80
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "High memory usage on {{ $labels.pod }}"
    description: "Memory usage is {{ $value }}% (threshold: 80%)"
```

#### Moderate Feature Drift

**Rule**:
```yaml
- alert: ModerateFeatureDrift
  expr: max(feature_drift_psi) > 0.10
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: "Moderate feature drift detected"
    description: "Maximum PSI score is {{ $value }} (threshold: 0.10)"
```

### Info Alerts (P3)

#### Model Not Retrained

**Rule**:
```yaml
- alert: ModelIsStale
  expr: time() - model_last_trained_timestamp > 1209600  # 14 days
  for: 1h
  labels:
    severity: info
  annotations:
    summary: "Model has not been retrained recently"
    description: "Model was last trained {{ $value | humanizeDuration }} ago"
```

#### Low Feedback Rate

**Rule**:
```yaml
- alert: LowFeedbackRate
  expr: |
    rate(feedback_received_total[24h]) / rate(predictions_total[24h]) < 0.10
  for: 6h
  labels:
    severity: info
  annotations:
    summary: "Low user feedback rate"
    description: "Feedback rate is {{ $value | humanizePercentage }} (threshold: 10%)"
```

---

## Alert Response

### Alert Acknowledgment

**PagerDuty**:
1. Click "Acknowledge" in PagerDuty app
2. Or reply "ack" to PagerDuty SMS
3. Or call PagerDuty number and press 4

**Slack**:
1. React with 👀 emoji to alert
2. Post "Acknowledged" in thread

### Alert Investigation

**Step 1: Verify Alert**
```bash
# Check Prometheus
curl "http://prometheus:9090/api/v1/query?query=<alert_query>"

# Check Grafana dashboard
# Open relevant dashboard and verify metrics
```

**Step 2: Gather Context**
```bash
# Check recent changes
kubectl rollout history deployment/illness-prediction-app -n illness-prediction

# Check logs
kubectl logs -f deployment/illness-prediction-app -n illness-prediction --tail=100

# Check pod status
kubectl get pods -n illness-prediction
```

**Step 3: Assess Impact**
- How many users affected?
- What functionality is impacted?
- Is data at risk?
- What is the severity?

### Alert Resolution

**Step 1: Implement Fix**
- See [Incident Response Playbook](./INCIDENT_RESPONSE_PLAYBOOK.md) for specific scenarios

**Step 2: Verify Resolution**
```bash
# Check metrics returned to normal
curl "http://prometheus:9090/api/v1/query?query=<alert_query>"

# Check logs for errors
kubectl logs deployment/illness-prediction-app -n illness-prediction --tail=100 | grep ERROR

# Test functionality
curl https://illness-prediction.example.com/health
```

**Step 3: Close Alert**
- PagerDuty: Click "Resolve"
- Slack: Post "Resolved" with summary
- Update incident channel

### Alert Tuning

**If False Positive**:
1. Document why it's false positive
2. Adjust threshold or duration
3. Update alert rule
4. Test new rule

**If Missing Alert**:
1. Document what should have alerted
2. Create new alert rule
3. Test alert rule
4. Deploy to production

---

## Maintenance

### Daily Tasks

- [ ] Review System Health dashboard
- [ ] Check for active alerts
- [ ] Review error logs
- [ ] Check Model Performance dashboard
- [ ] Review Drift Detection dashboard

### Weekly Tasks

- [ ] Review alert history
- [ ] Tune alert thresholds
- [ ] Update dashboards
- [ ] Review capacity trends
- [ ] Check backup status

### Monthly Tasks

- [ ] Review SLO compliance
- [ ] Analyze incident trends
- [ ] Update runbooks
- [ ] Review monitoring coverage
- [ ] Capacity planning

### Quarterly Tasks

- [ ] Review monitoring strategy
- [ ] Update alert rules
- [ ] Dashboard cleanup
- [ ] Monitoring stack upgrades
- [ ] Team training

### Dashboard Maintenance

**Adding New Panel**:
1. Edit dashboard in Grafana
2. Add panel with query
3. Configure visualization
4. Save dashboard
5. Export JSON
6. Commit to repository

**Updating Panel**:
1. Edit panel in Grafana
2. Update query or visualization
3. Save dashboard
4. Export JSON
5. Commit to repository

### Alert Rule Maintenance

**Adding New Alert**:
1. Write alert rule in YAML
2. Test rule in Prometheus
3. Add to alert rules file
4. Apply to Prometheus
5. Test alert fires correctly
6. Document in runbook

**Updating Alert**:
1. Edit alert rule
2. Test new threshold
3. Apply to Prometheus
4. Monitor for false positives
5. Update runbook

### Prometheus Maintenance

**Data Retention**:
```yaml
# prometheus.yml
storage:
  tsdb:
    retention.time: 30d
    retention.size: 50GB
```

**Backup**:
```bash
# Backup Prometheus data
kubectl exec -n monitoring deployment/prometheus -- \
  tar czf /tmp/prometheus-backup.tar.gz /prometheus

kubectl cp monitoring/prometheus-pod:/tmp/prometheus-backup.tar.gz \
  ./prometheus-backup-$(date +%Y%m%d).tar.gz
```

**Restore**:
```bash
# Restore Prometheus data
kubectl cp ./prometheus-backup-20240101.tar.gz \
  monitoring/prometheus-pod:/tmp/prometheus-backup.tar.gz

kubectl exec -n monitoring deployment/prometheus -- \
  tar xzf /tmp/prometheus-backup.tar.gz -C /
```

### Grafana Maintenance

**Dashboard Backup**:
```bash
# Export all dashboards
for dashboard in $(curl -s http://grafana:3000/api/search | jq -r '.[].uid'); do
  curl -s http://grafana:3000/api/dashboards/uid/$dashboard | \
    jq '.dashboard' > dashboard-$dashboard.json
done
```

**Dashboard Restore**:
```bash
# Import dashboard
curl -X POST http://grafana:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @dashboard.json
```

---

**Document Version**: 1.0.0  
**Last Review**: 2024  
**Next Review**: Quarterly  
**Owner**: Operations Team
