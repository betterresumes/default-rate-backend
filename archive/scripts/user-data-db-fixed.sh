#!/bin/bash
set -e

# Log everything
exec > >(tee /var/log/user-data.log) 2>&1
echo "Starting AccuNode deployment at $(date)"

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

# Install Nginx first
echo "Installing Nginx..."
amazon-linux-extras install nginx1 -y

# Login to ECR
echo "Logging into ECR..."
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 461962182774.dkr.ecr.us-east-1.amazonaws.com

# Pull the latest Docker image
echo "Pulling AccuNode Docker image..."
docker pull 461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest

# Run the container with corrected database credentials
echo "Starting AccuNode container with correct database URL..."
docker run -d \
  --name accunode-api \
  --restart unless-stopped \
  -p 8000:8000 \
  --health-cmd="curl -f http://localhost:8000/health || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-start-period=40s \
  --health-retries=3 \
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
  -e CORS_ORIGIN='https://accunode.ai,https://client-eta-sepia.vercel.app' \
  -e PYTHONUNBUFFERED='1' \
  -e PYTHONPATH='/app' \
  -e MODEL_PATH='./models/' \
  -e ENABLE_ML_CACHE='true' \
  -e PORT='8000' \
  -e ENVIRONMENT='production' \
  -e AWS_REGION='us-east-1' \
  -e LOG_LEVEL='INFO' \
  461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest

# Wait for container to start
echo "Waiting for AccuNode container to be ready..."
sleep 45

# Check if container is running
if ! docker ps | grep accunode-api > /dev/null; then
    echo "ERROR: AccuNode container failed to start"
    docker logs accunode-api
    exit 1
fi

# Create Nginx configuration
echo "Configuring Nginx..."
cat > /etc/nginx/nginx.conf << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    upstream accunode_backend {
        server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    }

    server {
        listen 80 default_server;
        listen [::]:80 default_server;
        server_name _;

        # Health check endpoint for Load Balancer
        location /health {
            proxy_pass http://accunode_backend/health;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 5s;
            proxy_send_timeout 5s;
            proxy_read_timeout 5s;
            access_log off;
        }

        # Main application
        location / {
            proxy_pass http://accunode_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
            
            # Handle WebSocket connections
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
EOF

# Test nginx configuration
nginx -t
if [ $? -ne 0 ]; then
    echo "ERROR: Nginx configuration test failed"
    exit 1
fi

# Start and enable Nginx
echo "Starting Nginx..."
systemctl start nginx
systemctl enable nginx

# Verify services are running
echo "Verifying services..."
sleep 10

# Test AccuNode API directly
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ AccuNode API is responding on port 8000"
else
    echo "❌ AccuNode API is not responding on port 8000"
    docker logs accunode-api
fi

# Test Nginx proxy
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo "✅ Nginx proxy is working on port 80"
else
    echo "❌ Nginx proxy is not working on port 80"
    systemctl status nginx
fi

echo "AccuNode deployment completed at $(date)"
echo "Container status: $(docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep accunode || echo 'Container not found')"
echo "Nginx status: $(systemctl is-active nginx)"
