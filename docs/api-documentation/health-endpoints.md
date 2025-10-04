# Health Endpoint

GET /health
- Purpose: readiness/liveness for monitoring and ALB checks
- Rate limit: 60/minute

Response shape
{
  "status": "healthy|degraded",
  "timestamp": "2024-01-01T00:00:00Z",
  "service": "default-rate-backend-api",
  "version": "2.0.0",
  "environment": "development|staging|production",
  "services": {
    "database": { "status": "healthy|error", "connected": true },
    "redis": { "status": "healthy|error", "connected": true },
    "ml_models": { "status": "healthy|warning|error", "loaded": true },
    "celery": { "status": "healthy|warning|error", "available": true }
  },
  "system": { "cpu_usage": 0.0, "memory_usage": 0.0, "disk_usage": 0.0 }
}

Behavior
- Returns 200 with status "healthy" or "degraded" depending on component checks.
- Does not raise 5xx on partial failures; consumers should inspect the services block.

Headers
- X-Process-Time added to all responses.
