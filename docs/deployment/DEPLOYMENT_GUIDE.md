# Deployment Guide - Illness Prediction System

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Environment Setup](#environment-setup)
4. [Docker Deployment](#docker-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [CI/CD Pipeline](#cicd-pipeline)
7. [Monitoring and Observability](#monitoring-and-observability)
8. [Troubleshooting](#troubleshooting)

## Overview

The Illness Prediction System supports multiple deployment strategies:

- **Docker Compose**: Local development and testing
- **Kubernetes**: Production deployment with auto-scaling and high availability
- **CI/CD**: Automated deployment via GitHub Actions

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Ingress                              │
│                    (NGINX/Load Balancer)                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Application Pods (3-10)                    │
│                  (Auto-scaling enabled)                      │
└─────────────────────────────────────────────────────────────┘
                    │                    │
                    ▼                    ▼
        ┌──────────────────┐  ┌──────────────────┐
        │    PostgreSQL    │  │      Redis       │
        │   (Persistent)   │  │   (Persistent)   │
        └──────────────────┘  └──────────────────┘
```

## Prerequisites

### Required Tools

- **Docker**: 20.10+ ([Install](https://docs.docker.com/get-docker/))
- **Docker Compose**: 2.0+ (included with Docker Desktop)
- **Kubernetes**: 1.24+ (for production)
- **kubectl**: 1.24+ ([Install](https://kubernetes.io/docs/tasks/tools/))
- **Helm**: 3.0+ (optional, for monitoring stack)
- **Git**: 2.30+

### Optional Tools

- **kustomize**: 4.5+ (for environment-specific configs)
- **k9s**: Terminal UI for Kubernetes
- **Lens**: Desktop Kubernetes IDE

### Cloud Provider Requirements

Choose one:

- **AWS**: EKS cluster, ECR registry, RDS (optional), ElastiCache (optional)
- **GCP**: GKE cluster, GCR registry, Cloud SQL (optional), Memorystore (optional)
- **Azure**: AKS cluster, ACR registry, Azure Database (optional), Azure Cache (optional)
- **Self-hosted**: Kubernetes cluster (kubeadm, k3s, etc.)

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/illness-prediction-system.git
cd illness-prediction-system
```

### 2. Configure Environment Variables

Create environment-specific configuration files:

```bash
# Staging environment
cp .env.example .env.staging
# Edit .env.staging with staging credentials

# Production environment
cp .env.example .env.production
# Edit .env.production with production credentials
```

**Important**: Never commit `.env.*` files to version control!

### 3. Generate Secrets

Generate secure keys for encryption and JWT:

```bash
# Encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Update your `.env.*` files with these values.

## Docker Deployment

### Local Development

1. **Start services**:

```bash
docker-compose up -d
```

2. **Check status**:

```bash
docker-compose ps
```

3. **View logs**:

```bash
docker-compose logs -f app
```

4. **Access application**:

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

5. **Stop services**:

```bash
docker-compose down
```

### Production Docker Deployment

1. **Build image**:

```bash
./scripts/build-and-push.sh v1.0.0 ghcr.io/your-org
```

2. **Run with production config**:

```bash
docker run -d \
  --name illness-prediction \
  --env-file .env.production \
  -p 8000:8000 \
  ghcr.io/your-org/illness-prediction:v1.0.0
```

## Kubernetes Deployment

### Prerequisites

1. **Kubernetes cluster** running and accessible
2. **kubectl** configured with cluster credentials
3. **Container registry** accessible from cluster

### Initial Setup

#### 1. Create Namespace

```bash
kubectl create namespace illness-prediction
```

#### 2. Set Up Secrets

```bash
# Using script (recommended)
./scripts/setup-secrets.sh production

# Or manually
kubectl create secret generic illness-prediction-secrets \
  --from-literal=POSTGRES_PASSWORD=your-password \
  --from-literal=ENCRYPTION_KEY=your-key \
  --from-literal=LLM_API_KEY=your-api-key \
  --from-literal=JWT_SECRET_KEY=your-jwt-secret \
  -n illness-prediction
```

#### 3. Configure Storage

Update storage class in manifests based on your provider:

- **AWS**: `gp3` or `gp2`
- **GCP**: `standard-rwo` or `premium-rwo`
- **Azure**: `managed-premium` or `managed`

```bash
# Edit storage class in PVC manifests
sed -i 's/storageClassName: standard/storageClassName: gp3/g' k8s/*.yaml
```

### Deployment Methods

#### Method 1: Using kubectl (Simple)

```bash
# Apply all manifests
kubectl apply -f k8s/ -n illness-prediction

# Wait for deployment
kubectl wait --for=condition=available --timeout=300s \
  deployment/illness-prediction-app -n illness-prediction
```

#### Method 2: Using Kustomize (Recommended)

```bash
# Staging
kubectl apply -k k8s/overlays/staging/

# Production
kubectl apply -k k8s/overlays/production/
```

#### Method 3: Using Deployment Script

```bash
# Staging
./scripts/deploy.sh staging v1.0.0

# Production
./scripts/deploy.sh production v1.0.0
```

### Verify Deployment

```bash
# Check pods
kubectl get pods -n illness-prediction

# Check services
kubectl get services -n illness-prediction

# Check ingress
kubectl get ingress -n illness-prediction

# View logs
kubectl logs -f deployment/illness-prediction-app -n illness-prediction

# Port forward for testing
kubectl port-forward -n illness-prediction service/illness-prediction-service 8080:80
curl http://localhost:8080/health
```

### Scaling

#### Manual Scaling

```bash
# Scale to 5 replicas
kubectl scale deployment/illness-prediction-app --replicas=5 -n illness-prediction

# Or use script
./scripts/scale.sh production 5
```

#### Auto-scaling (HPA)

The HorizontalPodAutoscaler is configured automatically:

- **Min replicas**: 3
- **Max replicas**: 10
- **CPU target**: 70%
- **Memory target**: 80%

Monitor auto-scaling:

```bash
kubectl get hpa -n illness-prediction
kubectl describe hpa illness-prediction-hpa -n illness-prediction
```

### Canary Deployment

For production deployments, use canary strategy:

1. **Deploy canary**:

```bash
kubectl apply -f k8s/canary-deployment.yaml -n illness-prediction
```

2. **Update canary image**:

```bash
kubectl set image deployment/illness-prediction-app-canary \
  app=ghcr.io/your-org/illness-prediction:v1.1.0 \
  -n illness-prediction
```

3. **Monitor canary** (10% traffic for 10 minutes)

4. **Promote to 50%** (update traffic split)

5. **Promote to 100%** (update main deployment)

6. **Remove canary**:

```bash
kubectl delete deployment illness-prediction-app-canary -n illness-prediction
```

### Rollback

If deployment fails:

```bash
# Rollback to previous version
kubectl rollout undo deployment/illness-prediction-app -n illness-prediction

# Or use script
./scripts/rollback.sh production

# Rollback to specific revision
./scripts/rollback.sh production 3
```

## CI/CD Pipeline

### GitHub Actions Setup

#### 1. Configure Secrets

Add these secrets to your GitHub repository (Settings → Secrets):

**Required**:
- `KUBECONFIG_STAGING`: Base64-encoded kubeconfig for staging
- `KUBECONFIG_PRODUCTION`: Base64-encoded kubeconfig for production
- `GITHUB_TOKEN`: Automatically provided by GitHub

**Optional**:
- `SLACK_WEBHOOK`: Slack webhook URL for notifications
- `STAGING_API_KEY`: API key for staging tests
- `CODECOV_TOKEN`: Codecov token for coverage reports

#### 2. Encode Kubeconfig

```bash
# Staging
cat ~/.kube/config-staging | base64 -w 0

# Production
cat ~/.kube/config-production | base64 -w 0
```

Add the output to GitHub secrets.

#### 3. Update Workflow

Edit `.github/workflows/cd.yml`:

- Update `IMAGE_NAME` with your repository
- Update domain names
- Update Slack webhook (if using)

### Workflow Triggers

**CI Pipeline** (`.github/workflows/ci.yml`):
- Runs on: Push to `main`/`develop`, Pull Requests
- Steps: Lint → Test → Security Scan → Build

**CD Pipeline** (`.github/workflows/cd.yml`):
- Runs on: Push to `main`, Tags (`v*.*.*`)
- Steps: Build → Push → Deploy Staging → Integration Tests → Deploy Production

### Manual Deployment

Trigger manual deployment:

1. Go to **Actions** tab in GitHub
2. Select **CD - Deploy to Production**
3. Click **Run workflow**
4. Choose environment (staging/production)
5. Click **Run workflow**

### Deployment Flow

```
┌─────────────┐
│   Push to   │
│    main     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Build    │
│   & Push    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Deploy    │
│   Staging   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Integration │
│    Tests    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Deploy    │
│ Production  │
│  (Canary)   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Monitor   │
│  & Promote  │
└─────────────┘
```

## Monitoring and Observability

### Prometheus & Grafana

#### Install Monitoring Stack

```bash
# Add Prometheus Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus Operator
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace

# Apply ServiceMonitor
kubectl apply -f k8s/service-monitor.yaml
```

#### Access Grafana

```bash
# Port forward
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Default credentials
# Username: admin
# Password: prom-operator
```

#### Import Dashboards

Import pre-built dashboards from `config/monitoring/grafana/dashboards/`:

1. **Prediction Monitoring**: Real-time prediction metrics
2. **Model Performance**: Model accuracy and drift
3. **System Health**: Infrastructure metrics
4. **Drift Detection**: Data drift visualization

### Logs

#### View Application Logs

```bash
# All pods
kubectl logs -f -l app=illness-prediction -n illness-prediction

# Specific pod
kubectl logs -f <pod-name> -n illness-prediction

# Previous pod (after crash)
kubectl logs --previous <pod-name> -n illness-prediction
```

#### Centralized Logging (Optional)

Set up ELK/EFK stack:

```bash
# Install Elasticsearch, Fluentd, Kibana
helm install elasticsearch elastic/elasticsearch -n logging --create-namespace
helm install kibana elastic/kibana -n logging
helm install fluentd fluent/fluentd -n logging
```

### Alerts

Alerts are configured in `k8s/service-monitor.yaml`:

- High error rate (>1%)
- High latency (P95 >500ms)
- Model accuracy degradation (<80%)
- Data drift detected (PSI >0.25)
- Pod not ready
- High memory/CPU usage

Configure alert destinations in Alertmanager.

## Troubleshooting

### Common Issues

#### 1. Pods Not Starting

**Symptoms**: Pods in `Pending` or `CrashLoopBackOff` state

**Solutions**:

```bash
# Check pod status
kubectl describe pod <pod-name> -n illness-prediction

# Check events
kubectl get events -n illness-prediction --sort-by='.lastTimestamp'

# Check logs
kubectl logs <pod-name> -n illness-prediction
```

Common causes:
- Insufficient resources (increase limits)
- Image pull errors (check registry credentials)
- Missing secrets (verify secrets exist)
- Database connection issues (check connectivity)

#### 2. Database Connection Errors

**Symptoms**: Application logs show database connection errors

**Solutions**:

```bash
# Check PostgreSQL pod
kubectl get pods -l app=postgres -n illness-prediction

# Test connection
kubectl exec -it <postgres-pod> -n illness-prediction -- psql -U illness_pred_user -d illness_prediction

# Check service
kubectl get svc postgres-service -n illness-prediction
```

#### 3. High Latency

**Symptoms**: Slow API responses

**Solutions**:

```bash
# Check resource usage
kubectl top pods -n illness-prediction

# Scale up
./scripts/scale.sh production 10

# Check HPA
kubectl get hpa -n illness-prediction
```

#### 4. Image Pull Errors

**Symptoms**: `ImagePullBackOff` or `ErrImagePull`

**Solutions**:

```bash
# Check image exists
docker pull ghcr.io/your-org/illness-prediction:v1.0.0

# Create image pull secret
kubectl create secret docker-registry regcred \
  --docker-server=ghcr.io \
  --docker-username=<username> \
  --docker-password=<token> \
  -n illness-prediction

# Add to deployment
kubectl patch serviceaccount default \
  -p '{"imagePullSecrets": [{"name": "regcred"}]}' \
  -n illness-prediction
```

#### 5. Ingress Not Working

**Symptoms**: Cannot access application via domain

**Solutions**:

```bash
# Check ingress
kubectl get ingress -n illness-prediction
kubectl describe ingress illness-prediction-ingress -n illness-prediction

# Check ingress controller
kubectl get pods -n ingress-nginx

# Test service directly
kubectl port-forward svc/illness-prediction-service 8080:80 -n illness-prediction
curl http://localhost:8080/health
```

### Health Checks

```bash
# Application health
curl https://illness-prediction.example.com/health

# API health
curl https://illness-prediction.example.com/api/v1/health

# Metrics
curl https://illness-prediction.example.com/metrics
```

### Debug Mode

Enable debug logging:

```bash
kubectl set env deployment/illness-prediction-app \
  LOG_LEVEL=DEBUG \
  -n illness-prediction
```

### Support

For additional support:

1. Check logs: `kubectl logs -f deployment/illness-prediction-app -n illness-prediction`
2. Check events: `kubectl get events -n illness-prediction`
3. Review documentation: `docs/`
4. Open issue: GitHub Issues

## Best Practices

### Security

1. **Use secrets management**: HashiCorp Vault, AWS Secrets Manager, etc.
2. **Enable network policies**: Restrict pod-to-pod communication
3. **Use RBAC**: Limit access to Kubernetes resources
4. **Scan images**: Use Trivy, Snyk, or similar tools
5. **Enable TLS**: Use cert-manager for automatic certificate management

### Performance

1. **Resource limits**: Set appropriate CPU/memory limits
2. **Auto-scaling**: Configure HPA based on metrics
3. **Caching**: Use Redis for session and prediction caching
4. **Connection pooling**: Configure database connection pools
5. **CDN**: Use CDN for static assets

### Reliability

1. **Health checks**: Configure liveness and readiness probes
2. **Graceful shutdown**: Handle SIGTERM signals
3. **Circuit breakers**: Implement circuit breakers for external services
4. **Retries**: Use exponential backoff for retries
5. **Monitoring**: Set up comprehensive monitoring and alerting

### Cost Optimization

1. **Right-sizing**: Monitor and adjust resource requests/limits
2. **Auto-scaling**: Scale down during low traffic
3. **Spot instances**: Use spot/preemptible instances for non-critical workloads
4. **Storage optimization**: Use appropriate storage classes
5. **Resource cleanup**: Remove unused resources

## Next Steps

1. Set up monitoring dashboards
2. Configure alerting rules
3. Implement backup strategy
4. Set up disaster recovery
5. Conduct load testing
6. Review security posture
7. Optimize costs

For more information, see:
- [Operations Runbook](./OPERATIONS_RUNBOOK.md)
- [Monitoring Guide](../../config/monitoring/README.md)
- [API Documentation](../api/README.md)
