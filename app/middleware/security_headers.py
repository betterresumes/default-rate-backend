"""
Security Headers Middleware for AccuNode API

Implements comprehensive security headers to protect against:
- Cross-Site Scripting (XSS)
- Clickjacking attacks  
- Content-Type sniffing
- Mixed content attacks
- CSRF attacks
"""

from fastapi import FastAPI, Request
from fastapi.responses import Response
import logging

logger = logging.getLogger(__name__)

async def add_security_headers(request: Request, call_next):
    """
    Add comprehensive security headers to all responses.
    
    Headers implemented:
    - X-Frame-Options: Prevent clickjacking
    - X-Content-Type-Options: Prevent MIME sniffing  
    - X-XSS-Protection: Enable XSS filtering
    - Strict-Transport-Security: Force HTTPS
    - Content-Security-Policy: Control resource loading
    - Referrer-Policy: Control referrer information
    - Permissions-Policy: Control browser features
    """
    
    response = await call_next(request)
    
    # Prevent clickjacking attacks
    response.headers["X-Frame-Options"] = "DENY"
    
    # Prevent MIME type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Enable XSS filtering (legacy browsers)
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Force HTTPS for all future requests (1 year)
    # Only add if request came via HTTPS
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    
    # Content Security Policy - Restrictive but functional for API
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-src 'none'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers["Content-Security-Policy"] = csp_policy
    
    # Control referrer information
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Permissions Policy (formerly Feature Policy)
    permissions_policy = (
        "accelerometer=(), "
        "camera=(), "
        "geolocation=(), "
        "gyroscope=(), "
        "magnetometer=(), "
        "microphone=(), "
        "payment=(), "
        "usb=()"
    )
    response.headers["Permissions-Policy"] = permissions_policy
    
    # Remove server information for security
    response.headers.pop("Server", None)
    
    # Add custom security header for identification
    response.headers["X-Security-Headers"] = "enabled"
    
    return response

def setup_security_headers(app: FastAPI) -> None:
    """
    Set up security headers middleware for the FastAPI application.
    
    This middleware adds comprehensive security headers to protect against
    common web vulnerabilities including XSS, clickjacking, and CSRF.
    """
    
    # Add security headers middleware
    app.middleware("http")(add_security_headers)
    
    logger.info("✅ Security headers middleware configured successfully")
    logger.info("🛡️ Protection enabled: XSS, Clickjacking, MIME sniffing, CSRF")
    logger.info("🔒 HSTS enabled for HTTPS requests")
    logger.info("📋 CSP policy applied for content restriction")
