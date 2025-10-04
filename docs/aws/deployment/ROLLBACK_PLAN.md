# 🚨 ROLLBACK PLAN - Production Service Recovery

## Current Working Configuration (SAVE THIS!)
**Date**: October 3, 2025
**Status**: ✅ VERIFIED WORKING

### Current Production Services:
- **API Service**: `accunode-api:7` (HEALTHY & RUNNING)
- **Worker Service**: `accunode-worker:6` (RUNNING)
- **Cluster**: `AccuNode-Production`

### Images Currently in Use:
- API: `461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest`
- Worker: `461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest`

## 🔄 ROLLBACK COMMANDS (If Testing Fails):

### Option 1: Rollback to Current Working Task Definitions
```bash
# Rollback API service to working version
aws ecs update-service \
  --cluster AccuNode-Production \
  --service accunode-api-service \
  --task-definition accunode-api:7

# Rollback Worker service to working version  
aws ecs update-service \
  --cluster AccuNode-Production \
  --service accunode-worker-service \
  --task-definition accunode-worker:6
```

### Option 2: Force Service Restart (If services become unhealthy)
```bash
# Force restart API service
aws ecs update-service \
  --cluster AccuNode-Production \
  --service accunode-api-service \
  --force-new-deployment

# Force restart Worker service
aws ecs update-service \
  --cluster AccuNode-Production \
  --service accunode-worker-service \
  --force-new-deployment
```

### Option 3: Scale Down and Back Up (Emergency reset)
```bash
# Scale down to 0
aws ecs update-service --cluster AccuNode-Production --service accunode-api-service --desired-count 0
aws ecs update-service --cluster AccuNode-Production --service accunode-worker-service --desired-count 0

# Wait 30 seconds, then scale back up
sleep 30

aws ecs update-service --cluster AccuNode-Production --service accunode-api-service --desired-count 1
aws ecs update-service --cluster AccuNode-Production --service accunode-worker-service --desired-count 1
```

## 📊 Health Check Commands:
```bash
# Check service status
aws ecs describe-services --cluster AccuNode-Production --services accunode-api-service accunode-worker-service --query 'services[*].[serviceName,taskDefinition,runningCount,desiredCount,status]' --output table

# Check task health
aws ecs list-tasks --cluster AccuNode-Production --service-name accunode-api-service
aws ecs list-tasks --cluster AccuNode-Production --service-name accunode-worker-service
```

## 🏷️ Current Working Images (Backup Reference):
- **Latest Working**: `accunode:latest` (used in task definitions 7 & 6)
- **Testing Image**: `accunode:testing-image` (clean codebase - ready for testing)

## ⚠️ IMPORTANT NOTES:
1. **ALWAYS** test with `accunode:testing-image` first before updating production
2. Current services (accunode-api:7, accunode-worker:6) are **VERIFIED WORKING**
3. Keep this file as reference during any updates
4. If quarterly processing fails, immediately rollback using Option 1 above

## 📋 Testing Checklist Before Updates:
- [ ] API health check passes
- [ ] Worker processes tasks correctly  
- [ ] Quarterly bulk upload works (main concern)
- [ ] No memory/CPU issues
- [ ] Database connections stable
