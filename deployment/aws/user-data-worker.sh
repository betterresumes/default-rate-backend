#!/bin/bash
set -e

# Update system
yum update -y

# Install Docker
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

# Configure Docker to login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 461962182774.dkr.ecr.us-east-1.amazonaws.com

# Pull AccuNode Docker image
docker pull 461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest

# Get configuration from Parameter Store
DATABASE_URL=$(aws ssm get-parameter --name "/accunode/database/url" --with-decryption --query 'Parameter.Value' --output text)
REDIS_URL=$(aws ssm get-parameter --name "/accunode/redis/url" --with-decryption --query 'Parameter.Value' --output text)

# Run AccuNode Worker container
docker run -d \
  --name accunode-worker \
  -e DATABASE_URL="$DATABASE_URL" \
  -e REDIS_URL="$REDIS_URL" \
  -e ENVIRONMENT="production" \
  --restart=unless-stopped \
  461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest \
  /app/deployment/scripts/start-worker.sh

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

echo "AccuNode Worker server setup completed"
