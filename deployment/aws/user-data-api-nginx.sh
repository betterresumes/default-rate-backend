#!/bin/bash
set -e

# Redirect all output to log file for debugging
exec > >(tee /var/log/user-data.log) 2>&1

echo "=== AccuNode API Server Setup Started at $(date) ==="

# Update system
echo "📦 Updating system..."
yum update -y

# Install Docker and Nginx
echo "🐳 Installing Docker and Nginx..."
yum install -y docker nginx
systemctl start docker nginx
systemctl enable docker nginx
usermod -a -G docker ec2-user

# Install AWS CLI v2
echo "☁️ Installing AWS CLI..."
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

# Test AWS connectivity
echo "🔐 Testing AWS connectivity..."
aws sts get-caller-identity

# Configure Docker to login to ECR
echo "🔑 Logging into ECR..."
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 461962182774.dkr.ecr.us-east-1.amazonaws.com

# Pull AccuNode Docker image
echo "📥 Pulling AccuNode Docker image..."
docker pull 461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest

# Get configuration from Parameter Store
echo "⚙️ Retrieving configuration from Parameter Store..."
DATABASE_URL=$(aws ssm get-parameter --name "/accunode/database/url" --with-decryption --query 'Parameter.Value' --output text)
REDIS_URL=$(aws ssm get-parameter --name "/accunode/redis/url" --with-decryption --query 'Parameter.Value' --output text)

echo "✅ Database URL retrieved: ${DATABASE_URL:0:30}..."
echo "✅ Redis URL retrieved: ${REDIS_URL:0:30}..."

# Configure Nginx
echo "🌐 Configuring Nginx..."
cat > /etc/nginx/conf.d/accunode.conf << 'EOF'
server {
    listen 80;
    server_name _;
    
    # Health check endpoint for ALB
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    
    # Main application proxy
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml;
}
EOF

# Remove default nginx config to avoid conflicts
rm -f /etc/nginx/conf.d/default.conf

# Test and reload nginx
echo "🔄 Testing Nginx configuration..."
nginx -t
systemctl reload nginx

# Run AccuNode API container
echo "🚀 Starting AccuNode API container..."
docker run -d \
  --name accunode-api \
  -p 127.0.0.1:8000:8000 \
  -e DATABASE_URL="$DATABASE_URL" \
  -e REDIS_URL="$REDIS_URL" \
  -e ENVIRONMENT="production" \
  --restart=unless-stopped \
  461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest \
  /app/start-production.sh

# Wait for container to start
echo "⏳ Waiting for container to initialize..."
sleep 30

# Test local connections
echo "🧪 Testing local connections..."
echo "Nginx health check:"
curl -f http://localhost/health || echo "❌ Nginx health check failed"

echo "FastAPI direct:"
curl -f http://localhost:8000/ || echo "❌ FastAPI direct failed"

echo "Through Nginx proxy:"
curl -f http://localhost/ || echo "❌ Nginx proxy failed"

# Show container status and logs
echo "📊 Container Status:"
docker ps -a

echo "📋 Container Logs (last 20 lines):"
docker logs --tail 20 accunode-api

# Setup log rotation
cat > /etc/logrotate.d/accunode << 'EOF'
/var/log/user-data.log {
    daily
    rotate 7
    copytruncate
    delaycompress
    compress
    notifempty
    missingok
}
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

echo "=== AccuNode API Server Setup Completed at $(date) ==="
