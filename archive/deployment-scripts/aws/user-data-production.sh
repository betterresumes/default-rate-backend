#!/bin/bash
set -e

# Redirect all output to log file for debugging
exec > >(tee /var/log/user-data-production.log) 2>&1

echo "=== AccuNode Production API Server Setup Started at $(date) ==="

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

# Configure Docker to login to ECR
echo "🔑 Logging into ECR..."
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 461962182774.dkr.ecr.us-east-1.amazonaws.com

# Pull AccuNode Production Docker image
echo "📥 Pulling AccuNode Production Docker image..."
docker pull 461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest

# Configure Nginx
echo "🌐 Configuring Nginx..."
cat > /etc/nginx/conf.d/accunode.conf << 'EOF'
server {
    listen 80;
    server_name _;
    
    # Health check endpoint for ALB - independent of FastAPI
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    
    # Main application proxy to FastAPI
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
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }
    
    # Static error page for when FastAPI is down
    error_page 502 503 504 /50x.html;
    location = /50x.html {
        root /usr/share/nginx/html;
        internal;
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

# Run AccuNode Production API container
echo "🚀 Starting AccuNode Production API container..."
docker run -d \
  --name accunode-api \
  --restart=unless-stopped \
  -p 127.0.0.1:8000:8000 \
  -e DATABASE_URL="postgresql://accunode_user:accunode123@accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com:5432/accunode" \
  -e REDIS_URL="redis://accunode-redis.d9avr2.0001.use1.cache.amazonaws.com:6379/0" \
  -e ENVIRONMENT="production" \
  -e PORT="8000" \
  -e HOST="0.0.0.0" \
  461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest

# Wait for container to start
echo "⏳ Waiting for container to initialize..."
sleep 45

# Test all endpoints
echo "🧪 Testing all endpoints..."

echo "1. Nginx health check:"
curl -f http://localhost/health || echo "❌ Nginx health check failed"

echo "2. FastAPI direct connection:"
curl -f http://localhost:8000/health || echo "⚠️ FastAPI direct connection failed"

echo "3. Through Nginx proxy:"
curl -f http://localhost/ || echo "⚠️ Nginx proxy failed"

# Show detailed status
echo "📊 System Status:"
echo "Nginx status:"
systemctl status nginx --no-pager -l

echo "Container status:"
docker ps -a

echo "📋 Container Logs:"
docker logs accunode-api --tail 30

echo "🔍 Container health check:"
docker exec accunode-api curl -f http://localhost:8000/health || echo "Container internal health check failed"

# Setup comprehensive log rotation
cat > /etc/logrotate.d/accunode << 'EOF'
/var/log/user-data-production.log {
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
/var/log/nginx/*.log {
    daily
    rotate 52
    copytruncate
    delaycompress
    compress
    notifempty
    missingok
    postrotate
        systemctl reload nginx
    endscript
}
EOF

echo "=== AccuNode Production API Server Setup Completed at $(date) ==="
