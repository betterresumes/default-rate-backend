"""
Rate limiting middleware for AccuNode API security protection.

Implements comprehensive rate limiting to prevent:
- DDoS attacks
- Brute force login attempts  
- API abuse
- Resource exhaustion
"""

import os
import redis
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

# Redis connection for rate limit storage
def get_redis_client():
    """Get Redis client for rate limiting storage"""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        # Parse Redis URL components for connection
        if redis_url.startswith("redis://"):
            redis_client = redis.from_url(redis_url, decode_responses=True)
        else:
            # Fallback to individual components
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", 6379))
            redis_db = int(os.getenv("REDIS_DB", 0))
            redis_password = os.getenv("REDIS_PASSWORD", None)
            
            redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password if redis_password else None,
                decode_responses=True
            )
        
        # Test connection
        redis_client.ping()
        logger.info("✅ Rate limiting Redis connection established")
        return redis_client
        
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed for rate limiting: {e}")
        logger.info("🔄 Falling back to in-memory rate limiting")
        return None

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,  # Rate limit by IP address
    storage_uri=None,  # Will be set dynamically
    default_limits=["1000 per day", "100 per hour"]  # Global fallback limits
)

# Set storage dynamically
redis_client = get_redis_client()
if redis_client:
    limiter.storage_uri = f"redis://{redis_client.connection_pool.connection_kwargs.get('host', 'localhost')}:{redis_client.connection_pool.connection_kwargs.get('port', 6379)}/1"

def get_client_identifier(request: Request) -> str:
    """
    Get client identifier for rate limiting.
    Uses IP address as the primary identifier.
    """
    # Try to get real IP from headers (load balancer forwarded)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get first IP in case of multiple proxies
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"

def setup_rate_limiting(app: FastAPI) -> None:
    """
    Set up comprehensive rate limiting for the FastAPI application.
    
    Rate Limiting Strategy:
    - General API: 1000/day, 100/hour, 10/minute
    - Authentication: 5/minute, 20/hour (stricter for brute force protection)
    - File uploads: 10/hour (resource intensive)
    - Health checks: 60/minute (monitoring needs)
    """
    
    # Override the key function to use our custom identifier
    limiter.key_func = lambda request: get_client_identifier(request)
    
    # Add middleware
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    
    # Custom rate limit exceeded handler
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        client_id = get_client_identifier(request)
        path = request.url.path
        
        logger.warning(
            f"🚫 Rate limit exceeded - Client: {client_id}, Path: {path}, "
            f"Limit: {exc.detail}"
        )
        
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please slow down and try again later.",
                "detail": exc.detail,
                "retry_after": getattr(exc, 'retry_after', 60),
                "client_id": client_id[:8] + "..." if len(client_id) > 8 else client_id  # Partial ID for security
            },
            headers={"Retry-After": str(getattr(exc, 'retry_after', 60))}
        )
    
    logger.info("✅ Rate limiting middleware configured successfully")

# Rate limiting decorators for different endpoint types
def rate_limit_auth(func):
    """Rate limit for authentication endpoints (stricter limits)"""
    return limiter.limit("30/minute")(func)

def rate_limit_auth_strict(func):
    """Rate limit for critical auth operations like password changes"""
    return limiter.limit("5/minute,20/hour")(func)

def rate_limit_ml(func):
    """Rate limit for ML prediction endpoints (compute intensive)"""
    return limiter.limit("100/minute")(func)

def rate_limit_upload(func):
    """Rate limit for file upload endpoints (resource intensive)"""
    return limiter.limit("10/minute,100/day")(func)

def rate_limit_user_create(func):
    """Rate limit for user creation endpoints"""
    return limiter.limit("20/hour,100/day")(func)

def rate_limit_user_read(func):
    """Rate limit for user read operations"""
    return limiter.limit("200/hour,1000/day")(func)

def rate_limit_user_update(func):
    """Rate limit for user update operations"""
    return limiter.limit("50/hour,200/day")(func)

def rate_limit_user_delete(func):
    """Rate limit for user delete operations"""
    return limiter.limit("10/hour,50/day")(func)

def rate_limit_org_create(func):
    """Rate limit for organization creation"""
    return limiter.limit("20/hour,100/day")(func)

def rate_limit_org_read(func):
    """Rate limit for organization read operations"""
    return limiter.limit("100/hour,500/day")(func)

def rate_limit_org_update(func):
    """Rate limit for organization update operations"""
    return limiter.limit("50/hour,200/day")(func)

def rate_limit_org_delete(func):
    """Rate limit for organization delete operations"""
    return limiter.limit("10/hour,50/day")(func)

def rate_limit_org_token(func):
    """Rate limit for token regeneration (security sensitive)"""
    return limiter.limit("5/hour,20/day")(func)

def rate_limit_tenant_create(func):
    """Rate limit for tenant creation"""
    return limiter.limit("20/hour,100/day")(func)

def rate_limit_tenant_read(func):
    """Rate limit for tenant read operations"""
    return limiter.limit("100/hour,500/day")(func)

def rate_limit_tenant_update(func):
    """Rate limit for tenant update operations"""
    return limiter.limit("50/hour,200/day")(func)

def rate_limit_tenant_delete(func):
    """Rate limit for tenant delete operations"""
    return limiter.limit("10/hour,50/day")(func)

def rate_limit_data_read(func):
    """Rate limit for data read operations"""
    return limiter.limit("200/hour,1000/day")(func)

def rate_limit_analytics(func):
    """Rate limit for analytics/dashboard operations"""
    return limiter.limit("100/hour,500/day")(func)

def rate_limit_job_control(func):
    """Rate limit for job control operations"""
    return limiter.limit("50/hour,200/day")(func)

def rate_limit_health(func):
    """Rate limit for health check endpoints (monitoring needs)"""
    return limiter.limit("60/minute")(func)

def rate_limit_api(func):
    """Standard rate limit for regular API endpoints"""
    return limiter.limit("100/hour,500/day")(func)
