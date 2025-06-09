#!/bin/bash
# Deploy Summit agents with different roles using a single template

set -e

AGENT_ROLE=${1:-engineering}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration for different agent roles
case $AGENT_ROLE in
  "engineering")
    export AGENT_NAME="engineering-agent"
    export AGENT_ROLE="engineering"
    export WORKFLOW_STAGE="second"
    ;;
  "product")
    export AGENT_NAME="product-agent"
    export AGENT_ROLE="product"
    export WORKFLOW_STAGE="first"
    ;;
  "quality_control")
    export AGENT_NAME="quality-control-agent"
    export AGENT_ROLE="quality_control"
    export WORKFLOW_STAGE="third"
    ;;
  *)
    echo "Error: Unknown agent role '$AGENT_ROLE'"
    echo "Usage: $0 [engineering|product|quality_control]"
    exit 1
    ;;
esac

echo "Deploying $AGENT_NAME with role $AGENT_ROLE..."

# Create the deployment YAML by substituting environment variables
cat > "/tmp/$AGENT_NAME.yaml" << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${AGENT_NAME}
  namespace: summit
  labels:
    app: ${AGENT_NAME}
    component: ai-agent
    role: ${AGENT_ROLE}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ${AGENT_NAME}
  template:
    metadata:
      labels:
        app: ${AGENT_NAME}
        role: ${AGENT_ROLE}
    spec:
      serviceAccountName: summit-agent-sa
      imagePullSecrets:
      - name: ghcr-login-secret
      initContainers:
      - name: repo-init
        image: alpine/git:latest
        command: ["/bin/sh"]
        args:
        - -c
        - |
          echo "Initializing repository for ${AGENT_ROLE} agent..."
          cd /workspace
          
          if [ "$(ls -A /workspace)" ]; then
            echo "Workspace not empty, cleaning up..."
            rm -rf /workspace/* /workspace/.[!.]* /workspace/..?* 2>/dev/null || true
          fi
          
          REPO_URL_WITH_TOKEN="https://${GITHUB_TOKEN}@github.com/mjfuentes/summit.git"
          echo "Cloning repository with authentication..."
          git clone --depth 10 "$REPO_URL_WITH_TOKEN" . || {
            echo "Clone with token failed, trying fallback methods..."
            git clone --depth 10 "https://github.com/mjfuentes/summit.git" . || {
              echo "ERROR: All git clone attempts failed"
              exit 1
            }
          }
          
          git config user.name "Summit ${AGENT_ROLE} Agent"
          git config user.email "${AGENT_ROLE}-agent@summit.ai"
          git config pull.rebase false
          echo "Repository initialized successfully"
        env:
        - name: AGENT_ROLE
          value: ${AGENT_ROLE}
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: summit-secrets
              key: github-token
        volumeMounts:
        - name: workspace
          mountPath: /workspace
      containers:
      - name: ${AGENT_NAME}
        image: ghcr.io/mjfuentes/summit/opencode:latest
        command: ["python3"]
        args: ["/app/agent_lifecycle.py"]
        env:
        - name: AGENT_ROLE
          value: ${AGENT_ROLE}
        - name: WORKFLOW_STAGE
          value: ${WORKFLOW_STAGE}
        - name: WORKSPACE_PATH
          value: "/workspace"
        - name: PYTHONPATH
          value: "/app/src"
        - name: AGENT_HEARTBEAT_INTERVAL
          value: "60"
        - name: GIT_CLEANUP_ENABLED
          value: "true"
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: summit-secrets
              key: anthropic-api-key
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: summit-secrets
              key: github-token
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "400m"
        livenessProbe:
          exec:
            command:
            - python3
            - -c
            - "import os; print('Agent alive'); exit(0)"
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          exec:
            command:
            - python3
            - -c
            - "import os; exit(0 if os.path.exists('/tmp/agent-ready') else 1)"
          initialDelaySeconds: 15
          periodSeconds: 10
        volumeMounts:
        - name: workspace
          mountPath: /workspace
        - name: app-code
          mountPath: /app
        - name: git-scripts
          mountPath: /scripts
      volumes:
      - name: workspace
        persistentVolumeClaim:
          claimName: ${AGENT_NAME}-workspace
      - name: app-code
        configMap:
          name: summit-agent-code
      - name: git-scripts
        configMap:
          name: git-cleanup-scripts
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ${AGENT_NAME}-workspace
  namespace: summit
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard-rwo
EOF

# Substitute environment variables and apply
envsubst < "/tmp/$AGENT_NAME.yaml" | kubectl apply -f -

echo " $AGENT_NAME deployed successfully!"

# Clean up temporary file
rm "/tmp/$AGENT_NAME.yaml" 