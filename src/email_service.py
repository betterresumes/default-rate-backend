import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
        self.from_name = os.getenv("FROM_NAME", "Default Rate Prediction")
        
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """Send an email."""
        try:
            if not self.smtp_username or not self.smtp_password:
                logger.error("SMTP credentials not configured!")
                # In development mode, show OTP in console
                if os.getenv("DEBUG", "false").lower() == "true":
                    logger.warning("DEBUG MODE: Using console fallback for development.")
                    print(f"\n🔐 EMAIL DEBUG - OTP for {to_email}:")
                    print(f"📧 Subject: {subject}")
                    if "verification" in subject.lower() or "password" in subject.lower():
                        # Extract OTP from HTML content
                        import re
                        otp_match = re.search(r'<div class="otp">(\d{6})</div>', html_content)
                        if otp_match:
                            otp = otp_match.group(1)
                            print(f"🔑 OTP: {otp}")
                            print(f"⏰ Valid for 10 minutes")
                            print("="*50)
                    return True
                else:
                    # In production, this is a real error
                    logger.error("Production environment requires SMTP credentials")
                    return False
                
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add text part if provided
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)
            
            # Add HTML part
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send the email with timeout
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed for {to_email}: {str(e)}")
            # In development, show OTP in console as fallback
            if os.getenv("DEBUG", "false").lower() == "true":
                self._console_fallback(to_email, subject, html_content)
                return True
            return False
            
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error when sending email to {to_email}: {str(e)}")
            # In development, show OTP in console as fallback
            if os.getenv("DEBUG", "false").lower() == "true":
                self._console_fallback(to_email, subject, html_content)
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            # In development, show OTP in console as fallback
            if os.getenv("DEBUG", "false").lower() == "true":
                self._console_fallback(to_email, subject, html_content)
                return True
            return False
    
    def _console_fallback(self, to_email: str, subject: str, html_content: str):
        """Console fallback for development."""
        print(f"\n🔐 EMAIL FALLBACK - OTP for {to_email}:")
        print(f"📧 Subject: {subject}")
        if "verification" in subject.lower() or "password" in subject.lower():
            # Extract OTP from HTML content
            import re
            otp_match = re.search(r'<div class="otp">(\d{6})</div>', html_content)
            if otp_match:
                otp = otp_match.group(1)
                print(f"🔑 OTP: {otp}")
                print(f"⏰ Valid for 10 minutes")
            elif "verification" in subject.lower() or "password" in subject.lower():
                # Try to extract from text content as well
                text_otp_match = re.search(r'OTP code: (\d{6})', html_content)
                if text_otp_match:
                    otp = text_otp_match.group(1)
                    print(f"🔑 OTP: {otp}")
                    print(f"⏰ Valid for 10 minutes")
            print("="*50)
    
    def send_verification_email(self, to_email: str, username: str, otp: str) -> bool:
        """Send email verification OTP."""
        subject = "Verify Your Email - Default Rate Prediction"
        
        html_template = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Email Verification</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #007bff; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9f9f9; }
                .otp { font-size: 24px; font-weight: bold; color: #007bff; text-align: center; 
                       background: white; padding: 15px; margin: 20px 0; border-radius: 5px; }
                .footer { padding: 20px; text-align: center; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Email Verification</h1>
                </div>
                <div class="content">
                    <p>Hello {{ username }},</p>
                    <p>Thank you for registering with Default Rate Prediction. To complete your registration, please verify your email address using the OTP code below:</p>
                    <div class="otp">{{ otp }}</div>
                    <p>This code will expire in 10 minutes.</p>
                    <p>If you didn't request this verification, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 Default Rate Prediction. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """)
        
        html_content = html_template.render(username=username, otp=otp)
        
        text_content = f"""
        Hello {username},
        
        Thank you for registering with Default Rate Prediction. 
        To complete your registration, please verify your email address using this OTP code: {otp}
        
        This code will expire in 10 minutes.
        
        If you didn't request this verification, please ignore this email.
        """
        
        return self.send_email(to_email, subject, html_content, text_content)
    
    def send_password_reset_email(self, to_email: str, username: str, otp: str) -> bool:
        """Send password reset OTP."""
        subject = "Reset Your Password - Default Rate Prediction"
        
        html_template = Template("""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Password Reset</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #dc3545; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9f9f9; }
                .otp { font-size: 24px; font-weight: bold; color: #dc3545; text-align: center; 
                       background: white; padding: 15px; margin: 20px 0; border-radius: 5px; }
                .footer { padding: 20px; text-align: center; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Password Reset</h1>
                </div>
                <div class="content">
                    <p>Hello {{ username }},</p>
                    <p>You have requested to reset your password. Use the OTP code below to reset your password:</p>
                    <div class="otp">{{ otp }}</div>
                    <p>This code will expire in 10 minutes.</p>
                    <p>If you didn't request this password reset, please ignore this email and your password will remain unchanged.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 Default Rate Prediction. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """)
        
        html_content = html_template.render(username=username, otp=otp)
        
        text_content = f"""
        Hello {username},
        
        You have requested to reset your password. 
        Use this OTP code to reset your password: {otp}
        
        This code will expire in 10 minutes.
        
        If you didn't request this password reset, please ignore this email.
        """
        
        return self.send_email(to_email, subject, html_content, text_content)

# Initialize email service
email_service = EmailService()
