import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional
import os

logger = logging.getLogger(__name__)

# Try to import fastapi_mail, but make it optional
try:
    from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
    FASTAPI_MAIL_AVAILABLE = True
except ImportError:
    FASTAPI_MAIL_AVAILABLE = False
    logger.warning("fastapi-mail not installed. Email functionality will be disabled. Install with: pip install fastapi-mail")

class EmailService:
    """Service for sending emails (verification, password reset)"""
    
    def __init__(self):
        # Email configuration from environment variables
        self.mail_username = os.getenv("MAIL_USERNAME", "")
        self.mail_password = os.getenv("MAIL_PASSWORD", "")
        self.mail_from = os.getenv("MAIL_FROM", "noreply@hrsp-ai-hub.com")
        self.mail_from_name = os.getenv("MAIL_FROM_NAME", "HRSP AI Hub")
        self.mail_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
        self.mail_port = int(os.getenv("MAIL_PORT", "587"))
        self.mail_starttls = os.getenv("MAIL_STARTTLS", "true").lower() == "true"
        self.mail_ssl_tls = os.getenv("MAIL_SSL_TLS", "false").lower() == "true"
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        
        # Initialize FastMail if email credentials are provided and fastapi-mail is available
        if FASTAPI_MAIL_AVAILABLE and self.mail_username and self.mail_password:
            try:
                self.conf = ConnectionConfig(
                    MAIL_USERNAME=self.mail_username,
                    MAIL_PASSWORD=self.mail_password,
                    MAIL_FROM=self.mail_from,
                    MAIL_FROM_NAME=self.mail_from_name,
                    MAIL_PORT=self.mail_port,
                    MAIL_SERVER=self.mail_server,
                    MAIL_STARTTLS=self.mail_starttls,
                    MAIL_SSL_TLS=self.mail_ssl_tls,
                    USE_CREDENTIALS=True,
                    VALIDATE_CERTS=True
                )
                self.fastmail = FastMail(self.conf)
                self.enabled = True
                logger.info("Email service initialized with SMTP configuration")
            except Exception as e:
                logger.warning(f"Failed to initialize email service: {e}. Email functionality will be disabled.")
                self.enabled = False
                self.fastmail = None
        else:
            self.enabled = False
            self.fastmail = None
            if not FASTAPI_MAIL_AVAILABLE:
                logger.warning("Email service disabled - fastapi-mail not installed")
            elif not self.mail_username or not self.mail_password:
                logger.warning("Email service disabled - MAIL_USERNAME and MAIL_PASSWORD not configured")
    
    def generate_verification_token(self) -> str:
        """Generate a secure verification token"""
        return secrets.token_urlsafe(32)
    
    def generate_reset_token(self) -> str:
        """Generate a secure password reset token"""
        return secrets.token_urlsafe(32)
    
    async def send_verification_email(self, email: str, token: str, full_name: str) -> bool:
        """
        Send email verification link to user
        
        Args:
            email: User's email address
            token: Verification token
            full_name: User's full name
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.enabled or not self.fastmail:
            verification_url = f"{self.frontend_url}/verify-email?token={token}"
            logger.info(f"Email service disabled - verification email not sent to {email}")
            logger.info(f"Verification token for {email}: {token}")
            logger.info(f"Verification URL: {verification_url}")
            logger.info("To enable email sending, configure MAIL_USERNAME and MAIL_PASSWORD in .env")
            return False
        
        try:
            verification_url = f"{self.frontend_url}/verify-email?token={token}"
            
            message = MessageSchema(
                subject="Verify Your Email Address - HRSP AI Hub",
                recipients=[email],
                body=f"""
Hello {full_name},

Thank you for registering with HRSP AI Hub!

Please verify your email address by clicking the link below:

{verification_url}

This link will expire in 24 hours.

If you did not create an account, please ignore this email.

Best regards,
HRSP AI Hub Team
                """.strip(),
                subtype=MessageType.plain
            )
            
            await self.fastmail.send_message(message)
            logger.info(f"Verification email sent to {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send verification email to {email}: {e}", exc_info=True)
            # Log the URL so user can still verify manually
            verification_url = f"{self.frontend_url}/verify-email?token={token}"
            logger.info(f"Manual verification URL: {verification_url}")
            return False
    
    async def send_password_reset_email(self, email: str, token: str, full_name: str) -> bool:
        """
        Send password reset link to user
        
        Args:
            email: User's email address
            token: Reset token
            full_name: User's full name
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.enabled or not self.fastmail:
            reset_url = f"{self.frontend_url}/reset-password?token={token}"
            logger.info(f"Email service disabled - password reset email not sent to {email}")
            logger.info(f"Reset token for {email}: {token}")
            logger.info(f"Reset URL: {reset_url}")
            logger.info("To enable email sending, configure MAIL_USERNAME and MAIL_PASSWORD in .env")
            return False
        
        try:
            reset_url = f"{self.frontend_url}/reset-password?token={token}"
            
            message = MessageSchema(
                subject="Password Reset Request - HRSP AI Hub",
                recipients=[email],
                body=f"""
Hello {full_name},

You requested to reset your password for your HRSP AI Hub account.

Click the link below to reset your password:

{reset_url}

This link will expire in 1 hour.

If you did not request a password reset, please ignore this email and your password will remain unchanged.

Best regards,
HRSP AI Hub Team
                """.strip(),
                subtype=MessageType.plain
            )
            
            await self.fastmail.send_message(message)
            logger.info(f"Password reset email sent to {email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {e}", exc_info=True)
            # Log the URL so user can still reset manually
            reset_url = f"{self.frontend_url}/reset-password?token={token}"
            logger.info(f"Manual reset URL: {reset_url}")
            return False

# Global instance
email_service = EmailService()

