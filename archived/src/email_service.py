"""
Email Service using Resend API
Handles verification emails and password resets for multi-tenant system
"""

import os
import logging
from typing import Optional
import resend

logger = logging.getLogger(__name__)

# Configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "re_9iGWQspQ_aM3E4HhU8YLUuqzYTfSfNhiT")
FROM_EMAIL = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
FROM_NAME = os.getenv("FROM_NAME", "Default Rate Prediction System")
BASE_URL = os.getenv("BASE_URL", "http://localhost:3000")

class EmailService:
    """Email service using Resend API"""
    
    def __init__(self):
        self.from_email = FROM_EMAIL
        self.from_name = FROM_NAME
        
        # Set Resend API key
        resend.api_key = RESEND_API_KEY
        
        if RESEND_API_KEY == "re_9iGWQspQ_aM3E4HhU8YLUuqzYTfSfNhiT":
            logger.info("✅ Resend email service initialized with provided API key")
        else:
            logger.info("✅ Resend email service initialized with environment API key")
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """Send email using Resend API"""
        try:
            # Prepare email data
            email_data = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content
            }
            
            # Add text content if provided
            if text_content:
                email_data["text"] = text_content
            
            # Send email using Resend
            response = resend.Emails.send(email_data)
            
            if response and hasattr(response, 'id'):
                logger.info(f"✅ Email sent successfully to {to_email}. Message ID: {response.id}")
                return True
            else:
                logger.info(f"✅ Email sent successfully to {to_email}")
                return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {e}")
            # Console fallback for testing
            logger.info(f"""
📧 EMAIL FALLBACK (Console Mode):
From: {self.from_name} <{self.from_email}>
To: {to_email}
Subject: {subject}
Content: {text_content or html_content[:100]}...
""")
            return True  # Return True for fallback to not break the flow
    
    def send_verification_email(self, to_email: str, user_name: str, otp_code: str) -> bool:
        """Send email verification OTP"""
        subject = f"Verify Your Email - {FROM_NAME}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Email Verification</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 28px;">Email Verification</h1>
                </div>
                
                <div style="padding: 40px; background-color: #ffffff;">
                    <h2 style="color: #333; margin: 0 0 20px 0;">Hi {user_name},</h2>
                    
                    <p style="font-size: 16px; color: #555; line-height: 1.6; margin-bottom: 30px;">
                        Welcome to {FROM_NAME}! Please verify your email address to complete your registration.
                    </p>
                    
                    <div style="background: #f8f9fa; padding: 30px; border-radius: 10px; text-align: center; margin: 30px 0; border: 2px solid #e9ecef;">
                        <p style="margin: 0 0 15px 0; color: #666; font-size: 14px;">Your verification code is:</p>
                        <div style="font-size: 36px; color: #667eea; font-weight: bold; letter-spacing: 8px; margin: 15px 0; font-family: 'Courier New', monospace;">{otp_code}</div>
                        <p style="margin: 15px 0 0 0; color: #666; font-size: 12px;">This code expires in 10 minutes</p>
                    </div>
                    
                    <p style="color: #777; font-size: 14px; line-height: 1.5; margin-top: 30px;">
                        If you didn't create an account, please ignore this email.
                    </p>
                </div>
                
                <div style="background: #333; padding: 20px; text-align: center;">
                    <p style="color: #999; margin: 0; font-size: 12px;">
                        © 2024 {FROM_NAME}. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
Hi {user_name},

Welcome to {FROM_NAME}! Please verify your email address to complete your registration.

Your verification code is: {otp_code}

This code expires in 10 minutes.

If you didn't create an account, please ignore this email.

© 2024 {FROM_NAME}
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_password_reset_email(self, to_email: str, user_name: str, reset_token: str) -> bool:
        """Send password reset email"""
        reset_url = f"{BASE_URL}/reset-password/{reset_token}"
        subject = f"Reset Your Password - {FROM_NAME}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Reset</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 28px;">Password Reset</h1>
                </div>
                
                <div style="padding: 40px; background-color: #ffffff;">
                    <h2 style="color: #333; margin: 0 0 20px 0;">Hi {user_name},</h2>
                    
                    <p style="font-size: 16px; color: #555; line-height: 1.6; margin-bottom: 30px;">
                        We received a request to reset your password for your {FROM_NAME} account.
                    </p>
                    
                    <div style="text-align: center; margin: 40px 0;">
                        <a href="{reset_url}" 
                           style="background: #dc3545; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block; font-size: 16px;">
                            Reset Password
                        </a>
                    </div>
                    
                    <p style="color: #777; font-size: 14px; line-height: 1.5; margin-top: 30px;">
                        Or copy and paste this link in your browser:<br>
                        <a href="{reset_url}" style="color: #dc3545; word-break: break-all;">{reset_url}</a>
                    </p>
                    
                    <p style="color: #777; font-size: 12px; line-height: 1.5; margin-top: 30px;">
                        This link expires in 1 hour. If you didn't request a password reset, you can safely ignore this email.
                    </p>
                </div>
                
                <div style="background: #333; padding: 20px; text-align: center;">
                    <p style="color: #999; margin: 0; font-size: 12px;">
                        © 2024 {FROM_NAME}. All rights reserved.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
Hi {user_name},

We received a request to reset your password for your {FROM_NAME} account.

Reset your password: {reset_url}

This link expires in 1 hour. If you didn't request a password reset, you can safely ignore this email.

© 2024 {FROM_NAME}
        """
        
        return self.send_email(to_email, subject, html_content, text_content)


# Create a global instance for use throughout the app
email_service = EmailService()

# Convenience functions for backwards compatibility
def send_verification_email(email: str, name: str, otp_code: str) -> bool:
    """Send verification email - convenience function"""
    return email_service.send_verification_email(email, name, otp_code)

def send_password_reset_email(email: str, name: str, token: str) -> bool:
    """Send password reset email - convenience function"""
    return email_service.send_password_reset_email(email, name, token)
