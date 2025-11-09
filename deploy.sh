#!/bin/bash
# deploy.sh - Simple deployment script for Whatspy production
# Usage: ./deploy.sh [branch_name]

set -e  # Exit on any error

# Configuration
BRANCH=${1:-main}
SERVICE_NAME="whatspy"

echo "🚀 Deploying Whatspy - Branch: $BRANCH"

# Pull latest code
echo "📥 Pulling latest code..."
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"
echo "✅ Code updated"

# Restart service
echo "🔄 Restarting service..."
sudo systemctl restart "$SERVICE_NAME"
echo "✅ Service restarted"

# Check if service is running
if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "🎉 Deployment completed successfully!"
    echo "📊 Service Status: $(sudo systemctl is-active $SERVICE_NAME)"
else
    echo "❌ Service failed to start!"
    sudo systemctl status "$SERVICE_NAME" --no-pager
    exit 1
fi