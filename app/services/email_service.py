from typing import Optional
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
import structlog
from datetime import datetime, timedelta
import requests
import json

from app.config.settings import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class EmailService:
    """Service for sending emails via Mailtrap."""
    
    def __init__(self):
        self.settings = settings
        # Initialize FastMail for SMTP if credentials are available
        if settings.smtp_username and settings.smtp_password and settings.email_from:
            self.conf = ConnectionConfig(
                MAIL_USERNAME=settings.smtp_username,
                MAIL_PASSWORD=settings.smtp_password,
                MAIL_FROM=settings.email_from,
                MAIL_PORT=settings.smtp_port,
                MAIL_SERVER=settings.smtp_server,
                MAIL_FROM_NAME=settings.email_from_name,
                MAIL_STARTTLS=settings.smtp_use_tls,
                MAIL_SSL_TLS=False,
                USE_CREDENTIALS=True,
                VALIDATE_CERTS=True
            )
            self.fastmail = FastMail(self.conf)
        else:
            self.fastmail = None
    
    async def send_password_reset_email(self, email: EmailStr, reset_token: str, user_name: str = "") -> bool:
        """Send password reset email with token via Mailtrap."""
        try:
            logger.info("Sending password reset email", email=self.settings)
            # Try Mailtrap API first, fallback to SMTP
            if self.settings.mailtrap_api_token:
                logger.info("Sending password reset email via Mailtrap API", email=email)
                return await self._send_via_mailtrap_api(email, reset_token, user_name)
            # elif self.fastmail:
            #     return await self._send_via_smtp(email, reset_token, user_name)
            else:
                logger.error("No email service configured")
                return False
                
        except Exception as e:
            logger.error("Failed to send password reset email", email=email, error=str(e))
            return False
    
    async def _send_via_smtp(self, email: EmailStr, reset_token: str, user_name: str = "") -> bool:
        """Send email via SMTP (FastMail)."""
        try:
            # Create reset link
            reset_link = f"{self.settings.frontend_url}/reset-password?token={reset_token}"
            
            # Email template
            html_body = self._get_password_reset_template(user_name, reset_link, reset_token)
            
            message = MessageSchema(
                subject="Password Reset Request - Plagiarism Detection System",
                recipients=[email],
                body=html_body,
                subtype=MessageType.html
            )
            
            await self.fastmail.send_message(message)
            logger.info("Password reset email sent via SMTP", email=email)
            return True
            
        except Exception as e:
            logger.error("Failed to send email via SMTP", email=email, error=str(e))
            return False
    
    async def _send_via_mailtrap_api(self, email: EmailStr, reset_token: str, user_name: str = "") -> bool:
        """Send email via Mailtrap API."""
        try:
           
            # Create reset link
            reset_link = f"{self.settings.frontend_url}/reset-password?token={reset_token}"
            
            # Email template
            html_body = self._get_password_reset_template(user_name, reset_link, reset_token)
            
            # Mailtrap API payload
            payload = {
                "from": {
                    "email": self.settings.mailtrap_sender_email or self.settings.email_from,
                    "name": self.settings.email_from_name
                },
                "to": [
                    {
                        "email": email
                    }
                ],
                "subject": "Password Reset Request - Plagiarism Detection System",
                "html": html_body,
                "category": "Password Reset"
            }
            
            headers = {
                "Authorization": f"Bearer {self.settings.mailtrap_api_token}",
                "Content-Type": "application/json"
            }
            
            # Use the correct Mailtrap API endpoint
            response = requests.post(
                "https://send.api.mailtrap.io/api/send",
                headers=headers,
                json=payload
            )

          

            if response.status_code == 200:
                logger.info("Password reset email sent via Mailtrap API", email=email)
                return True
            else:
                logger.error("Mailtrap API error", status_code=response.status_code, response=response.text)
                return False
                
        except Exception as e:
            logger.error("Failed to send email via Mailtrap API", email=email, error=str(e))
            return False
    
    def _get_password_reset_template(self, user_name: str, reset_link: str, reset_token: str) -> str:
        """Generate HTML template for password reset email."""
        greeting = f"Hello {user_name}," if user_name else "Hello,"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Password Reset Request</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #4f46e5;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background-color: #f9fafb;
                    padding: 30px;
                    border-radius: 0 0 8px 8px;
                }}
                .button {{
                    display: inline-block;
                    background-color: #4f46e5;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 6px;
                    margin: 20px 0;
                    font-weight: bold;
                }}
                .button:hover {{
                    background-color: #4338ca;
                }}
                .token-box {{
                    background-color: #e5e7eb;
                    padding: 15px;
                    border-radius: 6px;
                    font-family: monospace;
                    font-size: 14px;
                    margin: 15px 0;
                    word-break: break-all;
                }}
                .warning {{
                    background-color: #fef3c7;
                    border-left: 4px solid #f59e0b;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    color: #6b7280;
                    font-size: 12px;
                    margin-top: 30px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Password Reset Request</h1>
            </div>
            <div class="content">
                <p>{greeting}</p>
                
                <p>We received a request to reset your password for your Plagiarism Detection System account.</p>
                
                <p>Click the button below to reset your password:</p>
                
                <div style="text-align: center;">
                    <a href="{reset_link}" class="button">Reset Password</a>
                </div>
                
                <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                <div class="token-box">{reset_link}</div>
                
                <p>Or use this reset token directly:</p>
                <div class="token-box">{reset_token}</div>
                
                <div class="warning">
                    <strong>⚠️ Security Notice:</strong>
                    <ul>
                        <li>This link will expire in {settings.reset_token_expire_hours} hours</li>
                        <li>If you didn't request this reset, please ignore this email</li>
                        <li>Never share this link or token with anyone</li>
                    </ul>
                </div>
                
                <p>If you have any questions, please contact our support team.</p>
                
                <p>Best regards,<br>
                The Plagiarism Detection System Team</p>
            </div>
            <div class="footer">
                <p>This is an automated message. Please do not reply to this email.</p>
                <p>© 2024 Plagiarism Detection System. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
    
    async def send_test_email(self, email: EmailStr) -> bool:
        """Send a test email to verify configuration."""
        try:
            message = MessageSchema(
                subject="Test Email - Plagiarism Detection System",
                recipients=[email],
                body="<h1>Test Email</h1><p>Your email configuration is working correctly!</p>",
                subtype=MessageType.html
            )
            
            await self.fastmail.send_message(message)
            logger.info("Test email sent successfully", email=email)
            return True
            
        except Exception as e:
            logger.error("Failed to send test email", email=email, error=str(e))
            return False
