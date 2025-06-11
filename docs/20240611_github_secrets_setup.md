# GitHub Secrets Setup Guide

**Last Updated:** December 2024  
**Version:** 1.1

This document provides step-by-step instructions for configuring GitHub repository secrets required for Summit's CI/CD pipeline.

## Required Secrets

### Google Cloud Authentication

The workflow supports two authentication methods. Configure **one** of the following:

#### Option 1: Service Account Key (Recommended for testing)

1. **GCP_SA_KEY**: Base64-encoded service account key JSON
   - Create a service account in your GCP project
   - Download the JSON key file
   - Base64 encode the entire JSON content
   - Add as repository secret

2. **GCP_PROJECT_ID**: Your Google Cloud project ID
   - Example: `summit-ai-platform`

#### Option 2: Workload Identity Federation (Recommended for production)

1. **WIF_PROVIDER**: Workload Identity Provider resource name
   - Example: `projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider`

2. **WIF_SERVICE_ACCOUNT**: Service account email for workload identity
   - Example: `github-actions@summit-ai-platform.iam.gserviceaccount.com`

3. **GCP_PROJECT_ID**: Your Google Cloud project ID

### Application Secrets (Optional)

These secrets are used by the deployed applications but are not required for infrastructure deployment:

- **RUNPOD_API_KEY**: RunPod API key for GPU compute
- **HUGGINGFACE_TOKEN**: Hugging Face API token for model access
- **GITHUB_TOKEN**: GitHub personal access token (usually auto-provided)

## Setting Up Secrets

### In GitHub Repository

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the exact name and value

### Service Account Permissions

Your service account needs the following IAM roles:

- `Kubernetes Engine Admin`
- `Compute Admin`
- `Cloud Tasks Admin`
- `Cloud Datastore User`
- `Service Account User`

### Example Service Account Key Setup

```bash
# Create service account
gcloud iam service-accounts create github-actions \
    --display-name="GitHub Actions" \
    --project=summit-ai-platform

# Grant necessary permissions
gcloud projects add-iam-policy-binding summit-ai-platform \
    --member="serviceAccount:github-actions@summit-ai-platform.iam.gserviceaccount.com" \
    --role="roles/container.admin"

gcloud projects add-iam-policy-binding summit-ai-platform \
    --member="serviceAccount:github-actions@summit-ai-platform.iam.gserviceaccount.com" \
    --role="roles/compute.admin"

gcloud projects add-iam-policy-binding summit-ai-platform \
    --member="serviceAccount:github-actions@summit-ai-platform.iam.gserviceaccount.com" \
    --role="roles/cloudtasks.admin"

# Create and download key
gcloud iam service-accounts keys create github-actions-key.json \
    --iam-account=github-actions@summit-ai-platform.iam.gserviceaccount.com

# Base64 encode for GitHub secret
base64 -i github-actions-key.json | pbcopy  # macOS
base64 -w 0 github-actions-key.json         # Linux
```

## Workflow Behavior

### Without Secrets
- Terraform plan will run but may fail on GCP operations
- Deployment steps will be skipped with informational messages
- No infrastructure changes will be made

### With Proper Secrets
- Full infrastructure deployment will proceed
- Kubernetes cluster will be created/updated
- Cloud Tasks and PostgreSQL database will be provisioned
- OpenCode agents will be deployed

## Troubleshooting

### "workload_identity_provider" or "credentials_json" Error
- Ensure exactly one authentication method is configured
- Check that secret names match exactly (case-sensitive)
- Verify secret values are properly formatted

### Permission Denied Errors
- Check service account has required IAM roles
- Verify project ID is correct
- Ensure APIs are enabled in GCP project

### Deployment Timeouts
- Check cluster has sufficient resources
- Verify container images are accessible
- Review Kubernetes events for pod startup issues

## Security Best Practices

1. **Use Workload Identity Federation** for production deployments
2. **Rotate service account keys** regularly if using key-based auth
3. **Limit service account permissions** to minimum required
4. **Monitor secret usage** in GitHub Actions logs
5. **Use environment-specific secrets** for staging vs production

## Testing the Setup

You can test your secret configuration by:

1. Creating a test PR that modifies infrastructure files
2. Checking the workflow runs successfully
3. Verifying authentication steps complete without errors
4. Confirming Terraform plan executes properly

The workflow will provide clear feedback about which authentication method is being used and any configuration issues. 