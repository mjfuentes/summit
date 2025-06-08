#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN} Deploying OpenCode to Kubernetes${NC}"

# Check if kubectl is configured
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED} kubectl is not configured or cluster is not accessible${NC}"
    echo "Please run: gcloud container clusters get-credentials summit-cluster --region us-central1"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "infrastructure/kubernetes/opencode/deployment.yaml" ]; then
    echo -e "${RED} Please run this script from the Summit project root${NC}"
    exit 1
fi

echo -e "${YELLOW} Current cluster context:${NC}"
kubectl config current-context

echo -e "${YELLOW} Creating namespace and shared resources...${NC}"
kubectl apply -f infrastructure/kubernetes/shared/namespace.yaml

echo -e "${YELLOW} Deploying OpenCode agents...${NC}"
kubectl apply -f infrastructure/kubernetes/opencode/deployment.yaml

echo -e "${YELLOW} Waiting for deployment to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/opencode-agent -n summit

echo -e "${GREEN} OpenCode deployment successful!${NC}"

echo -e "${YELLOW} Deployment status:${NC}"
kubectl get pods -n summit -l app=opencode-agent
kubectl get services -n summit

echo -e "${YELLOW} To check logs:${NC}"
echo "kubectl logs -f deployment/opencode-agent -n summit"

echo -e "${YELLOW} To port-forward for testing:${NC}"
echo "kubectl port-forward service/opencode-service 8080:80 -n summit"

echo -e "${GREEN} OpenCode is now running on Kubernetes!${NC}" 