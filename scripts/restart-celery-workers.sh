#!/bin/bash

# Celery Worker Restart Script for Bulk Upload Task Fix
# This script restarts Celery workers to pick up updated task signatures

echo "🔄 Restarting Celery Workers to Fix Bulk Upload Task Signatures..."
echo "=========================================================="

# Function to check if running in Docker
check_docker() {
    if [ -f /.dockerenv ]; then
        return 0  # Inside Docker container
    elif docker info >/dev/null 2>&1; then
        return 1  # Docker available but not inside container
    else
        return 2  # No Docker
    fi
}

# Function to restart Docker Compose services
restart_docker_compose() {
    echo "📦 Detected Docker environment"
    
    if [ -f "docker-compose.dev.yml" ]; then
        echo "🔧 Using development compose file..."
        docker-compose -f docker-compose.dev.yml restart celery-worker
        echo "✅ Celery worker restarted (development)"
    elif [ -f "docker-compose.yml" ]; then
        echo "🔧 Using production compose file..."
        docker-compose restart celery-worker
        echo "✅ Celery worker restarted (production)"
    else
        echo "❌ No docker-compose.yml found"
        echo "🔧 Trying to restart celery container directly..."
        docker restart $(docker ps -q --filter ancestor=*celery*)
    fi
}

# Function to restart local Celery process
restart_local_celery() {
    echo "🖥️  Restarting local Celery processes..."
    
    # Kill existing Celery processes
    echo "🔪 Killing existing Celery processes..."
    pkill -f celery
    sleep 2
    
    # Check if any processes still running
    if pgrep -f celery > /dev/null; then
        echo "⚠️  Force killing remaining Celery processes..."
        pkill -9 -f celery
        sleep 2
    fi
    
    echo "✅ Celery processes stopped"
    echo ""
    echo "🚀 To start Celery worker again, run:"
    echo "   celery -A app.workers.celery_app worker --loglevel=info"
    echo ""
    echo "🚀 Or with concurrency (recommended):"
    echo "   celery -A app.workers.celery_app worker --loglevel=info --concurrency=4"
}

# Function to restart systemd service
restart_systemd() {
    echo "🐧 Trying systemd service restart..."
    
    if systemctl is-active --quiet celery-worker; then
        sudo systemctl restart celery-worker
        echo "✅ Celery worker restarted via systemd"
        return 0
    elif systemctl is-active --quiet celery; then
        sudo systemctl restart celery
        echo "✅ Celery service restarted via systemd"
        return 0
    else
        echo "❌ No systemd celery service found"
        return 1
    fi
}

# Function to restart supervisor
restart_supervisor() {
    echo "👨‍💼 Trying supervisorctl restart..."
    
    if command -v supervisorctl > /dev/null 2>&1; then
        if supervisorctl status celery-worker > /dev/null 2>&1; then
            supervisorctl restart celery-worker
            echo "✅ Celery worker restarted via supervisor"
            return 0
        elif supervisorctl status celery > /dev/null 2>&1; then
            supervisorctl restart celery
            echo "✅ Celery service restarted via supervisor"
            return 0
        fi
    fi
    
    echo "❌ No supervisor celery service found"
    return 1
}

# Main execution
main() {
    echo "🔍 Detecting environment..."
    
    check_docker
    docker_status=$?
    
    if [ $docker_status -eq 0 ]; then
        echo "🐳 Running inside Docker container"
        restart_local_celery
    elif [ $docker_status -eq 1 ]; then
        echo "🐳 Docker available, checking for compose..."
        restart_docker_compose
    else
        echo "💻 Local environment detected"
        
        # Try different process managers
        if restart_systemd; then
            echo "✅ Restarted via systemd"
        elif restart_supervisor; then
            echo "✅ Restarted via supervisor"  
        else
            echo "🔧 Using direct process restart..."
            restart_local_celery
        fi
    fi
    
    echo ""
    echo "🎯 Verification Commands:"
    echo "   # Check if Celery is running"
    echo "   ps aux | grep celery"
    echo ""
    echo "   # Check registered tasks"
    echo "   celery -A app.workers.celery_app inspect registered"
    echo ""
    echo "   # Monitor worker logs"
    echo "   celery -A app.workers.celery_app events"
    echo ""
    echo "🐛 If issues persist:"
    echo "   1. Check Redis/broker connection"
    echo "   2. Verify task imports in celery_app.py"
    echo "   3. Check worker logs for errors"
    echo ""
    echo "✅ Task signature fix should now be active!"
}

# Run the main function
main
