#!/bin/bash
set -e

# Redirect all output to log file
exec > >(tee /var/log/user-data.log) 2>&1

echo "Starting AccuNode API setup at $(date)"

# Update system
echo "Updating system..."
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

# Test AWS connectivity
echo "Testing AWS connectivity..."
aws sts get-caller-identity

# Configure Docker to login to ECR
echo "Logging into ECR..."
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 461962182774.dkr.ecr.us-east-1.amazonaws.com

# Pull AccuNode Docker image
echo "Pulling Docker image..."
docker pull 461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest

# Test Parameter Store access
echo "Testing Parameter Store access..."
aws ssm get-parameter --name "/accunode/database/url" --with-decryption --query 'Parameter.Value' --output text > /tmp/db_test
aws ssm get-parameter --name "/accunode/redis/url" --with-decryption --query 'Parameter.Value' --output text > /tmp/redis_test

# Get configuration from Parameter Store
DATABASE_URL=$(aws ssm get-parameter --name "/accunode/database/url" --with-decryption --query 'Parameter.Value' --output text)
REDIS_URL=$(aws ssm get-parameter --name "/accunode/redis/url" --with-decryption --query 'Parameter.Value' --output text)

echo "Database URL retrieved: ${DATABASE_URL:0:20}..."
echo "Redis URL retrieved: ${REDIS_URL:0:20}..."

# Run AccuNode API container
echo "Starting AccuNode container..."
docker run -d \
  --name accunode-api \
  -p 80:8000 \
  -e DATABASE_URL="$DATABASE_URL" \
  -e REDIS_URL="$REDIS_URL" \
  -e ENVIRONMENT="production" \
  --restart=unless-stopped \
  461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest \
  /app/start-production.sh

# Wait for container to start
echo "Waiting for container to start..."
sleep 30

# Check container status
echo "Container status:"
docker ps -a

# Check container logs
echo "Container logs:"
docker logs accunode-api

# Test local connection
echo "Testing local connection..."
curl -f http://localhost/ || echo "Local connection failed"

# Setup log rotation for docker logs
cat > /etc/logrotate.d/docker-containers << 'EOF'
/var/lib/docker/containers/*/*.log {
  daily
  rotate 7
  copytruncate
  delaycompress
  compress
  notifempty
  missingok
}
EOF

echo "AccuNode API server setup completed at $(date)"
