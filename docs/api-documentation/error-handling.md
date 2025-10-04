# Error Handling

Validation errors (422)
- Custom format from middleware
{
  "success": false,
  "error": "Validation failed",
  "message": "Please check the following fields and try again:",
  "errors": [
    { "field": "email", "message": "Please enter a valid email address" }
  ]
}

Standard HTTP exceptions
- Structure: { "detail": "message" }
- Common statuses: 400 (bad request), 401 (unauthorized), 403 (forbidden), 404 (not found), 409 (conflict), 500 (server error)

Rate limit exceeded (429)
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. Please slow down and try again later.",
  "detail": "<limit>",
  "retry_after": 60,
  "client_id": "abc123..."
}
Headers
- Retry-After: present on 429
- X-Process-Time: present on all responses

Notes
- Some successful operations return simple { "message": "..." } bodies.
- Error text originates from explicit HTTPException usage inside routers.
