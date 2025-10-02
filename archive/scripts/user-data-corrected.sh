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

# Configure AWS region
export AWS_DEFAULT_REGION=us-east-1

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 461962182774.dkr.ecr.us-east-1.amazonaws.com

# Pull the latest corrected Docker image
docker pull 461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest

# Run the container with production environment variables
docker run -d \
  --name accunode-api \
  --restart unless-stopped \
  -p 8000:8000 \
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
  -e PORT='8000' \
  -e ENVIRONMENT='production' \
  -e AWS_REGION='us-east-1' \
  -e LOG_LEVEL='INFO' \
  461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest

# Install and configure Nginx using Amazon Linux extras
amazon-linux-extras install nginx1 -y

# Create Nginx configuration
cat > /etc/nginx/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream accunode_backend {
        server 127.0.0.1:8000;
    }

    server {
        listen 80;
        server_name _;

        location / {
            proxy_pass http://accunode_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        location /health {
            proxy_pass http://accunode_backend/health;
            proxy_set_header Host $host;
            access_log off;
        }
    }
}
EOF

# Start and enable Nginx
systemctl start nginx
systemctl enable nginx

# Wait for container to be healthy
sleep 30

# Log completion
echo "AccuNode deployment completed successfully!" >> /var/log/user-data.log
