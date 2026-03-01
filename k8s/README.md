# Kubernetes Deployment Configuration

This directory contains Kubernetes manifests for deploying the Illness Prediction System.

## Directory Structure

```
k8s/
├── README.md                    # This file
├── namespace.yaml               # Namespace definition
├── configmap.yaml              # Application configuration
├── secrets.yaml                # Sensitive configuration (template)
├── postgres-deployment.yaml    # PostgreSQL database
├── redis-deployment.yaml       # Redis cache
├── app-deployment.yaml         # Main application
├── ingress.yaml                # Ingress configuration
├── network-policy.yaml         # Network policies
├── service-monitor.yaml        # Prometheus monitoring
├── canary-deployment.yaml      # Canary deployment
├── kustomization.yaml          # Kustomize base
└── overlays/
    ├── staging/
    │   └── kustomization.yaml  # Staging overrides
    └── production/
        └── kustomization.yaml  # Production overrides
```

## Quick Start

### 1. Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Container registry access

### 2. Update Configuration

Edit `secrets.yaml` with your actual secrets:

```bash
# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Deploy

#### Option A: Direct kubectl

```bash
kubectl apply -f namespace.yaml
kubectl apply -f secrets.yaml -n illness-prediction
kubectl apply -f . -n illness-prediction
```

#### Option B: Kustomize (Recommended)

```bash
# Staging
kubectl apply -k overlays/staging/

# Production
kubectl apply -k overlays/production/
```

#### Option C: Deployment Script

```bash
# From project root
./scripts/deploy.sh production v1.0.0
```

### 4. Verify

```bash
kubectl get all -n illness-prediction
kubectl get ingress -n illness-prediction
```

## Components

### Application (app-deployment.yaml)

- **Replicas**: 3 (configurable via HPA: 3-10)
- **Resources**:
  - Requests: 512Mi memory, 500m CPU
  - Limits: 2Gi memory, 2000m CPU
- **Probes**:
  - Liveness: `/health` endpoint
  - Readiness: `/health` endpoint
- **Volumes**:
  - Models: 20Gi (ReadWriteMany)
  - Data: 50Gi (ReadWriteMany)

### PostgreSQL (postgres-deployment.yaml)

- **Image**: postgres:15-alpine
- **Storage**: 10Gi persistent volume
- **Resources**:
  - Requests: 256Mi memory, 250m CPU
  - Limits: 1Gi memory, 1000m CPU

### Redis (redis-deployment.yaml)

- **Image**: redis:7-alpine
- **Storage**: 5Gi persistent volume
- **Resources**:
  - Requests: 128Mi memory, 100m CPU
  - Limits: 512Mi memory, 500m CPU

### Ingress (ingress.yaml)

- **Controller**: NGINX Ingress Controller
- **TLS**: Let's Encrypt (cert-manager)
- **Features**:
  - SSL redirect
  - Rate limiting (100 RPS)
  - CORS enabled
  - Connection limits (50)

### Network Policies (network-policy.yaml)

- App pods can access: PostgreSQL, Redis, external APIs
- PostgreSQL accepts: App pods only
- Redis accepts: App pods only
- Ingress accepts: Ingress controller only

### Monitoring (service-monitor.yaml)

- **ServiceMonitor**: Prometheus scraping configuration
- **PrometheusRule**: Alert rules
  - High error rate (>1%)
  - High latency (P95 >500ms)
  - Model accuracy degradation (<80%)
  - Data drift (PSI >0.25)
  - Resource usage alerts

## Configuration

### ConfigMap

Application configuration is stored in `configmap.yaml`. Update values as needed:

```yaml
data:
  LOG_LEVEL: "INFO"
  MAX_QUESTIONS_PER_SESSION: "15"
  PREDICTION_CONFIDENCE_THRESHOLD: "0.30"
  # ... more config
```

### Secrets

Sensitive data is stored in `secrets.yaml`. **Never commit actual secrets!**

Required secrets:
- `POSTGRES_PASSWORD`
- `ENCRYPTION_KEY`
- `LLM_API_KEY`
- `JWT_SECRET_KEY`

Optional secrets:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `GOOGLE_PLACES_API_KEY`
- `TRANSLATION_API_KEY`

### Environment-Specific Overrides

Use Kustomize overlays for environment-specific configuration:

**Staging** (`overlays/staging/kustomization.yaml`):
- 2 replicas
- Lower resource limits
- Debug logging enabled

**Production** (`overlays/production/kustomization.yaml`):
- 5 replicas
- Higher resource limits
- Info logging

## Scaling

### Manual Scaling

```bash
kubectl scale deployment/illness-prediction-app --replicas=5 -n illness-prediction
```

### Auto-Scaling (HPA)

Horizontal Pod Autoscaler is configured automatically:

```yaml
minReplicas: 3
maxReplicas: 10
metrics:
  - CPU: 70%
  - Memory: 80%
```

Monitor HPA:

```bash
kubectl get hpa -n illness-prediction
kubectl describe hpa illness-prediction-hpa -n illness-prediction
```

## Canary Deployment

Deploy new version with canary strategy:

1. **Deploy canary**:
```bash
kubectl apply -f canary-deployment.yaml -n illness-prediction
```

2. **Update image**:
```bash
kubectl set image deployment/illness-prediction-app-canary \
  app=your-registry/illness-prediction:v1.1.0 \
  -n illness-prediction
```

3. **Monitor** (10% traffic)

4. **Promote** (update main deployment)

5. **Cleanup**:
```bash
kubectl delete deployment illness-prediction-app-canary -n illness-prediction
```

## Rollback

```bash
# Rollback to previous version
kubectl rollout undo deployment/illness-prediction-app -n illness-prediction

# Rollback to specific revision
kubectl rollout undo deployment/illness-prediction-app \
  --to-revision=2 \
  -n illness-prediction

# Check rollout history
kubectl rollout history deployment/illness-prediction-app -n illness-prediction
```

## Monitoring

### Prometheus

ServiceMonitor is configured to scrape metrics from `/metrics` endpoint on port 9090.

### Grafana Dashboards

Import dashboards from `config/monitoring/grafana/dashboards/`:
- Prediction Monitoring
- Model Performance
- System Health
- Drift Detection

### Alerts

PrometheusRule defines alerts for:
- Application errors
- High latency
- Model performance
- Resource usage

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n illness-prediction
kubectl describe pod <pod-name> -n illness-prediction
kubectl logs -f <pod-name> -n illness-prediction
```

### Check Services

```bash
kubectl get svc -n illness-prediction
kubectl describe svc illness-prediction-service -n illness-prediction
```

### Check Ingress

```bash
kubectl get ingress -n illness-prediction
kubectl describe ingress illness-prediction-ingress -n illness-prediction
```

### Port Forward for Testing

```bash
kubectl port-forward -n illness-prediction \
  service/illness-prediction-service 8080:80

curl http://localhost:8080/health
```

### Check Events

```bash
kubectl get events -n illness-prediction --sort-by='.lastTimestamp'
```

## Storage Classes

Update storage class based on your cloud provider:

**AWS**:
```yaml
storageClassName: gp3  # or gp2
```

**GCP**:
```yaml
storageClassName: standard-rwo  # or premium-rwo
```

**Azure**:
```yaml
storageClassName: managed-premium  # or managed
```

## Security

### Network Policies

Network policies restrict traffic between pods. Ensure your CNI supports network policies (Calico, Cilium, etc.).

### RBAC

Create service account with minimal permissions:

```bash
kubectl create serviceaccount illness-prediction-sa -n illness-prediction
# Apply RBAC rules as needed
```

### Pod Security

Consider using Pod Security Standards:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: illness-prediction
  labels:
    pod-security.kubernetes.io/enforce: restricted
```

## Best Practices

1. **Use Kustomize**: Manage environment-specific configs
2. **External Secrets**: Use external secret management (Vault, AWS Secrets Manager)
3. **Resource Limits**: Always set resource requests and limits
4. **Health Checks**: Configure liveness and readiness probes
5. **Monitoring**: Set up Prometheus and Grafana
6. **Backups**: Regular database backups
7. **Updates**: Keep images and dependencies updated
8. **Testing**: Test in staging before production

## Additional Resources

- [Deployment Guide](../docs/deployment/DEPLOYMENT_GUIDE.md)
- [Operations Runbook](../docs/deployment/OPERATIONS_RUNBOOK.md)
- [Monitoring Guide](../config/monitoring/README.md)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
