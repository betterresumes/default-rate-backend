#!/bin/bash

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 461962182774.dkr.ecr.us-east-1.amazonaws.com

# Pull the latest production image
docker pull 461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:production

# Stop and remove existing container
docker stop accunode-app 2>/dev/null || true
docker rm accunode-app 2>/dev/null || true

# Run the new production container
docker run -d \
  --name accunode-app \
  --restart unless-stopped \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://accunode_user:accunode123@accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com:5432/accunode" \
  -e REDIS_URL="redis://accunode-redis.d9avr2.0001.use1.cache.amazonaws.com:6379" \
  -e ENVIRONMENT="production" \
  461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:production

# Check container status
echo "Container updated. Current status:"
docker ps -a
echo "Container logs:"
docker logs accunode-app --tail 20
