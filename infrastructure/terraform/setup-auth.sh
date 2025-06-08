#!/bin/bash

# Terraform Authentication Setup Script
# This script helps set up authentication for Terraform with Google Cloud

set -e

echo "Summit Terraform Authentication Setup"
echo "===================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed."
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "No active gcloud authentication found."
    echo "Please run: gcloud auth login"
    exit 1
fi

# Get current project
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")

if [ -z "$CURRENT_PROJECT" ]; then
    echo "No default project set."
    echo "Please run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "Current project: $CURRENT_PROJECT"

# Set up application default credentials
echo "Setting up application default credentials..."
gcloud auth application-default login

echo ""
echo "Authentication setup complete!"
echo ""
echo "You can now run Terraform commands:"
echo "  terraform init"
echo "  terraform plan -var=\"project_id=$CURRENT_PROJECT\""
echo "  terraform apply -var=\"project_id=$CURRENT_PROJECT\""
echo ""
echo "For CI/CD, set the GOOGLE_APPLICATION_CREDENTIALS environment variable"
echo "to point to your service account key file." 