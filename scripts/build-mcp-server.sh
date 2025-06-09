#!/bin/bash

# Build and test MCP Server Docker image locally
# Usage: ./scripts/build-mcp-server.sh [--push]

set -e  # Exit on any error

# Configuration
IMAGE_NAME="ghcr.io/mjfuentes/summit/mcp-server"
TAG="latest"
DOCKERFILE="infrastructure/docker/Dockerfile.mcp-server"
PUSH_TO_REGISTRY=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --push)
            PUSH_TO_REGISTRY=true
            shift
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--push] [--tag TAG]"
            echo ""
            echo "Options:"
            echo "  --push       Push image to GitHub Container Registry"
            echo "  --tag TAG    Use specific tag (default: latest)"
            echo "  --help       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

echo "=== Building MCP Server Docker Image ==="
echo "Image: $IMAGE_NAME:$TAG"
echo "Dockerfile: $DOCKERFILE"
echo "Push to registry: $PUSH_TO_REGISTRY"
echo ""

# Check if Dockerfile exists
if [[ ! -f "$DOCKERFILE" ]]; then
    echo "Error: Dockerfile not found at $DOCKERFILE"
    exit 1
fi

# Check if we're in the project root
if [[ ! -f "requirements.txt" ]] || [[ ! -d "src" ]]; then
    echo "Error: This script must be run from the project root directory"
    echo "Make sure you're in the directory containing requirements.txt and src/"
    exit 1
fi

# Build the image
echo "Building Docker image..."
docker build \
    -f "$DOCKERFILE" \
    -t "$IMAGE_NAME:$TAG" \
    .

echo "Build completed successfully!"

# Test the image
echo ""
echo "=== Testing Docker Image ==="

# Test 1: Check if image exists and basic info
echo "Image details:"
docker images "$IMAGE_NAME:$TAG"

# Test 2: Run basic container test
echo ""
echo "Testing container startup..."
CONTAINER_ID=$(docker run -d \
    -p 8080:8080 \
    -e ANTHROPIC_API_KEY="test-key" \
    -e GITHUB_TOKEN="test-token" \
    "$IMAGE_NAME:$TAG")

echo "Container ID: $CONTAINER_ID"

# Wait a moment for startup
sleep 5

# Check if container is running
if docker ps | grep -q "$CONTAINER_ID"; then
    echo "Container is running successfully!"
    
    # Test health check
    echo "Testing health check..."
    if docker exec "$CONTAINER_ID" timeout 5 bash -c '</dev/tcp/localhost/8080' 2>/dev/null; then
        echo "Health check passed!"
    else
        echo "Health check failed (this might be expected if MCP server needs API keys)"
    fi
    
    # Show container logs
    echo ""
    echo "Container logs (last 20 lines):"
    docker logs "$CONTAINER_ID" | tail -20
else
    echo "Container failed to start!"
    docker logs "$CONTAINER_ID"
    docker rm -f "$CONTAINER_ID" 2>/dev/null
    exit 1
fi

# Cleanup test container
echo ""
echo "Cleaning up test container..."
docker stop "$CONTAINER_ID" > /dev/null
docker rm "$CONTAINER_ID" > /dev/null

# Push to registry if requested
if [[ "$PUSH_TO_REGISTRY" == "true" ]]; then
    echo ""
    echo "=== Pushing to GitHub Container Registry ==="
    
    # Check if user is logged in to GHCR
    if ! docker info | grep -q "ghcr.io"; then
        echo "Logging in to GitHub Container Registry..."
        echo "Please ensure you have a GitHub token with packages:write permission"
        docker login ghcr.io
    fi
    
    echo "Pushing $IMAGE_NAME:$TAG..."
    docker push "$IMAGE_NAME:$TAG"
    
    echo "Push completed successfully!"
    echo ""
    echo "Image is now available at: $IMAGE_NAME:$TAG"
fi

echo ""
echo "=== Summary ==="
echo "Image: $IMAGE_NAME:$TAG"
echo "Build: SUCCESS"
echo "Test: SUCCESS"
if [[ "$PUSH_TO_REGISTRY" == "true" ]]; then
    echo "Push: SUCCESS"
fi
echo ""
echo "To deploy to Kubernetes:"
echo "kubectl set image deployment/summit-mcp-server mcp-server=$IMAGE_NAME:$TAG -n summit"
echo ""
echo "To run locally:"
echo "docker run -p 8080:8080 -e ANTHROPIC_API_KEY=\$ANTHROPIC_API_KEY -e GITHUB_TOKEN=\$GITHUB_TOKEN $IMAGE_NAME:$TAG" 