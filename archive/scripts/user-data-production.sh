#!/bin/bash

# Update system packages
yum update -y

# Install Docker
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
yum install -y unzip
unzip awscliv2.zip
./aws/install

# Install Nginx
amazon-linux-extras install -y nginx1
systemctl start nginx
systemctl enable nginx

# Create Nginx configuration
cat > /etc/nginx/nginx.conf << 'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

include /usr/share/nginx/modules/*.conf;

events {
    worker_connections 1024;
}

http {
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    sendfile            on;
    tcp_nopush          on;
    tcp_nodelay         on;
    keepalive_timeout   65;
    types_hash_max_size 2048;

    include             /etc/nginx/mime.types;
    default_type        application/octet-stream;

    server {
        listen 80;
        server_name _;

        # Health check endpoint (handled by Nginx directly)
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }

        # Proxy all other requests to FastAPI
        location / {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
    }
}
EOF

# Restart Nginx with new configuration
systemctl restart nginx

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 461962182774.dkr.ecr.us-east-1.amazonaws.com

# Pull and run the production Docker container
docker pull 461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:production

# Stop any existing container
docker stop accunode-app 2>/dev/null || true
docker rm accunode-app 2>/dev/null || true

# Run the production container
docker run -d \
  --name accunode-app \
  --restart unless-stopped \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://accunode_user:accunode123@accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com:5432/accunode" \
  -e REDIS_URL="redis://accunode-redis.d9avr2.0001.use1.cache.amazonaws.com:6379" \
  -e ENVIRONMENT="production" \
  461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:production

# Log container status
echo "Container status:" >> /var/log/user-data.log
docker ps -a >> /var/log/user-data.log
docker logs accunode-app >> /var/log/user-data.log 2>&1

echo "User data script completed" >> /var/log/user-data.log
