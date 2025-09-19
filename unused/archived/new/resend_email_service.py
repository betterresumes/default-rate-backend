import os
import httpx
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ResendEmailService:
    """Fast, reliable email service using Resend API"""
    
    def __init__(self):
        self.api_key = os.getenv("RESEND_API_KEY")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@yourdomain.com")
        self.from_name = os.getenv("FROM_NAME", "Default Rate Platform")
        self.base_url = "https://api.resend.com"
        
    async def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email via Resend API"""
        try:
            if not self.api_key:
                logger.error("RESEND_API_KEY not configured!")
                # Development fallback
                if os.getenv("DEBUG", "false").lower() == "true":
                    logger.warning("DEBUG MODE: Email simulation")
                    print(f"\n📧 EMAIL SIMULATION - {to_email}")
                    print(f"Subject: {subject}")
                    # Extract OTP if present
                    import re
                    otp_match = re.search(r'(\d{6})', html_content)
                    if otp_match:
                        print(f"🔑 OTP: {otp_match.group(1)}")
                    print("="*50)
                    return True
                return False
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/emails",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": f"{self.from_name} <{self.from_email}>",
                        "to": [to_email],
                        "subject": subject,
                        "html": html_content
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Email sent successfully to {to_email}")
                    return True
                else:
                    logger.error(f"Failed to send email: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Email sending failed: {str(e)}")
            return False
    
    async def send_invitation_email(self, to_email: str, org_name: str, invitation_link: str, inviter_name: str) -> bool:
        """Send organization invitation email"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Invitation to {org_name}</title>
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px; text-align: center; margin-bottom: 30px;">
                <h1 style="margin: 0; font-size: 28px;">You're Invited!</h1>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Join {org_name} on Default Rate Platform</p>
            </div>
            
            <div style="padding: 20px; background-color: #f8f9fa; border-radius: 8px; margin-bottom: 20px;">
                <p style="font-size: 16px; color: #333; margin: 0 0 15px 0;">Hello!</p>
                <p style="font-size: 16px; color: #333; margin: 0 0 15px 0;">
                    <strong>{inviter_name}</strong> has invited you to join <strong>{org_name}</strong> on our Default Rate Analysis Platform.
                </p>
                <p style="font-size: 16px; color: #333; margin: 0;">
                    Click the button below to accept the invitation:
                </p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{invitation_link}" 
                   style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; 
                          padding: 15px 30px; 
                          text-decoration: none; 
                          border-radius: 8px; 
                          font-size: 16px; 
                          font-weight: bold;
                          display: inline-block;">
                    Accept Invitation
                </a>
            </div>
            
            <div style="padding: 20px; background-color: #fff3cd; border-radius: 8px; margin: 20px 0;">
                <p style="font-size: 14px; color: #856404; margin: 0;">
                    ⏰ This invitation expires in 7 days.
                </p>
            </div>
            
            <div style="border-top: 1px solid #eee; padding-top: 20px; margin-top: 30px;">
                <p style="font-size: 12px; color: #666; margin: 0;">
                    If you didn't expect this invitation, you can safely ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(
            to_email=to_email,
            subject=f"Invitation to join {org_name}",
            html_content=html_content
        )
    
    async def send_verification_email(self, to_email: str, username: str, otp: str) -> bool:
        """Send email verification OTP"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Verify Your Email</title>
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 30px; border-radius: 8px; text-align: center; margin-bottom: 30px;">
                <h1 style="margin: 0; font-size: 28px;">Verify Your Email</h1>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">Default Rate Platform</p>
            </div>
            
            <div style="padding: 20px; background-color: #f8f9fa; border-radius: 8px; margin-bottom: 20px;">
                <p style="font-size: 16px; color: #333; margin: 0 0 15px 0;">Hello {username}!</p>
                <p style="font-size: 16px; color: #333; margin: 0 0 15px 0;">
                    Please use the following verification code to complete your registration:
                </p>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                           color: white; 
                           padding: 20px; 
                           border-radius: 8px; 
                           display: inline-block;
                           font-size: 32px; 
                           font-weight: bold;
                           letter-spacing: 8px;
                           font-family: monospace;">
                    {otp}
                </div>
            </div>
            
            <div style="padding: 20px; background-color: #fff3cd; border-radius: 8px; margin: 20px 0;">
                <p style="font-size: 14px; color: #856404; margin: 0;">
                    ⏰ This code expires in 10 minutes for security.
                </p>
            </div>
            
            <div style="border-top: 1px solid #eee; padding-top: 20px; margin-top: 30px;">
                <p style="font-size: 12px; color: #666; margin: 0;">
                    If you didn't create an account, you can safely ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(
            to_email=to_email,
            subject="Verify your email address",
            html_content=html_content
        )

# Global instance
resend_email_service = ResendEmailService()
