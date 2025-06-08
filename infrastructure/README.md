# Summit Infrastructure

This directory contains all infrastructure-as-code for deploying Summit and its components.

## Architecture Overview

```
        
   Render.com           Kubernetes            RunPod       
                                                           
  Summit App       OpenCode         Llama 3.1      
  (FastAPI)            Agents               Model          
                                                           
        
```

## Deployment Strategy

### Phase 1: OpenCode on Kubernetes
- Deploy OpenCode agents to K8s cluster
- Keep Summit app on Render.com
- Test integration between Render ↔ K8s ↔ RunPod

### Phase 2: Full Migration
- Move Summit app to Kubernetes
- Unified deployment and scaling
- Single cluster management

## Directory Structure

```
infrastructure/
 kubernetes/
    opencode/          # OpenCode agent deployments
    summit-app/        # Summit FastAPI app
    shared/            # Shared resources (ingress, secrets)
 terraform/             # Cloud infrastructure provisioning
 helm-charts/           # Helm charts for complex deployments
 scripts/               # Deployment automation scripts
```

## Getting Started

1. Choose cloud provider
2. Run Terraform to provision cluster
3. Deploy OpenCode agents
4. Test integration
5. Migrate Summit app 