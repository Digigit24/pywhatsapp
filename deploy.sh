#!/bin/bash
# deploy.sh - Simple deployment script for Whatspy production
# Usage: ./deploy.sh [branch_name]

set -e  # Exit on any error

# Configuration
BRANCH=${1:-main}
APP_DIR="/home/ubuntu/whatspy"
SERVICE_NAME="whatspy"
VENV_PATH="/opt/whatspy/venv"
PROD_APP_DIR="/opt/whatspy/app"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if service exists
service_exists() {
    systemctl list-units --full -all | grep -Fq "$1.service"
}

echo "=========================================="
echo "🚀 Deploying Whatspy to Production"
echo "=========================================="
echo "Branch: $BRANCH"
echo "App Directory: $APP_DIR"
echo "Production Directory: $PROD_APP_DIR"
echo "Service: $SERVICE_NAME"
echo "=========================================="

# Step 1: Pull latest code
log_info "Pulling latest code from $BRANCH branch..."
cd "$APP_DIR"
git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"
log_success "Code updated successfully"

# Step 2: Check if production directory exists
if [ ! -d "$PROD_APP_DIR" ]; then
    log_error "Production directory $PROD_APP_DIR does not exist!"
    log_error "Please run auto_setup_prod.py first to set up the production environment."
    exit 1
fi

# Step 3: Copy updated files to production directory
log_info "Copying files to production directory..."
# Backup current .env file
if [ -f "$PROD_APP_DIR/.env" ]; then
    cp "$PROD_APP_DIR/.env" "$PROD_APP_DIR/.env.backup"
    log_info "Backed up existing .env file"
fi

# Copy all files except .env
rsync -av --exclude='.env' --exclude='.git' --exclude='__pycache__' \
    --exclude='*.pyc' --exclude='.pytest_cache' \
    "$APP_DIR/" "$PROD_APP_DIR/"

# Restore .env file if it was backed up
if [ -f "$PROD_APP_DIR/.env.backup" ]; then
    mv "$PROD_APP_DIR/.env.backup" "$PROD_APP_DIR/.env"
    log_info "Restored .env file"
fi

# Set correct ownership
sudo chown -R whatspy:whatspy "$PROD_APP_DIR"
log_success "Files copied and ownership set"

# Step 4: Update Python dependencies
log_info "Updating Python dependencies..."
if [ -f "$PROD_APP_DIR/requirements_prod.txt" ]; then
    sudo -u whatspy "$VENV_PATH/bin/pip" install -r "$PROD_APP_DIR/requirements_prod.txt" --upgrade
    log_success "Dependencies updated"
else
    log_warning "requirements_prod.txt not found, using requirements.txt"
    sudo -u whatspy "$VENV_PATH/bin/pip" install -r "$PROD_APP_DIR/requirements.txt" --upgrade
fi

# Step 5: Run database migrations (if alembic is set up)
log_info "Running database migrations..."
cd "$PROD_APP_DIR"
if [ -f "alembic.ini" ]; then
    sudo -u whatspy "$VENV_PATH/bin/alembic" upgrade head
    log_success "Database migrations completed"
else
    log_warning "No alembic.ini found, skipping migrations"
fi

# Step 6: Collect static files (if applicable)
# This is optional for FastAPI apps, but good to have
if [ -d "$PROD_APP_DIR/static" ]; then
    log_info "Setting up static files..."
    sudo chown -R whatspy:whatspy "$PROD_APP_DIR/static"
    log_success "Static files configured"
fi

# Step 7: Test configuration
log_info "Testing application configuration..."
cd "$PROD_APP_DIR"
if sudo -u whatspy "$VENV_PATH/bin/python" -c "from app.main import app; print('✅ App configuration is valid')"; then
    log_success "Configuration test passed"
else
    log_error "Configuration test failed!"
    exit 1
fi

# Step 8: Restart the service
log_info "Restarting $SERVICE_NAME service..."
if service_exists "$SERVICE_NAME"; then
    sudo systemctl restart "$SERVICE_NAME"
    
    # Wait a moment for the service to start
    sleep 3
    
    # Check service status
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "$SERVICE_NAME service restarted successfully"
    else
        log_error "$SERVICE_NAME service failed to start!"
        log_error "Service status:"
        sudo systemctl status "$SERVICE_NAME" --no-pager
        exit 1
    fi
else
    log_error "Service $SERVICE_NAME does not exist!"
    log_error "Please run auto_setup_prod.py to create the service."
    exit 1
fi

# Step 9: Reload Nginx (if needed)
log_info "Reloading Nginx..."
if sudo nginx -t; then
    sudo systemctl reload nginx
    log_success "Nginx reloaded successfully"
else
    log_warning "Nginx configuration test failed, but continuing..."
fi

# Step 10: Health check
log_info "Performing health check..."
sleep 5  # Give the service time to fully start

# Try to check if the service is responding
if curl -f -s http://localhost:8000/healthz > /dev/null 2>&1; then
    log_success "Health check passed - Application is responding"
elif curl -f -s http://localhost/healthz > /dev/null 2>&1; then
    log_success "Health check passed - Application is responding via Nginx"
else
    log_warning "Health check failed - Application may still be starting"
    log_info "Check service logs: sudo journalctl -u $SERVICE_NAME -f"
fi

# Step 11: Show service status
log_info "Final service status:"
sudo systemctl status "$SERVICE_NAME" --no-pager -l

echo "=========================================="
log_success "🎉 Deployment completed successfully!"
echo "=========================================="
echo "📊 Service Status: $(sudo systemctl is-active $SERVICE_NAME)"
echo "📝 View logs: sudo journalctl -u $SERVICE_NAME -f"
echo "🌐 Application should be available at your domain"
echo "🔧 If issues occur, check:"
echo "   - Service logs: sudo journalctl -u $SERVICE_NAME -f"
echo "   - Nginx logs: sudo tail -f /var/log/nginx/error.log"
echo "   - Application logs: sudo tail -f /var/log/whatspy/app.log"
echo "=========================================="