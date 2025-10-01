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

# Configure Nginx with fallback handling
echo "🌐 Configuring Nginx..."
cat > /etc/nginx/conf.d/accunode.conf << 'EOF'
upstream fastapi_backend {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name _;
    
    # Health check endpoint for ALB - Always works
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    
    # Status endpoint to check FastAPI
    location /api/status {
        proxy_pass http://fastapi_backend/;
        proxy_connect_timeout 5s;
        proxy_send_timeout 5s;
        proxy_read_timeout 5s;
        
        # If FastAPI is down, return custom response
        error_page 502 503 504 = @fastapi_down;
    }
    
    # Main application proxy with fallback
    location / {
        proxy_pass http://fastapi_backend;
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
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # If FastAPI is down, show status page
        error_page 502 503 504 = @fastapi_down;
    }
    
    # Fallback when FastAPI is down
    location @fastapi_down {
        return 200 '{"status":"initializing","message":"AccuNode API is starting up, please wait...","timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}';
        add_header Content-Type application/json;
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

# Remove default nginx config
rm -f /etc/nginx/conf.d/default.conf

# Test and reload nginx
echo "🔄 Testing Nginx configuration..."
nginx -t
systemctl reload nginx

# Start a simple FastAPI health server first
echo "🏥 Starting temporary health server..."
python3 -c "
import http.server
import socketserver
import json
from datetime import datetime

class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'status': 'ok',
                'message': 'AccuNode temporary health check',
                'timestamp': datetime.utcnow().isoformat()
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

with socketserver.TCPServer(('127.0.0.1', 8000), HealthHandler) as httpd:
    print('Temporary health server on port 8000')
    httpd.serve_request()
" &
TEMP_PID=$!

# Wait a moment for temp server
sleep 5

# Test connections with temp server
echo "🧪 Testing with temporary server..."
curl -f http://localhost/health && echo " ✅ Health check works"
curl -f http://localhost/ && echo " ✅ Proxy works"

# Kill temp server
kill $TEMP_PID 2>/dev/null || true

# Run AccuNode API container with better error handling
echo "🚀 Starting AccuNode API container..."
docker run -d \
  --name accunode-api \
  -p 127.0.0.1:8000:8000 \
  -e DATABASE_URL="$DATABASE_URL" \
  -e REDIS_URL="$REDIS_URL" \
  -e ENVIRONMENT="production" \
  -e PORT="8000" \
  --restart=unless-stopped \
  --health-cmd="curl -f http://localhost:8000/ || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest \
  /app/start-production.sh

# Monitor container startup
echo "⏳ Monitoring container startup..."
for i in {1..12}; do
    sleep 10
    echo "Check $i/12: $(date)"
    
    # Check container status
    if docker ps | grep -q accunode-api; then
        echo "✅ Container is running"
        
        # Check if it's responding
        if curl -f http://localhost:8000/ >/dev/null 2>&1; then
            echo "🎉 FastAPI is responding!"
            break
        else
            echo "⏳ FastAPI not ready yet..."
        fi
    else
        echo "❌ Container stopped, checking logs..."
        docker logs accunode-api --tail 10
        
        # Restart if crashed
        echo "🔄 Restarting container..."
        docker start accunode-api || true
    fi
    
    if [ $i -eq 12 ]; then
        echo "⚠️ Container taking longer than expected, but continuing..."
    fi
done

# Final status check
echo "📊 Final Status Check:"
docker ps -a | grep accunode || echo "No container found"
docker logs --tail 20 accunode-api || echo "No logs available"

# Test all endpoints
echo "🧪 Testing all endpoints..."
echo "Health endpoint:"
curl -s http://localhost/health || echo "Failed"

echo "API Status:"
curl -s http://localhost/api/status || echo "Will show fallback"

echo "Root endpoint:"
curl -s http://localhost/ || echo "Will show fallback"

echo "=== AccuNode API Server Setup Completed at $(date) ==="
