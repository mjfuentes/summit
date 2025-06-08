# Summit Infrastructure

This directory contains all infrastructure-as-code for deploying Summit and its components.

## TODOs and Future Improvements

### Task Distribution Architecture
Current: Cloud Tasks with HTTP webhooks to agents
Future: Consider migration to system with better backpressure handling:
- Pub/Sub with pull subscriptions (agents pull messages)
- Database polling with atomic claiming and load awareness
- Custom queue system with agent capacity monitoring

Current setup works but has limitations around backpressure when agents are overwhelmed.

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