#!/bin/bash

# AccuNode Live Log Monitor
# Continuous log streaming from both instances

echo "🔴 AccuNode Live Log Monitor"
echo "============================"
echo

# Function to stream API logs
stream_api_logs() {
    echo "🌐 Streaming API Server logs..."
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/AccuNode-Production-Key.pem ec2-user@3.81.112.54 "
        echo '🔴 LIVE API LOGS - $(date)'
        echo '=================='
        sudo docker logs -f --tail 20 accunode-api
    "
}

# Function to stream Worker logs  
stream_worker_logs() {
    echo "⚡ Streaming Celery Worker logs..."
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/AccuNode-Production-Key.pem ec2-user@34.204.78.204 "
        echo '🔴 LIVE WORKER LOGS - $(date)'
        echo '===================='
        sudo docker logs -f --tail 20 accunode-worker
    "
}

# Function to stream both logs in parallel
stream_both_logs() {
    echo "📊 Starting dual log streaming..."
    echo "API logs will show in this terminal"
    echo "Worker logs will show in a new terminal window"
    echo
    
    # Stream API logs in current terminal
    stream_api_logs &
    API_PID=$!
    
    # Stream worker logs in background
    stream_worker_logs &
    WORKER_PID=$!
    
    # Wait for user to stop
    echo "Press Ctrl+C to stop all log streaming..."
    trap "kill $API_PID $WORKER_PID 2>/dev/null; exit 0" INT
    
    wait
}

# Function to show system stats alongside logs
stream_with_stats() {
    echo "📈 Streaming logs with system statistics..."
    
    while true; do
        clear
        echo "🔴 LIVE AccuNode Monitor - $(date)"
        echo "=================================="
        
        # Get quick stats from API instance
        echo "📊 API Instance Status:"
        ssh -o StrictHostKeyChecking=no -i ~/.ssh/AccuNode-Production-Key.pem ec2-user@3.81.112.54 "
            echo 'Container Status:' && sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' --filter name=accunode-api
            echo 'Recent Logs:' && sudo docker logs accunode-api --tail 5 2>/dev/null
        " 2>/dev/null
        
        echo
        echo "📊 Worker Instance Status:"
        ssh -o StrictHostKeyChecking=no -i ~/.ssh/AccuNode-Production-Key.pem ec2-user@34.204.78.204 "
            echo 'Container Status:' && sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' --filter name=accunode-worker
            echo 'Recent Logs:' && sudo docker logs accunode-worker --tail 3 2>/dev/null
        " 2>/dev/null
        
        echo
        echo "Refreshing in 10 seconds... (Ctrl+C to stop)"
        sleep 10
    done
}

# Menu
echo "Choose monitoring option:"
echo "1. Stream API logs only"
echo "2. Stream Worker logs only" 
echo "3. Stream both logs (split view)"
echo "4. Dashboard view (refreshing stats + recent logs)"
echo "5. Exit"
echo

read -p "Enter choice (1-5): " choice

case $choice in
    1)
        stream_api_logs
        ;;
    2)
        stream_worker_logs
        ;;
    3)
        stream_both_logs
        ;;
    4)
        stream_with_stats
        ;;
    5)
        echo "👋 Goodbye!"
        exit 0
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac
