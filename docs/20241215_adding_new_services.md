# Adding New Services to Summit

**Date:** December 15, 2024  
**Status:** Active  

## Overview

Summit uses a **fully automated GitOps deployment pipeline**. When you add a new service, GitHub Actions automatically builds, pushes, and deploys it to the GKE cluster.

##  Automated Flow

```
Git Push → GitHub Actions → Docker Build → GKE Deploy →  Live Service
```

**Zero manual cluster interaction required!**

##  Adding a New Service

### Step 1: Create Service Directory Structure

```bash
mkdir summit/new-service/
cd summit/new-service/
```

Required files:
```
new-service/
 Dockerfile                # Container build
 requirements.txt          # Dependencies  
 new_service.py           # Main application
 k8s-deployment.yaml      # Kubernetes manifests
 README.md                # Service docs
```

### Step 2: Use Template Files

```bash
# Copy from existing service (e.g., bridge-service)
cp ../bridge-service/Dockerfile .
cp ../bridge-service/k8s-deployment.yaml .
cp ../bridge-service/requirements.txt .

# Edit files to match your service name and requirements
```

### Step 3: Create CI/CD Workflow

```bash
cp ../.github/workflows/build-bridge-service.yml \
   ../.github/workflows/build-new-service.yml
```

Update the workflow file:
- Change `CONTEXT_PATH: bridge-service` to `CONTEXT_PATH: new-service`
- Change `IMAGE_NAME: ${{ github.repository }}/bridge-service` to `IMAGE_NAME: ${{ github.repository }}/new-service`
- Update workflow name and paths

### Step 4: Deploy

```bash
git add .
git commit -m "Add new-service deployment"
git push origin main
```

**That's it!** GitHub Actions will automatically:
- Build Docker image
- Push to `ghcr.io/mjfuentes/summit/new-service:latest`
- Deploy to GKE cluster in `summit` namespace

##  Verify Deployment

```bash
# Check service status
kubectl get pods -n summit -l app=new-service
kubectl get service new-service -n summit

# Test health endpoint
kubectl run test-pod --image=curlimages/curl -it --rm -- \
  curl http://new-service.summit.svc.cluster.local:8000/health
```

##  Service Templates

### Standard Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY new_service.py .
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["python", "new_service.py"]
```

### Standard Kubernetes Manifest
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: new-service
  namespace: summit
spec:
  replicas: 2
  selector:
    matchLabels:
      app: new-service
  template:
    metadata:
      labels:
        app: new-service
    spec:
      containers:
      - name: new-service
        image: ghcr.io/mjfuentes/summit/new-service:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
---
apiVersion: v1
kind: Service
metadata:
  name: new-service
  namespace: summit
spec:
  selector:
    app: new-service
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

##  Key Points

- **No manual `kubectl` commands needed**
- **No manual Docker builds/pushes**
- **Everything automated through GitHub Actions**
- **Service available at:** `http://new-service.summit.svc.cluster.local:8000`
- **Monitor progress:** `https://github.com/mjfuentes/summit/actions`

##  Current Services

| Service | Internal URL | Purpose |
|---------|--------------|---------|
| `summit-mcp-service` | `:8080` | Task management & MCP tools |
| `bridge-service` | `:8000` | OpenAI ↔ RunPod translation |

---

*Fully automated GitOps deployment - just commit and push!*  