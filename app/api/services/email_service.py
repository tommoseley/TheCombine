"""
Email service for sending magic link authentication emails.

Supports two backends:
- SMTP: Production email delivery via smtplib
- Console: Development backend that prints emails to console
"""

import smtplib
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from jinja2 import Template
from datetime import datetime, timedelta, timezone
from typing import Dict

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple in-memory rate limiter for magic link requests."""
    
    def __init__(self, max_requests: int = 5, window_minutes: int = 10):
        self.max_requests = max_requests
        self.window_minutes = window_minutes
        self.requests: Dict[str, list] = {}
    
    def can_send(self, email: str) -> bool:
        """Check if email can be sent (within rate limit)."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=self.window_minutes)
        
        if email not in self.requests:
            self.requests[email] = []
        
        self.requests[email] = [
            ts for ts in self.requests[email]
            if ts > cutoff
        ]
        
        return len(self.requests[email]) < self.max_requests
    
    def record_request(self, email: str):
        """Record a magic link request."""
        now = datetime.now(timezone.utc)
        if email not in self.requests:
            self.requests[email] = []
        self.requests[email].append(now)
    
    def get_retry_after(self, email: str) -> int:
        """Get seconds until rate limit resets."""
        if email not in self.requests or not self.requests[email]:
            return 0
        
        oldest_request = min(self.requests[email])
        retry_time = oldest_request + timedelta(minutes=self.window_minutes)
        seconds_until_reset = (retry_time - datetime.now(timezone.utc)).total_seconds()
        
        return max(0, int(seconds_until_reset))


class EmailService:
    """
    Email service for sending magic link emails.
    
    Supports two backends via EMAIL_BACKEND environment variable:
    - 'smtp': Send emails via SMTP (production)
    - 'console': Print emails to console (development)
    """
    
    def __init__(self):
        self.backend = os.getenv("EMAIL_BACKEND", "console")
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        self.from_email = os.getenv("SMTP_FROM_EMAIL", self.smtp_user or "noreply@workbench.ai")
        
        self.rate_limiter = RateLimiter(max_requests=5, window_minutes=10)
        
        logger.info(f"EmailService initialized with backend: {self.backend}")
    
    def can_send_magic_link(self, email: str) -> tuple[bool, int]:
        """
        Check if magic link can be sent to email (rate limit check).
        
        Returns:
            Tuple of (can_send: bool, retry_after_seconds: int)
        """
        can_send = self.rate_limiter.can_send(email)
        retry_after = 0 if can_send else self.rate_limiter.get_retry_after(email)
        return can_send, retry_after
    
    def send_magic_link(self, email: str, magic_link: str) -> bool:
        """
        Send magic link email to user.
        
        Args:
            email: Recipient email address
            magic_link: Full magic link URL
            
        Returns:
            True if email sent successfully, False otherwise
        """
        # Record request for rate limiting
        self.rate_limiter.record_request(email)
        
        # Load email template
        template_path = Path(__file__).resolve().parents[2] / "templates" / "auth" / "magic_link_email.txt"
        
        try:
            email_template = Template(template_path.read_text())
            email_body = email_template.render(magic_link=magic_link)
        except Exception as e:
            logger.error(f"Failed to load email template: {e}")
            # Fallback to simple text
            email_body = f"Click this link to log in to Workbench AI:\n\n{magic_link}\n\nThis link expires in 7 days."
        
        if self.backend == "smtp":
            return self._send_via_smtp(email, email_body)
        else:
            return self._send_via_console(email, email_body)
    
    def _send_via_smtp(self, email: str, body: str) -> bool:
        """Send email via SMTP."""
        try:
            # Validate SMTP configuration
            if not all([self.smtp_host, self.smtp_user, self.smtp_password]):
                logger.error("SMTP configuration incomplete (missing SMTP_HOST, SMTP_USER, or SMTP_PASSWORD)")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = email
            msg['Subject'] = "Your Workbench AI Login Link"
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Magic link sent to {email} via SMTP")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            return False
    
    def _send_via_console(self, email: str, body: str) -> bool:
        """Print email to console (development mode)."""
        print("\n" + "=" * 80)
        print("📧 EMAIL (Console Backend)")
        print("=" * 80)
        print(f"To: {email}")
        print(f"From: {self.from_email}")
        print(f"Subject: Your Workbench AI Login Link")
        print("-" * 80)
        print(body)
        print("=" * 80 + "\n")
        
        logger.info(f"Magic link printed to console for {email}")
        return True


# Singleton instance
email_service = EmailService()