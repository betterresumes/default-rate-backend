#!/bin/bash
set -e

# Log everything
exec > >(tee /var/log/user-data.log) 2>&1
echo "Starting AccuNode Worker deployment at $(date)"

# Update system
echo "Updating system packages..."
yum update -y

# Install Docker
echo "Installing Docker..."
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install AWS CLI v2
echo "Installing AWS CLI..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

# Configure AWS region
export AWS_DEFAULT_REGION=us-east-1

# Login to ECR
echo "Logging into ECR..."
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 461962182774.dkr.ecr.us-east-1.amazonaws.com

# Pull the latest Docker image
echo "Pulling AccuNode Docker image..."
docker pull 461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest

# Run Celery worker container
echo "Starting AccuNode Celery Worker..."
docker run -d \
  --name accunode-worker \
  --restart unless-stopped \
  -e DATABASE_URL='postgresql://accunode_admin:AccuNode2024!SecurePass@accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com:5432/postgres' \
  -e REDIS_URL='redis://accunode-redis.d9avr2.0001.use1.cache.amazonaws.com:6379' \
  -e REDIS_HOST='accunode-redis.d9avr2.0001.use1.cache.amazonaws.com' \
  -e REDIS_PORT='6379' \
  -e REDIS_PASSWORD='' \
  -e REDIS_DB='0' \
  -e REDISUSER='' \
  -e DEBUG='false' \
  -e SECRET_KEY='accunode-production-secret-key-2024-secure' \
  -e ACCESS_TOKEN_EXPIRE_MINUTES='60' \
  -e CORS_ORIGIN='*' \
  -e PYTHONUNBUFFERED='1' \
  -e PYTHONPATH='/app' \
  -e MODEL_PATH='./models/' \
  -e ENABLE_ML_CACHE='true' \
  -e ENVIRONMENT='production' \
  -e AWS_REGION='us-east-1' \
  -e LOG_LEVEL='INFO' \
  -e C_FORCE_ROOT='1' \
  461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest \
  celery -A app.workers.celery_app worker --loglevel=info --concurrency=2

# Wait for container to start
echo "Waiting for Celery worker to be ready..."
sleep 30

# Check if container is running
if docker ps | grep accunode-worker > /dev/null; then
    echo "✅ AccuNode Celery worker is running"
    docker logs accunode-worker | tail -10
else
    echo "❌ AccuNode Celery worker failed to start"
    docker logs accunode-worker
    exit 1
fi

echo "AccuNode Worker deployment completed at $(date)"
echo "Worker status: $(docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Command}}' | grep accunode || echo 'Worker not found')"
