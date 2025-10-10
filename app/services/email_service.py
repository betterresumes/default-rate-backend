"""
Email service for handling SMTP operations and email templates.
Supports both local development and production environments.
"""

import asyncio
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from pathlib import Path
import aiosmtplib
from jinja2 import Environment, FileSystemLoader, Template
from app.core.config import get_config

logger = logging.getLogger(__name__)

class EmailService:
    """Async email service using aiosmtplib for SMTP operations."""
    
    def __init__(self):
        self.config = get_config()
        self.smtp_host = self.config.SMTP_HOST
        self.smtp_port = self.config.SMTP_PORT
        self.smtp_username = self.config.SMTP_USERNAME
        self.smtp_password = self.config.SMTP_PASSWORD
        self.smtp_tls = self.config.SMTP_TLS
        self.smtp_ssl = self.config.SMTP_SSL
        self.email_from = self.config.EMAIL_FROM
        self.email_from_name = self.config.EMAIL_FROM_NAME
        
        # Setup Jinja2 for email templates
        templates_dir = Path(__file__).parent.parent / "templates" / "email"
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(templates_dir)),
                autoescape=True
            )
        except Exception as e:
            logger.warning(f"Could not setup Jinja2 templates: {e}")
            self.jinja_env = None
    
    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None
    ) -> bool:
        """
        Send an email using SMTP.
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text content (optional)
            from_email: Sender email (uses config default if None)
            from_name: Sender name (uses config default if None)
        
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Validate configuration
            if not self.smtp_username or not self.smtp_password:
                logger.error("SMTP credentials not configured")
                return False
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{from_name or self.email_from_name} <{from_email or self.email_from}>"
            message["To"] = ", ".join(to_emails)
            
            # Add text content
            if text_content:
                text_part = MIMEText(text_content, "plain", "utf-8")
                message.attach(text_part)
            
            # Add HTML content
            html_part = MIMEText(html_content, "html", "utf-8")
            message.attach(html_part)
            
            # Send email
            await self._send_smtp_email(message, to_emails)
            
            logger.info(f"✅ Email sent successfully to {', '.join(to_emails)}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            return False
    
    async def _send_smtp_email(self, message: MIMEMultipart, to_emails: List[str]):
        """Send email using SMTP with proper connection handling."""
        smtp_client = aiosmtplib.SMTP(
            hostname=self.smtp_host,
            port=self.smtp_port,
            use_tls=self.smtp_ssl,
            start_tls=self.smtp_tls
        )
        
        try:
            await smtp_client.connect()
            
            if self.smtp_username and self.smtp_password:
                await smtp_client.login(self.smtp_username, self.smtp_password)
            
            await smtp_client.send_message(message)
            
        finally:
            if smtp_client.is_connected:
                await smtp_client.quit()
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render an email template with context data.
        
        Args:
            template_name: Name of the template file
            context: Context data for template rendering
        
        Returns:
            str: Rendered template content
        """
        if not self.jinja_env:
            logger.warning("Jinja2 not configured, using fallback template")
            return self._fallback_template(template_name, context)
        
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(context)
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            return self._fallback_template(template_name, context)
    
    def _fallback_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Fallback template when Jinja2 is not available."""
        if template_name == "contact_form.html":
            return f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #2c3e50;">New Contact Form Submission</h2>
                        <div style="background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                            <p><strong>Name:</strong> {context.get('name', 'Not provided')}</p>
                            <p><strong>Email:</strong> {context.get('email', 'Not provided')}</p>
                            <p><strong>Subject:</strong> {context.get('subject', 'General Inquiry')}</p>
                            <p><strong>Message:</strong></p>
                            <div style="background: white; padding: 15px; border-left: 3px solid #3498db; margin-top: 10px;">
                                {context.get('message', '').replace(chr(10), '<br>')}
                            </div>
                        </div>
                        <p style="color: #7f8c8d; font-size: 0.9em;">
                            This email was sent from the AccuNode contact form at {context.get('timestamp', 'Unknown time')}.
                        </p>
                    </div>
                </body>
            </html>
            """
        return f"<p>Template {template_name} not found. Context: {context}</p>"
    
    async def send_contact_form_email(
        self,
        name: str,
        email: str,
        subject: str,
        message: str,
        user_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Send contact form submission email.
        
        Args:
            name: Sender's name
            email: Sender's email
            subject: Email subject
            message: Message content
            user_ip: User's IP address (optional)
            user_agent: User's user agent (optional)
        
        Returns:
            bool: True if email was sent successfully
        """
        try:
            from datetime import datetime
            
            # Prepare template context
            context = {
                'name': name,
                'email': email,
                'subject': subject,
                'message': message,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
                'user_ip': user_ip,
                'user_agent': user_agent
            }
            
            # Render email content
            html_content = self.render_template("contact_form.html", context)
            
            # Create text version
            text_content = f"""
New Contact Form Submission

Name: {name}
Email: {email}
Subject: {subject}

Message:
{message}

Submitted at: {context['timestamp']}
            """.strip()
            
            # Prepare email details - Include user name in subject
            email_subject = f"{self.config.EMAIL_SUBJECT_PREFIX} [{name}] {subject}"
            to_emails = [self.config.EMAIL_TO]
            
            # Send email
            return await self.send_email(
                to_emails=to_emails,
                subject=email_subject,
                html_content=html_content,
                text_content=text_content
            )
            
        except Exception as e:
            logger.error(f"Failed to send contact form email: {e}")
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test SMTP connection and return status.
        
        Returns:
            Dict with connection status and details
        """
        try:
            if not self.smtp_username or not self.smtp_password:
                return {
                    "success": False,
                    "error": "SMTP credentials not configured",
                    "details": {
                        "smtp_host": self.smtp_host,
                        "smtp_port": self.smtp_port,
                        "has_username": bool(self.smtp_username),
                        "has_password": bool(self.smtp_password)
                    }
                }
            
            smtp_client = aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=self.smtp_ssl,
                start_tls=self.smtp_tls
            )
            
            await smtp_client.connect()
            await smtp_client.login(self.smtp_username, self.smtp_password)
            await smtp_client.quit()
            
            return {
                "success": True,
                "message": "SMTP connection successful",
                "details": {
                    "smtp_host": self.smtp_host,
                    "smtp_port": self.smtp_port,
                    "smtp_username": self.smtp_username[:3] + "***" if self.smtp_username else None,
                    "smtp_tls": self.smtp_tls,
                    "smtp_ssl": self.smtp_ssl
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": {
                    "smtp_host": self.smtp_host,
                    "smtp_port": self.smtp_port,
                    "smtp_username": self.smtp_username[:3] + "***" if self.smtp_username else None
                }
            }


# Global email service instance
email_service = EmailService()
