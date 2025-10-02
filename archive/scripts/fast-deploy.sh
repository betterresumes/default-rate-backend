#!/bin/bash

# Fast Deploy Script - Hot deployment without full Docker rebuild
# Deploy time: ~30 seconds instead of 5 minutes

set -e

echo "🚀 AccuNode Fast Deploy"
echo "======================"
echo "Deployment started at: $(date)"

# Configuration
ECR_REGISTRY="461962182774.dkr.ecr.us-east-1.amazonaws.com"
REPO_NAME="accunode"
API_INSTANCES=$(aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names AccuNode-API-ASG --query 'AutoScalingGroups[0].Instances[?LifecycleState==`InService`].InstanceId' --output text)
WORKER_INSTANCES=$(aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names AccuNode-Worker-ASG --query 'AutoScalingGroups[0].Instances[?LifecycleState==`InService`].InstanceId' --output text)

# Function to deploy to instances
deploy_to_instances() {
    local instances="$1"
    local service_name="$2"
    
    echo "📦 Deploying to $service_name instances: $instances"
    
    for instance_id in $instances; do
        echo "🔄 Deploying to instance: $instance_id"
        
        # Get instance IP
        instance_ip=$(aws ec2 describe-instances --instance-ids $instance_id --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
        
        if [ "$instance_ip" != "None" ] && [ "$instance_ip" != "" ]; then
            echo "   📡 Connecting to $instance_ip..."
            
            # Hot deployment via SSH
            ssh -o StrictHostKeyChecking=no -i ~/.ssh/AccuNode-Production-Key.pem ec2-user@$instance_ip "
                echo '🔄 Starting hot deployment on $instance_id'
                
                # Method 1: Update code in running container (fastest)
                echo '📝 Method 1: Hot code update...'
                if sudo docker exec accunode-api ls /app/app >/dev/null 2>&1 || sudo docker exec accunode-worker ls /app/app >/dev/null 2>&1; then
                    echo '   📦 Updating application code in running container...'
                    
                    # Create temporary directory for new code
                    sudo mkdir -p /tmp/accunode-deploy
                    cd /tmp/accunode-deploy
                    
                    # Clone latest code (or you can rsync from local)
                    if [ ! -d '.git' ]; then
                        git clone https://github.com/betterresumes/default-rate-backend.git . 2>/dev/null || echo 'Git clone failed, using alternative method'
                    else
                        git pull origin prod 2>/dev/null || echo 'Git pull failed, using alternative method'
                    fi
                    
                    # Copy updated code into running container
                    if sudo docker ps | grep -q accunode-api; then
                        sudo docker cp ./app accunode-api:/app/ 2>/dev/null && echo '   ✅ API code updated'
                        sudo docker cp ./main.py accunode-api:/app/ 2>/dev/null
                        
                        # Restart gunicorn workers (no container restart needed)
                        sudo docker exec accunode-api pkill -HUP gunicorn 2>/dev/null && echo '   ♻️ API workers restarted' || echo '   ℹ️ Worker restart not needed'
                    fi
                    
                    if sudo docker ps | grep -q accunode-worker; then
                        sudo docker cp ./app accunode-worker:/app/ 2>/dev/null && echo '   ✅ Worker code updated'
                        
                        # Restart celery workers gracefully
                        sudo docker exec accunode-worker pkill -TERM celery 2>/dev/null
                        sleep 2
                        sudo docker restart accunode-worker >/dev/null 2>&1 && echo '   ♻️ Celery worker restarted'
                    fi
                    
                else
                    echo '   📦 Method 2: Container restart with new image...'
                    
                    # Get current container image
                    current_image=\$(sudo docker inspect --format='{{.Config.Image}}' accunode-api 2>/dev/null || sudo docker inspect --format='{{.Config.Image}}' accunode-worker 2>/dev/null)
                    
                    # Pull latest image
                    aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin $ECR_REGISTRY
                    sudo docker pull \$current_image
                    
                    # Restart containers with new image
                    if sudo docker ps | grep -q accunode-api; then
                        sudo docker stop accunode-api && sudo docker rm accunode-api
                        sudo docker run -d --name accunode-api -p 8000:8000 \
                            -e DATABASE_URL=\"\$DATABASE_URL\" -e REDIS_URL=\"\$REDIS_URL\" -e ENVIRONMENT=production \
                            \$current_image
                        echo '   ✅ API container restarted'
                    fi
                    
                    if sudo docker ps | grep -q accunode-worker; then
                        sudo docker stop accunode-worker && sudo docker rm accunode-worker
                        sudo docker run -d --name accunode-worker \
                            -e DATABASE_URL=\"\$DATABASE_URL\" -e REDIS_URL=\"\$REDIS_URL\" -e ENVIRONMENT=production \
                            \$current_image celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 --queues=medium_priority
                        echo '   ✅ Worker container restarted'
                    fi
                fi
                
                echo '✅ Deployment completed on $instance_id'
                
                # Health check
                sleep 5
                if curl -f http://localhost:8000/health >/dev/null 2>&1; then
                    echo '✅ Health check passed'
                else
                    echo '⚠️ Health check failed - check logs'
                fi
            " && echo "   ✅ Successfully deployed to $instance_id" || echo "   ❌ Failed to deploy to $instance_id"
        else
            echo "   ⚠️ No public IP found for instance $instance_id"
        fi
        echo
    done
}

# Deploy to API instances
if [ -n "$API_INSTANCES" ]; then
    deploy_to_instances "$API_INSTANCES" "API"
else
    echo "⚠️ No API instances found"
fi

# Deploy to Worker instances  
if [ -n "$WORKER_INSTANCES" ]; then
    deploy_to_instances "$WORKER_INSTANCES" "Worker"
else
    echo "⚠️ No Worker instances found"
fi

echo "🎉 Fast deployment completed at: $(date)"
echo "⏱️ Total deployment time: ~30-60 seconds"
echo
echo "🔍 Verify deployment:"
echo "curl http://AccuNode-ALB-910622084.us-east-1.elb.amazonaws.com/health"
