"""
Contact API endpoints for handling contact form submissions.
Includes rate limiting and security measures.
"""

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
from datetime import datetime
import uuid
from typing import Optional

from app.schemas.schemas import ContactFormRequest, ContactFormResponse
from app.services.email_service import email_service

# Setup logging
logger = logging.getLogger(__name__)

# Setup rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create router
router = APIRouter(prefix="/contact", tags=["Contact"])

# Rate limit exceeded handler will be handled by the main app


async def send_contact_email_background(
    name: str,
    email: str,
    subject: str,
    message: str,
    user_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    reference_id: Optional[str] = None
):
    """Background task to send contact form email"""
    try:
        success = await email_service.send_contact_form_email(
            name=name,
            email=email,
            subject=subject,
            message=message,
            user_ip=user_ip,
            user_agent=user_agent
        )
        
        if success:
            logger.info(f"✅ Contact email sent successfully (ref: {reference_id})")
        else:
            logger.error(f"❌ Failed to send contact email (ref: {reference_id})")
            
    except Exception as e:
        logger.error(f"❌ Background email task failed (ref: {reference_id}): {e}")


@router.post("/submit", response_model=ContactFormResponse)
@limiter.limit("5/minute")  # Allow 5 submissions per minute per IP
async def submit_contact_form(
    request: Request,
    contact_data: ContactFormRequest,
    background_tasks: BackgroundTasks
) -> ContactFormResponse:
    """
    Submit a contact form message.
    
    This endpoint accepts contact form submissions and sends them via email.
    Rate limited to prevent spam (5 submissions per minute per IP address).
    
    Args:
        contact_data: Contact form data including name, email, subject, and message
    
    Returns:
        ContactFormResponse: Success/failure status with message
    
    Raises:
        HTTPException: If validation fails or server error occurs
    """
    try:
        # Generate reference ID for tracking
        reference_id = f"cf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        # Get client info for logging/security
        client_ip = get_remote_address(request)
        user_agent = request.headers.get("user-agent", "Unknown")
        
        logger.info(f"📧 Contact form submission (ref: {reference_id})")
        logger.info(f"   From: {contact_data.name} <{contact_data.email}>")
        logger.info(f"   Subject: {contact_data.subject}")
        logger.info(f"   IP: {client_ip}")
        
        # Add email sending to background tasks
        background_tasks.add_task(
            send_contact_email_background,
            name=contact_data.name,
            email=contact_data.email,
            subject=contact_data.subject,
            message=contact_data.message,
            user_ip=client_ip,
            user_agent=user_agent,
            reference_id=reference_id
        )
        
        # Return immediate response
        return ContactFormResponse(
            success=True,
            message="Your message has been sent successfully! We'll get back to you soon.",
            reference_id=reference_id
        )
        
    except Exception as e:
        logger.error(f"❌ Contact form submission failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your message. Please try again later."
        )


@router.get("/test-email")
async def test_email_configuration() -> dict:
    """
    Test email configuration (development/admin use only).
    
    Returns:
        dict: Email configuration test results
    """
    try:
        # Test SMTP connection
        connection_result = await email_service.test_connection()
        
        return {
            "email_service": "operational" if connection_result["success"] else "error",
            "smtp_test": connection_result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Email test failed: {e}")
        return {
            "email_service": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.post("/test-send")
async def test_send_email(
    background_tasks: BackgroundTasks,
    test_email: str = "test@example.com"
) -> dict:
    """
    Send a test contact form email (development/admin use only).
    
    Args:
        test_email: Email address to use as sender in test
    
    Returns:
        dict: Test email sending results
    """
    try:
        reference_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Add test email to background tasks
        background_tasks.add_task(
            send_contact_email_background,
            name="Test User",
            email=test_email,
            subject="Test Contact Form Submission",
            message="This is a test message from the contact form API endpoint.",
            user_ip="127.0.0.1",
            user_agent="Test Agent",
            reference_id=reference_id
        )
        
        return {
            "success": True,
            "message": "Test email queued for sending",
            "reference_id": reference_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Test email send failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
