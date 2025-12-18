#!/bin/bash
# Script to create Kubernetes secret from .env file

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    exit 1
fi

# Create secret from .env file in default namespace
kubectl create secret generic mcp-assessment-secret \
    --from-env-file=.env \
    --dry-run=client -o yaml | kubectl apply -f -

echo "Secret created successfully in default namespace!"
echo "To verify: kubectl get secret mcp-assessment-secret"
