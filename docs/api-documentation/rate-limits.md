# API Rate Limits

Overview
- Backed by Redis when available, otherwise in-memory fallback.
- Client identity: X-Forwarded-For (first IP) -> X-Real-IP -> requester IP.
- Exceeding limits returns 429 with Retry-After header.

429 response example
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please slow down and try again later.",
  "detail": "100 per minute",
  "retry_after": 60,
  "client_id": "1.2.3.4"
}

Standard headers
- Retry-After: seconds until next allowed request
- X-Process-Time: added to all responses (ms)

Limits by category (exact values from code)
- Authentication: 30/minute
- Authentication (strict ops): 5/minute, 20/hour
- ML predictions (compute): 100/minute
- Prediction data reads: 500/hour, 2000/day
- General data reads: 200/hour, 1000/day
- File uploads: 10/minute, 100/day
- User create: 20/hour, 100/day
- User read: 200/hour, 1000/day
- User update: 50/hour, 200/day
- User delete: 10/hour, 50/day
- Organization create: 20/hour, 100/day
- Organization read: 100/hour, 500/day
- Organization update: 50/hour, 200/day
- Organization delete: 10/hour, 50/day
- Organization token regeneration: 5/hour, 20/day
- Tenant create: 20/hour, 100/day
- Tenant read: 100/hour, 500/day
- Tenant update: 50/hour, 200/day
- Tenant delete: 10/hour, 50/day
- Analytics/Dashboards: 100/hour, 500/day
- Job control: 50/hour, 200/day
- Health checks: 60/minute
- Standard API: 100/hour, 500/day
- Global default (fallback): 1000/day, 100/hour

Notes
- All limits are IP-based by default and work behind load balancers due to forwarded headers.
- Tune Redis via REDIS_URL; when unavailable, in-memory limits reset on restart.
