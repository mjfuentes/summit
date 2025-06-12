# Cluster Status Monitoring

The Summit cluster status monitoring tool provides clear, organized information about all deployments, pods, and services in the Kubernetes cluster without requiring deep Kubernetes or GCP knowledge.

## Quick Start

```bash
# Basic status check
python3 scripts/cluster_status.py

# Detailed view with resource usage
python3 scripts/cluster_status.py --detailed

# Continuous monitoring
python3 scripts/cluster_status.py --watch

# Check only Summit namespace
python3 scripts/cluster_status.py --namespace summit
```

## Prerequisites

1. **kubectl installed and configured**
   ```bash
   # Install kubectl using Homebrew (recommended for macOS)
   brew install kubectl
   
   # OR install manually:
   curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/amd64/kubectl"
   chmod +x kubectl
   sudo mv kubectl /usr/local/bin/
   
   # Verify installation
   kubectl version --client
   
   # Configure access to Summit cluster
   gcloud container clusters get-credentials summit-cluster --region us-central1
   ```

2. **Python 3** (usually pre-installed on macOS)

## Usage Examples

### Basic Status Check
Shows overview of all deployments, pods, and services:
```bash
python3 scripts/cluster_status.py
```

**Output includes:**
- Cluster connection status
- Namespace overview
- Deployment health (ready/total replicas)
- Pod status with age and restart counts
- Service endpoints and ports
- Recent events
- Overall cluster health summary

### Detailed Information
Includes resource usage, container details, and deployment conditions:
```bash
python3 scripts/cluster_status.py --detailed
```

**Additional details:**
- CPU and memory requests/limits
- Container restart counts and reasons
- Deployment conditions (Available, Progressing)
- Resource utilization

### Continuous Monitoring
Refreshes status every 30 seconds (useful for debugging deployments):
```bash
python3 scripts/cluster_status.py --watch
```

Press `Ctrl+C` to stop monitoring.

### Specific Namespace
Focus on a particular namespace:
```bash
# Summit namespace only
python3 scripts/cluster_status.py --namespace summit

# Default namespace
python3 scripts/cluster_status.py --namespace default
```

### Events Only
Show recent cluster events for troubleshooting:
```bash
python3 scripts/cluster_status.py --events-only
```

## Understanding the Output

### Status Indicators
-  **Green**: Healthy/Running/Ready
-  **Yellow**: Warning/Degraded/Pending
-  **Red**: Error/Failed/Not Ready
- ℹ **Blue**: Information/Normal events

### Deployment Status
- **Ready: X/Y** - X pods ready out of Y desired
- **Age** - How long since deployment was created
- **Version** - Deployment version label (if present)

### Pod Status
- **Running** - Pod is active and containers are running
- **Pending** - Pod is waiting to be scheduled or start
- **ContainerCreating** - Pod is starting up
- **CrashLoopBackOff** - Container keeps failing and restarting

### Service Information
- **Type** - ClusterIP (internal), LoadBalancer (external), NodePort
- **Cluster IP** - Internal cluster address
- **Ports** - Port mappings (name:external->internal/protocol)

### Events
- **Age** - When the event occurred (e.g., 5m, 2h, 3d)
- **Object** - What resource the event relates to
- **Reason** - Event type (Started, Pulled, Created, etc.)

## Common Scenarios

### Checking Deployment Health
```bash
# Quick health check
python3 scripts/cluster_status.py --namespace summit

# Look for:
# - All deployments showing "Ready: X/X" 
# - Pods in "Running" status
# - No recent Warning events
```

### Debugging Failed Deployments
```bash
# Get detailed information
python3 scripts/cluster_status.py --detailed --namespace summit

# Check for:
# - Pods stuck in Pending/ContainerCreating
# - High restart counts
# - Resource limit issues
# - Recent error events
```

### Monitoring During Deployment
```bash
# Watch deployment progress
python3 scripts/cluster_status.py --watch --namespace summit

# Monitor until:
# - New pods reach Running status
# - Deployment shows healthy replica count
# - No error events appear
```

## Expected Services

The Summit cluster typically runs these services:

### Summit Namespace
- **opencode-agent** - AI coding agent pods
- **summit-app** - Main Summit application
- **summit-mcp-server** - MCP server for AI interactions
- **bridge-service** - API bridge service

### Service Health Indicators
- **Deployments**: Should show "Ready: 1/1" or higher
- **Pods**: Should be in "Running" status with low restart counts
- **Services**: Should have cluster IPs assigned
- **Events**: Recent events should be mostly "Normal" type

## Troubleshooting

### Cannot Connect to Cluster
```
Error: Cannot connect to cluster
```
**Solution:**
```bash
gcloud container clusters get-credentials summit-cluster --region us-central1
```

### kubectl Not Found
```
Error: kubectl is not installed or not in PATH
```
**Solution:** Install kubectl:
```bash
# Easiest method - using Homebrew
brew install kubectl

# Alternative - using gcloud SDK
gcloud components install kubectl

# Verify installation
kubectl version --client
```

### Pods Stuck in Pending
**Common causes:**
- Insufficient cluster resources
- Image pull failures
- Missing secrets or config maps
- Node selector constraints

**Check with:**
```bash
python3 scripts/cluster_status.py --detailed --namespace summit
```

### High Restart Counts
**Indicates:**
- Application crashes
- Health check failures
- Resource limits exceeded

**Investigate with:**
```bash
# Check pod logs
kubectl logs -l app=<service-name> -n summit --tail=100

# Check resource usage
kubectl top pods -n summit
```

### Services Not Accessible
**Check:**
- Service has correct selector labels
- Pods are running and ready
- Ports are correctly configured
- Network policies allow traffic

## Integration with CI/CD

The cluster status tool integrates with Summit's deployment workflows:

- **Post-deployment validation** - Verify services are healthy after deployment
- **Monitoring dashboards** - Automated health checks
- **Alert integration** - Detect and report deployment issues

## Advanced Usage

### Custom Output Format
The tool outputs structured information that can be parsed:
```bash
# Save status to file
python3 scripts/cluster_status.py > cluster-status.log

# Filter specific information
python3 scripts/cluster_status.py | grep -A 5 "opencode-agent"
```

### Automation Scripts
Use in deployment scripts:
```bash
#!/bin/bash
# Deploy and verify
kubectl apply -f deployment.yaml

# Wait and check status
sleep 30
python3 scripts/cluster_status.py --namespace summit

# Exit with error if unhealthy
if ! python3 scripts/cluster_status.py --namespace summit | grep -q "Overall Status: Healthy"; then
    echo "Deployment verification failed"
    exit 1
fi
```

## Related Tools

- **kubectl** - Direct Kubernetes CLI
- **k9s** - Terminal-based Kubernetes UI
- **Grafana** - Metrics and monitoring dashboards
- **Summit deployment scripts** - Automated deployment tools

## Support

For issues with the cluster status tool:
1. Check prerequisites are met
2. Verify cluster connectivity
3. Review recent cluster events
4. Check Summit deployment documentation 