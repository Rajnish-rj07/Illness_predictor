# Illness Prediction System - Deployment Guide

**Version**: 1.0.0  
**Last Updated**: 2024  
**Audience**: DevOps Engineers, SREs

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Environment Setup](#environment-setup)
4. [Initial Deployment](#initial-deployment)
5. [Deployment Strategies](#deployment-strategies)
6. [Configuration Management](#configuration-management)
7. [Database Management](#database-management)
8. [Model Deployment](#model-deployment)
9. [Monitoring Setup](#monitoring-setup)
10. [Troubleshooting](#troubleshooting)

---

## Overview

This guide provides comprehensive instructions for deploying the Illness Prediction System to various environments (development, staging, production).

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Repository                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Push/Tag
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  GitHub Actions CI/CD                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Build   │→ │   Test   │→ │  Deploy  │→ │  Verify  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
    ┌────────┐  ┌────────┐  ┌────────┐
    │  Dev   │  │Staging │  │  Prod  │
    └────────┘  └────────┘  └────────┘
```

### Deployment Environments

| Environment | Purpose | Auto-Deploy | Approval Required |
|-------------|---------|-------------|-------------------|
| Development | Feature testing | Yes (on push to dev branch) | No |
| Staging | Pre-production testing | Yes (on push to main) | No |
| Production | Live system | Yes (on tag) | Yes (manual approval) |

---

## Prerequisites

### Required Tools

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install kustomize
curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
sudo mv kustomize /usr/local/bin/

# Install Python 3.11+
sudo apt-get update
sudo apt-get install python3.11 python3.11-venv python3-pip
```

### Access Requirements

- [ ] Kubernetes cluster access (kubeconfig)
- [ ] Container registry credentials (GitHub Container Registry)
- [ ] Cloud provider credentials (AWS/GCP/Azure)
- [ ] Database credentials
- [ ] API keys (OpenAI, Twilio, etc.)
- [ ] GitHub repository access
- [ ] Monitoring tools access (Grafana, Prometheus)

### Cluster Requirements

**Minimum Resources**:
- **Nodes**: 3 worker nodes
- **CPU**: 8 cores per node
- **Memory**: 16 GB per node
- **Storage**: 100 GB per node
- **Kubernetes Version**: 1.24+

**Recommended Resources** (Production):
- **Nodes**: 5-10 worker nodes
- **CPU**: 16 cores per node
- **Memory**: 32 GB per node
- **Storage**: 200 GB per node

---

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/org/illness-prediction-system.git
cd illness-prediction-system
```

### 2. Configure kubectl

```bash
# Set up kubeconfig for your environment
export KUBECONFIG=~/.kube/config-production

# Verify connection
kubectl cluster-info
kubectl get nodes
```

### 3. Create Namespace

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Verify
kubectl get namespace illness-prediction
```

### 4. Set Up Secrets

```bash
# Generate encryption key
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Generate JWT secret
export JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Create secrets
kubectl create secret generic illness-prediction-secrets \
  --from-literal=POSTGRES_PASSWORD='your_secure_password' \
  --from-literal=REDIS_PASSWORD='your_redis_password' \
  --from-literal=ENCRYPTION_KEY="$ENCRYPTION_KEY" \
  --from-literal=JWT_SECRET_KEY="$JWT_SECRET" \
  --from-literal=LLM_API_KEY='your_openai_key' \
  --from-literal=TWILIO_ACCOUNT_SID='your_twilio_sid' \
  --from-literal=TWILIO_AUTH_TOKEN='your_twilio_token' \
  --from-literal=GOOGLE_PLACES_API_KEY='your_places_key' \
  --from-literal=TRANSLATION_API_KEY='your_translation_key' \
  -n illness-prediction

# Verify (values should be base64 encoded)
kubectl get secret illness-prediction-secrets -n illness-prediction -o yaml
```

### 5. Configure ConfigMap

```bash
# Edit configmap with environment-specific values
kubectl apply -f k8s/configmap.yaml -n illness-prediction

# Verify
kubectl get configmap illness-prediction-config -n illness-prediction -o yaml
```

### 6. Set Up Persistent Storage

```bash
# Create storage class (if not exists)
kubectl apply -f k8s/storage-class.yaml

# Create persistent volumes
kubectl apply -f k8s/postgres-pv.yaml
kubectl apply -f k8s/redis-pv.yaml
kubectl apply -f k8s/models-pv.yaml

# Verify
kubectl get pv
kubectl get pvc -n illness-prediction
```

---

## Initial Deployment

### Method 1: Using Kustomize (Recommended)

```bash
# Deploy to staging
kubectl apply -k k8s/overlays/staging/

# Verify deployment
kubectl get all -n illness-prediction

# Check pod status
kubectl get pods -n illness-prediction -w

# Check logs
kubectl logs -f deployment/illness-prediction-app -n illness-prediction
```

### Method 2: Using kubectl

```bash
# Deploy in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml -n illness-prediction
kubectl apply -f k8s/secrets.yaml -n illness-prediction
kubectl apply -f k8s/postgres-deployment.yaml -n illness-prediction
kubectl apply -f k8s/redis-deployment.yaml -n illness-prediction
kubectl apply -f k8s/app-deployment.yaml -n illness-prediction
kubectl apply -f k8s/ingress.yaml -n illness-prediction
kubectl apply -f k8s/network-policy.yaml -n illness-prediction
kubectl apply -f k8s/service-monitor.yaml -n illness-prediction

# Wait for all pods to be ready
kubectl wait --for=condition=ready pod -l app=illness-prediction-app -n illness-prediction --timeout=300s
```

### Method 3: Using Deployment Script

```bash
# Make script executable
chmod +x scripts/deploy.sh

# Deploy to staging
./scripts/deploy.sh staging v1.0.0

# Deploy to production
./scripts/deploy.sh production v1.0.0
```

### Verify Deployment

```bash
# Check all resources
kubectl get all -n illness-prediction

# Check pod status
kubectl get pods -n illness-prediction
# All pods should be Running with READY 1/1

# Check services
kubectl get svc -n illness-prediction

# Check ingress
kubectl get ingress -n illness-prediction

# Test health endpoint
kubectl port-forward -n illness-prediction service/illness-prediction-service 8080:80 &
curl http://localhost:8080/health
# Expected: {"status": "healthy", "version": "v1.0.0"}

# Test API endpoint
curl http://localhost:8080/api/v1/health
# Expected: {"status": "ok", "database": "connected", "redis": "connected"}
```

---

## Deployment Strategies

### 1. Rolling Update (Default)

**Use Case**: Standard updates, low risk changes

**Configuration**:
```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

**Process**:
```bash
# Update image
kubectl set image deployment/illness-prediction-app \
  app=ghcr.io/org/illness-prediction:v1.1.0 \
  -n illness-prediction

# Monitor rollout
kubectl rollout status deployment/illness-prediction-app -n illness-prediction

# Pause rollout if issues
kubectl rollout pause deployment/illness-prediction-app -n illness-prediction

# Resume rollout
kubectl rollout resume deployment/illness-prediction-app -n illness-prediction
```

**Advantages**:
- Zero downtime
- Gradual rollout
- Easy to pause/resume

**Disadvantages**:
- Slower than recreate
- Mixed versions during rollout

### 2. Blue-Green Deployment

**Use Case**: Major updates, need instant rollback

**Process**:
```bash
# 1. Deploy green (new version) alongside blue (current)
kubectl apply -f k8s/app-deployment-green.yaml -n illness-prediction

# 2. Wait for green to be ready
kubectl wait --for=condition=ready pod -l app=illness-prediction-app,version=green -n illness-prediction

# 3. Test green deployment
kubectl port-forward -n illness-prediction service/illness-prediction-service-green 8081:80 &
curl http://localhost:8081/health

# 4. Switch traffic to green
kubectl patch service illness-prediction-service -n illness-prediction \
  -p '{"spec":{"selector":{"version":"green"}}}'

# 5. Monitor for 10 minutes

# 6. If successful, delete blue
kubectl delete deployment illness-prediction-app-blue -n illness-prediction

# 7. If issues, rollback to blue
kubectl patch service illness-prediction-service -n illness-prediction \
  -p '{"spec":{"selector":{"version":"blue"}}}'
```

**Advantages**:
- Instant rollback
- Full testing before switch
- No mixed versions

**Disadvantages**:
- Requires 2x resources
- More complex setup

### 3. Canary Deployment

**Use Case**: High-risk changes, gradual validation

**Process**:
```bash
# 1. Deploy canary (10% traffic)
kubectl apply -f k8s/canary-deployment.yaml -n illness-prediction

# 2. Configure traffic split (using Istio/Linkerd)
kubectl apply -f k8s/virtual-service-canary-10.yaml -n illness-prediction

# 3. Monitor canary metrics for 10 minutes
# - Error rate
# - Latency
# - Success rate

# 4. If metrics good, increase to 50%
kubectl apply -f k8s/virtual-service-canary-50.yaml -n illness-prediction

# 5. Monitor for another 10 minutes

# 6. If still good, promote to 100%
kubectl set image deployment/illness-prediction-app \
  app=ghcr.io/org/illness-prediction:v1.1.0 \
  -n illness-prediction

# 7. Clean up canary
kubectl delete deployment illness-prediction-app-canary -n illness-prediction
```

**Advantages**:
- Gradual risk mitigation
- Real user validation
- Easy to abort

**Disadvantages**:
- Requires service mesh
- Longer deployment time
- More complex monitoring

### 4. Recreate Deployment

**Use Case**: Development environment, database migrations

**Configuration**:
```yaml
spec:
  strategy:
    type: Recreate
```

**Process**:
```bash
# Update deployment
kubectl apply -f k8s/app-deployment.yaml -n illness-prediction

# All old pods terminated before new ones created
```

**Advantages**:
- Simple
- No mixed versions
- Good for stateful apps

**Disadvantages**:
- Downtime during deployment
- Not suitable for production

---

## Configuration Management

### Environment-Specific Configuration

**Directory Structure**:
```
k8s/
├── base/
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   └── configmap.yaml
└── overlays/
    ├── development/
    │   ├── kustomization.yaml
    │   ├── configmap-patch.yaml
    │   └── deployment-patch.yaml
    ├── staging/
    │   ├── kustomization.yaml
    │   ├── configmap-patch.yaml
    │   └── deployment-patch.yaml
    └── production/
        ├── kustomization.yaml
        ├── configmap-patch.yaml
        └── deployment-patch.yaml
```

**Development Configuration**:
```yaml
# k8s/overlays/development/configmap-patch.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: illness-prediction-config
data:
  LOG_LEVEL: "DEBUG"
  ENVIRONMENT: "development"
  MAX_QUESTIONS_PER_SESSION: "15"
  ENABLE_PROFILING: "true"
```

**Staging Configuration**:
```yaml
# k8s/overlays/staging/configmap-patch.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: illness-prediction-config
data:
  LOG_LEVEL: "INFO"
  ENVIRONMENT: "staging"
  MAX_QUESTIONS_PER_SESSION: "15"
  ENABLE_PROFILING: "false"
```

**Production Configuration**:
```yaml
# k8s/overlays/production/configmap-patch.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: illness-prediction-config
data:
  LOG_LEVEL: "WARNING"
  ENVIRONMENT: "production"
  MAX_QUESTIONS_PER_SESSION: "15"
  ENABLE_PROFILING: "false"
  RATE_LIMIT_ENABLED: "true"
```

### Updating Configuration

```bash
# Update ConfigMap
kubectl edit configmap illness-prediction-config -n illness-prediction

# Or apply new version
kubectl apply -f k8s/configmap.yaml -n illness-prediction

# Restart pods to pick up changes
kubectl rollout restart deployment/illness-prediction-app -n illness-prediction

# Verify
kubectl rollout status deployment/illness-prediction-app -n illness-prediction
```

### Managing Secrets

```bash
# Update secret
kubectl create secret generic illness-prediction-secrets \
  --from-literal=NEW_KEY='new_value' \
  -n illness-prediction \
  --dry-run=client -o yaml | kubectl apply -f -

# Or use external secret management
# AWS Secrets Manager
kubectl apply -f k8s/external-secret-aws.yaml

# HashiCorp Vault
kubectl apply -f k8s/external-secret-vault.yaml

# Restart to pick up changes
kubectl rollout restart deployment/illness-prediction-app -n illness-prediction
```

---

## Database Management

### Initial Database Setup

```bash
# 1. Deploy PostgreSQL
kubectl apply -f k8s/postgres-deployment.yaml -n illness-prediction

# 2. Wait for pod to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n illness-prediction

# 3. Initialize database
kubectl exec -n illness-prediction deployment/postgres -- \
  psql -U illness_prediction -d postgres -c "CREATE DATABASE illness_prediction;"

# 4. Run migrations
kubectl exec -n illness-prediction deployment/illness-prediction-app -- \
  alembic upgrade head

# 5. Verify
kubectl exec -n illness-prediction deployment/postgres -- \
  psql -U illness_prediction -d illness_prediction -c "\dt"
```

### Database Migrations

```bash
# Create new migration
kubectl exec -n illness-prediction deployment/illness-prediction-app -- \
  alembic revision --autogenerate -m "Add new table"

# Apply migration
kubectl exec -n illness-prediction deployment/illness-prediction-app -- \
  alembic upgrade head

# Rollback migration
kubectl exec -n illness-prediction deployment/illness-prediction-app -- \
  alembic downgrade -1

# Check migration history
kubectl exec -n illness-prediction deployment/illness-prediction-app -- \
  alembic history
```

### Database Backup

```bash
# Manual backup
kubectl exec -n illness-prediction deployment/postgres -- \
  pg_dump -U illness_prediction illness_prediction > backup-$(date +%Y%m%d-%H%M%S).sql

# Automated backup (CronJob)
kubectl apply -f k8s/backup-cronjob.yaml -n illness-prediction

# Verify backup
kubectl get cronjob -n illness-prediction
kubectl get jobs -n illness-prediction
```

### Database Restore

```bash
# Restore from backup
kubectl exec -i -n illness-prediction deployment/postgres -- \
  psql -U illness_prediction -d illness_prediction < backup-20240101-120000.sql

# Or copy file to pod first
kubectl cp backup-20240101-120000.sql \
  illness-prediction/postgres-pod:/tmp/backup.sql

kubectl exec -n illness-prediction deployment/postgres -- \
  psql -U illness_prediction -d illness_prediction -f /tmp/backup.sql
```

---

## Model Deployment

### Initial Model Setup

```bash
# 1. Train initial model
python src/mlops/training_pipeline.py --config config/training_config.yaml

# 2. Register model in MLflow
python scripts/register_model.py --model-path models/model.pkl --version v1.0.0

# 3. Deploy model to Kubernetes
kubectl create configmap model-config \
  --from-file=model_version=v1.0.0 \
  -n illness-prediction

# 4. Mount model volume
kubectl apply -f k8s/model-pvc.yaml -n illness-prediction

# 5. Copy model to volume
kubectl cp models/model.pkl \
  illness-prediction/illness-prediction-app-pod:/models/model.pkl

# 6. Restart application
kubectl rollout restart deployment/illness-prediction-app -n illness-prediction
```

### Model Update

```bash
# 1. Train new model
python src/mlops/training_pipeline.py --config config/training_config.yaml

# 2. Register in MLflow
python scripts/register_model.py --model-path models/model_v2.pkl --version v2.0.0

# 3. Deploy to staging
kubectl set env deployment/illness-prediction-app \
  MODEL_VERSION=v2.0.0 \
  -n illness-prediction-staging

# 4. Test in staging
pytest tests/test_model_integration.py --env=staging

# 5. Deploy to production (canary)
# See Canary Deployment section

# 6. Monitor model performance
# Check Model Performance dashboard in Grafana
```

### Model Rollback

```bash
# 1. Update model version
kubectl set env deployment/illness-prediction-app \
  MODEL_VERSION=v1.0.0 \
  -n illness-prediction

# 2. Restart application
kubectl rollout restart deployment/illness-prediction-app -n illness-prediction

# 3. Verify
kubectl exec -n illness-prediction deployment/illness-prediction-app -- \
  python -c "from src.mlops.ml_model_service import MLModelService; print(MLModelService().get_active_model())"
```

---

## Monitoring Setup

### Install Monitoring Stack

```bash
# 1. Deploy Prometheus
kubectl apply -f config/monitoring/prometheus/deployment.yaml

# 2. Deploy Grafana
kubectl apply -f config/monitoring/grafana/deployment.yaml

# 3. Deploy Alertmanager
kubectl apply -f config/monitoring/alertmanager/deployment.yaml

# 4. Configure ServiceMonitor
kubectl apply -f k8s/service-monitor.yaml -n illness-prediction

# 5. Import Grafana dashboards
kubectl apply -f config/monitoring/grafana/dashboards/ -n monitoring

# 6. Configure alerts
kubectl apply -f config/monitoring/prometheus/alerts/ -n monitoring
```

### Verify Monitoring

```bash
# Check Prometheus targets
kubectl port-forward -n monitoring service/prometheus 9090:9090 &
curl http://localhost:9090/api/v1/targets

# Access Grafana
kubectl port-forward -n monitoring service/grafana 3000:3000 &
# Open http://localhost:3000 (admin/admin)

# Test alert
kubectl apply -f config/monitoring/test-alert.yaml
```

---

## Troubleshooting

### Common Deployment Issues

#### Issue: ImagePullBackOff

```bash
# Check image name and tag
kubectl describe pod/illness-prediction-app-xxx -n illness-prediction | grep Image

# Check image pull secret
kubectl get secret -n illness-prediction | grep regcred

# Create image pull secret if missing
kubectl create secret docker-registry regcred \
  --docker-server=ghcr.io \
  --docker-username=your-username \
  --docker-password=your-token \
  -n illness-prediction
```

#### Issue: CrashLoopBackOff

```bash
# Check logs
kubectl logs pod/illness-prediction-app-xxx -n illness-prediction --previous

# Common causes:
# 1. Missing environment variables
kubectl describe pod/illness-prediction-app-xxx -n illness-prediction | grep -A 10 Environment

# 2. Database connection failure
kubectl exec -n illness-prediction deployment/postgres -- pg_isready

# 3. Port conflict
kubectl describe pod/illness-prediction-app-xxx -n illness-prediction | grep Port
```

#### Issue: Pending Pods

```bash
# Check pod events
kubectl describe pod/illness-prediction-app-xxx -n illness-prediction

# Common causes:
# 1. Insufficient resources
kubectl describe nodes | grep -A 5 "Allocated resources"

# 2. PVC not bound
kubectl get pvc -n illness-prediction

# 3. Node selector mismatch
kubectl get nodes --show-labels
```

### Deployment Validation Checklist

- [ ] All pods are Running (1/1 READY)
- [ ] Services have endpoints
- [ ] Ingress has external IP
- [ ] Health endpoint returns 200
- [ ] API endpoint returns 200
- [ ] Database connection successful
- [ ] Redis connection successful
- [ ] Model loaded successfully
- [ ] Metrics endpoint accessible
- [ ] Logs show no errors
- [ ] Grafana dashboards showing data
- [ ] Alerts configured and firing (test)

---

**Document Version**: 1.0.0  
**Last Review**: 2024  
**Next Review**: Quarterly  
**Owner**: DevOps Team
