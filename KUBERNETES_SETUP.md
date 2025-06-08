# Summit Kubernetes Setup Guide

This guide walks you through deploying Summit's OpenCode agents to Kubernetes while keeping the main app on Render.com.

## Architecture

```
        
   Render.com           Kubernetes            RunPod       
                                                           
  Summit App       OpenCode         Llama 3.1      
  (FastAPI)            Agents               Model          
                                                           
        
```

## Prerequisites

1. **Google Cloud Account** with billing enabled
2. **gcloud CLI** installed and configured
3. **kubectl** installed
4. **Terraform** installed (optional, for automated setup)

## Quick Setup (Manual)

### 1. Create GKE Cluster

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable container.googleapis.com
gcloud services enable compute.googleapis.com

# Create cluster
gcloud container clusters create summit-cluster \
  --region us-central1 \
  --num-nodes 2 \
  --machine-type e2-standard-2 \
  --enable-autoscaling \
  --min-nodes 1 \
  --max-nodes 5
```

### 2. Configure kubectl

```bash
gcloud container clusters get-credentials summit-cluster --region us-central1
```

### 3. Deploy OpenCode

```bash
# From Summit project root
./infrastructure/scripts/deploy-opencode.sh
```

## Automated Setup (Terraform)

### 1. Set up Terraform

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var="project_id=your-gcp-project-id"

# Apply
terraform apply -var="project_id=your-gcp-project-id"
```

### 2. Deploy OpenCode

```bash
# Get cluster credentials
gcloud container clusters get-credentials summit-cluster --region us-central1

# Deploy
./infrastructure/scripts/deploy-opencode.sh
```

## Required Secrets

Add these to your GitHub repository secrets for CI/CD:

- `GCP_PROJECT_ID`: Your Google Cloud project ID
- `GCP_SA_KEY`: Service account key JSON (base64 encoded)
- `RUNPOD_API_KEY`: Your RunPod API key
- `HUGGINGFACE_TOKEN`: Your Hugging Face token

## Testing the Deployment

### 1. Check Pod Status

```bash
kubectl get pods -n summit
```

### 2. Check Logs

```bash
kubectl logs -f deployment/opencode-agent -n summit
```

### 3. Port Forward for Testing

```bash
kubectl port-forward service/opencode-service 8080:80 -n summit
```

Then test: `curl http://localhost:8080/health`

## Connecting from Render.com

Update your Summit app on Render to connect to the Kubernetes OpenCode service:

```python
# In your Summit app
OPENCODE_ENDPOINT = "http://opencode-service.summit.svc.cluster.local"
# Or use external LoadBalancer IP if configured
```

## Scaling

The deployment auto-scales based on CPU usage:
- **Min replicas**: 1
- **Max replicas**: 5
- **Target CPU**: 70%

Manual scaling:
```bash
kubectl scale deployment opencode-agent --replicas=3 -n summit
```

## Monitoring

View metrics in Google Cloud Console:
- **GKE Workloads**: Monitor pod health
- **Cloud Logging**: View application logs
- **Cloud Monitoring**: Set up alerts

## Cost Optimization

- **Preemptible nodes**: Add `--preemptible` flag for 80% cost savings
- **Auto-scaling**: Automatically scales down during low usage
- **Resource limits**: Prevents runaway resource usage

## Troubleshooting

### Common Issues

1. **Pods stuck in Pending**: Check node resources
2. **ImagePullBackOff**: Verify image name and registry access
3. **CrashLoopBackOff**: Check application logs

### Debug Commands

```bash
# Describe pod for events
kubectl describe pod <pod-name> -n summit

# Get detailed logs
kubectl logs <pod-name> -n summit --previous

# Execute into pod
kubectl exec -it <pod-name> -n summit -- /bin/bash
```

## Next Steps

1. **Test OpenCode integration** with Summit app
2. **Set up monitoring** and alerting
3. **Configure CI/CD** for automated deployments
4. **Plan Summit app migration** to Kubernetes 