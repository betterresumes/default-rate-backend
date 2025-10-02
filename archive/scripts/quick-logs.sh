#!/bin/bash

# Quick Live Logs - Simple continuous streaming
# Usage: ./quick-logs.sh [api|worker|both]

LOG_TYPE=${1:-both}

case $LOG_TYPE in
    "api")
        echo "🔴 STREAMING API LOGS (Ctrl+C to stop)"
        echo "======================================"
        ssh -o StrictHostKeyChecking=no -i ~/.ssh/AccuNode-Production-Key.pem ec2-user@3.81.112.54 \
            "sudo docker logs -f --tail 50 accunode-api"
        ;;
    "worker")
        echo "🔴 STREAMING WORKER LOGS (Ctrl+C to stop)"
        echo "========================================"
        ssh -o StrictHostKeyChecking=no -i ~/.ssh/AccuNode-Production-Key.pem ec2-user@34.204.78.204 \
            "sudo docker logs -f --tail 50 accunode-worker"
        ;;
    "both")
        echo "🔴 STREAMING BOTH LOGS (Ctrl+C to stop)"
        echo "======================================"
        echo "API logs will be prefixed with [API]"
        echo "Worker logs will be prefixed with [WORKER]"
        echo
        
        # Stream API logs with prefix
        ssh -o StrictHostKeyChecking=no -i ~/.ssh/AccuNode-Production-Key.pem ec2-user@3.81.112.54 \
            "sudo docker logs -f --tail 20 accunode-api | sed 's/^/[API] /'" &
        
        # Stream Worker logs with prefix  
        ssh -o StrictHostKeyChecking=no -i ~/.ssh/AccuNode-Production-Key.pem ec2-user@34.204.78.204 \
            "sudo docker logs -f --tail 20 accunode-worker | sed 's/^/[WORKER] /'" &
        
        # Wait for both processes
        wait
        ;;
    *)
        echo "Usage: $0 [api|worker|both]"
        echo "  api    - Stream API server logs only"
        echo "  worker - Stream Celery worker logs only" 
        echo "  both   - Stream both logs with prefixes"
        exit 1
        ;;
esac
