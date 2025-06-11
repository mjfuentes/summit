# OpenCode Agent with Vertex AI

A production-ready OpenCode agent deployment for Kubernetes with Vertex AI integration.

## Overview

This OpenCode agent provides AI-powered coding assistance using Google's Vertex AI (Gemini 2.0 Flash) model. It includes three pre-configured agents:

- **coder**: High-reasoning coding assistant (4096 tokens)
- **reviewer**: Medium-reasoning code reviewer (2048 tokens)  
- **debugger**: High-reasoning debugging assistant (4096 tokens)

## Features

-  **Vertex AI Integration**: Uses Gemini 2.0 Flash via Vertex AI
-  **Kubernetes Ready**: Full K8s deployment with proper resource limits
-  **Secure Authentication**: Service account-based Google Cloud authentication
-  **GitOps CI/CD**: Automated build and deployment pipeline
-  **Interactive Mode**: TTY support for direct interaction

## Prerequisites

### Google Cloud Setup

1. **Service Account**: Create a service account with Vertex AI permissions:
   ```bash
   gcloud iam service-accounts create opencode-agent \
     --description="OpenCode agent service account" \
     --display-name="OpenCode Agent"
   ```

2. **IAM Roles**: Grant necessary permissions:
   ```bash
   gcloud projects add-iam-policy-binding summit-ai-platform \
     --member="serviceAccount:opencode-agent@summit-ai-platform.iam.gserviceaccount.com" \
     --role="roles/aiplatform.user"
   ```

3. **Workload Identity** (if using GKE Workload Identity):
   ```bash
   gcloud iam service-accounts add-iam-policy-binding \
     opencode-agent@summit-ai-platform.iam.gserviceaccount.com \
     --role roles/iam.workloadIdentityUser \
     --member "serviceAccount:summit-ai-platform.svc.id.goog[default/opencode-agent-sa]"
   ```

### Kubernetes Setup

1. **Service Account Credentials**: Create a Kubernetes secret with the service account key:
   ```bash
   kubectl create secret generic google-cloud-credentials \
     --from-file=credentials.json=/path/to/service-account-key.json
   ```

## Deployment

### Automated Deployment (GitOps)

The agent deploys automatically when changes are pushed to the `main` branch:

1. **Push to Summit repository**: Any changes to `opencode-agent/` trigger the CI/CD pipeline
2. **Build**: Docker image is built and pushed to GitHub Container Registry
3. **Deploy**: Image is deployed to GKE cluster automatically

### Manual Deployment

```bash
# Build and push image
docker build -t ghcr.io/matifuentes/opencode-agent:latest .
docker push ghcr.io/matifuentes/opencode-agent:latest

# Deploy to Kubernetes
kubectl apply -f k8s-deployment.yaml
```

## Usage

### Connect to the Agent

```bash
# Get the pod name
kubectl get pods -l app=opencode-agent

# Connect interactively
kubectl exec -it <pod-name> -- /bin/bash
```

### Using OpenCode Agents

Once connected to the pod:

```bash
# Use the coder agent
opencode coder -p "Add a calculate_sum function to this Python file"

# Use the reviewer agent  
opencode reviewer -p "Review this code for best practices"

# Use the debugger agent
opencode debugger -p "Help me debug this error: ..."

# Get help
opencode -h
```

### Example Commands

```bash
# File editing task
opencode coder -p "Read the file app.py and add proper error handling"

# Code review
opencode reviewer -p "Review the changes in this directory for security issues"

# Debugging assistance  
opencode debugger -p "This function is throwing a TypeError, help me fix it"
```

## Configuration

### Agent Configuration

Edit `opencode_config.json` to modify agent behavior:

```json
{
  "agents": {
    "coder": {
      "model": "vertex:gemini-2.0-flash-001",
      "reasoningEffort": "high",
      "maxTokens": 4096
    }
  }
}
```

### Environment Variables

- `VERTEXAI_PROJECT`: Google Cloud project ID
- `VERTEXAI_LOCATION`: Vertex AI region (us-central1)
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account JSON

## Architecture

```
        
   Developer       OpenCode Pod      Vertex AI     
                       (Kubernetes)         (Gemini 2.0)   
        
                              
                              
                       
                          Workspace     
                          (emptyDir)    
                       
```

## Monitoring

### Check Agent Status

```bash
# Pod status
kubectl get pods -l app=opencode-agent

# Logs
kubectl logs -l app=opencode-agent --tail=100

# Resource usage
kubectl top pods -l app=opencode-agent
```

### Health Checks

The entrypoint script performs automatic health checks:
-  Environment variables validation
-  Credentials file verification  
-  OpenCode binary availability
-  Configuration file validation

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   ```bash
   # Check credentials
   kubectl describe secret google-cloud-credentials
   
   # Verify service account permissions
   gcloud projects get-iam-policy summit-ai-platform
   ```

2. **Pod Crash Loop**
   ```bash
   # Check logs
   kubectl logs <pod-name> --previous
   
   # Check events
   kubectl describe pod <pod-name>
   ```

3. **Out of Memory**
   ```bash
   # Check resource usage
   kubectl top pod <pod-name>
   
   # Increase memory limits in k8s-deployment.yaml
   ```

## Security

-  **Least Privilege**: Service account has minimal required permissions
-  **Secrets Management**: Credentials stored as Kubernetes secrets
-  **Network Isolation**: ClusterIP service for internal access only
-  **Container Security**: Non-root user, minimal base image

## Development

### Local Testing

```bash
# Build locally
docker build -t opencode-agent:dev .

# Test with local credentials
docker run -it --rm \
  -v ~/.config/gcloud/application_default_credentials.json:/tmp/creds.json:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/creds.json \
  -e VERTEXAI_PROJECT=summit-ai-platform \
  -e VERTEXAI_LOCATION=us-central1 \
  opencode-agent:dev
```

### Adding New Agents

1. Edit `opencode_config.json`
2. Add new agent configuration
3. Update documentation
4. Test deployment

## Support

For issues and questions:
- Check logs: `kubectl logs -l app=opencode-agent`
- Review configuration: `kubectl describe pod <pod-name>`
- Verify authentication: Test Vertex AI access manually 