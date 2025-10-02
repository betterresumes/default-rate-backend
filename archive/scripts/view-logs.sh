#!/bin/bash

# AccuNode Log Viewer Script
# Easy access to CloudWatch logs without SSH

echo "🔍 AccuNode Log Viewer"
echo "======================"

# Function to show log options
show_menu() {
    echo
    echo "Select log source:"
    echo "1. API Server logs (last 50 lines)"
    echo "2. Celery Worker logs (last 50 lines)"
    echo "3. Nginx logs (last 50 lines)"
    echo "4. API Server logs (live streaming)"
    echo "5. Worker logs (live streaming)"
    echo "6. All logs summary"
    echo "7. Search logs for specific term"
    echo "8. Exit"
    echo
    read -p "Enter your choice (1-8): " choice
}

# Function to get recent logs
get_recent_logs() {
    local log_group=$1
    local lines=${2:-50}
    
    echo "📋 Recent logs from $log_group:"
    echo "================================="
    
    aws logs tail $log_group --since 1h --format short --region us-east-1 | tail -n $lines
    
    echo
    echo "To view in AWS Console: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$(echo $log_group | sed 's/\//%252F/g')"
}

# Function to stream logs
stream_logs() {
    local log_group=$1
    
    echo "📡 Streaming logs from $log_group (Press Ctrl+C to stop):"
    echo "========================================================="
    
    aws logs tail $log_group --follow --format short --region us-east-1
}

# Function to search logs
search_logs() {
    read -p "Enter search term: " search_term
    read -p "Search in (api/worker/nginx/all): " log_type
    
    case $log_type in
        "api")
            log_groups=("/accunode/api")
            ;;
        "worker")
            log_groups=("/accunode/worker")
            ;;
        "nginx")
            log_groups=("/accunode/nginx")
            ;;
        "all")
            log_groups=("/accunode/api" "/accunode/worker" "/accunode/nginx")
            ;;
        *)
            echo "Invalid option"
            return
            ;;
    esac
    
    echo "🔍 Searching for '$search_term' in logs..."
    echo "=========================================="
    
    for log_group in "${log_groups[@]}"; do
        echo
        echo "📁 Results from $log_group:"
        aws logs filter-log-events --log-group-name "$log_group" \
            --filter-pattern "$search_term" \
            --start-time $(date -d '1 hour ago' +%s)000 \
            --region us-east-1 \
            --query 'events[*].[eventTimestamp,message]' \
            --output table 2>/dev/null || echo "No results found in $log_group"
    done
}

# Function to show summary
show_summary() {
    echo "📊 AccuNode System Summary"
    echo "=========================="
    
    # Check if log groups exist
    echo "📋 Available log groups:"
    aws logs describe-log-groups --log-group-name-prefix "/accunode" --region us-east-1 \
        --query 'logGroups[*].[logGroupName,storedBytes,retentionInDays]' --output table
    
    echo
    echo "🕐 Recent activity (last 10 minutes):"
    
    for log_group in "/accunode/api" "/accunode/worker" "/accunode/nginx"; do
        echo
        echo "📁 $log_group:"
        aws logs filter-log-events --log-group-name "$log_group" \
            --start-time $(date -d '10 minutes ago' +%s)000 \
            --region us-east-1 \
            --query 'length(events)' --output text 2>/dev/null | \
            xargs -I {} echo "  {} log events in last 10 minutes"
    done
}

# Main menu loop
while true; do
    show_menu
    
    case $choice in
        1)
            get_recent_logs "/accunode/api"
            ;;
        2)
            get_recent_logs "/accunode/worker"
            ;;
        3)
            get_recent_logs "/accunode/nginx"
            ;;
        4)
            stream_logs "/accunode/api"
            ;;
        5)
            stream_logs "/accunode/worker"
            ;;
        6)
            show_summary
            ;;
        7)
            search_logs
            ;;
        8)
            echo "👋 Goodbye!"
            exit 0
            ;;
        *)
            echo "❌ Invalid option. Please try again."
            ;;
    esac
    
    echo
    read -p "Press Enter to continue..."
done
