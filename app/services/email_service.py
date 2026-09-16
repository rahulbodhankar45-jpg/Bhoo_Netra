"""
Email Service: Dispatches verification OTPs and statutory notifications via SMTP.
Supports standard STARTTLS, SSL, and graceful fallback logging for local demo environments.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import os
from dotenv import load_dotenv

from app.core.config import settings

logger = logging.getLogger("app.email_service")


class EmailService:
    """Handles sending transactional emails such as Registration OTPs and statutory alerts."""

    def _reload_env(self):
        load_dotenv(override=False)

    @property
    def host(self):
        self._reload_env()
        return os.getenv("SMTP_HOST") or settings.SMTP_HOST

    @property
    def port(self):
        self._reload_env()
        val = os.getenv("SMTP_PORT")
        return int(val) if val else settings.SMTP_PORT

    @property
    def user(self):
        self._reload_env()
        return os.getenv("SMTP_USER") or settings.SMTP_USER

    @property
    def password(self):
        self._reload_env()
        return os.getenv("SMTP_PASSWORD") or settings.SMTP_PASSWORD

    @property
    def from_email(self):
        self._reload_env()
        return os.getenv("SMTP_FROM_EMAIL") or settings.SMTP_FROM_EMAIL

    @property
    def from_name(self):
        self._reload_env()
        return os.getenv("SMTP_FROM_NAME") or settings.SMTP_FROM_NAME

    @property
    def use_tls(self):
        self._reload_env()
        val = os.getenv("SMTP_TLS")
        if val is not None:
            return val.lower() in ("true", "1", "yes")
        return settings.SMTP_TLS

    @property
    def use_ssl(self):
        self._reload_env()
        val = os.getenv("SMTP_SSL")
        if val is not None:
            return val.lower() in ("true", "1", "yes")
        return settings.SMTP_SSL

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> tuple[bool, Optional[str], bool]:
        """
        Sends an email via SMTP.
        Returns: (success: bool, error_message: Optional[str], is_live_smtp: bool)
        """
        to_email = to_email.strip()
        if not to_email:
            logger.warning("Attempted to send email to empty address.")
            return False, "Recipient email address is required.", False

        if not text_content:
            text_content = html_content

        # Create MIME container
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = to_email

        # Attach text and HTML parts
        msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        if not self.host:
            logger.info(
                "[EMAIL SERVICE] (Simulated / Local Log Mode) OTP Email to '%s' | Subject: '%s'",
                to_email,
                subject
            )
            return True, None, False

        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=12)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=12)

            server.ehlo()
            if self.use_tls and not self.use_ssl:
                server.starttls()
                server.ehlo()

            if self.user and self.password:
                clean_pwd = self.password.replace(" ", "").strip()
                server.login(self.user.strip(), clean_pwd)

            server.sendmail(self.from_email, [to_email], msg.as_string())
            server.quit()
            logger.info("Successfully sent email to %s via SMTP (%s)", to_email, self.host)
            return True, None, True
        except Exception as exc:
            err_msg = str(exc)
            logger.error("Failed to send email to %s via SMTP (%s): %s", to_email, self.host, err_msg)
            return False, err_msg, True

    def send_registration_otp_email(self, to_email: str, otp_code: str) -> tuple[bool, Optional[str], bool]:
        """Generates and sends a high-integrity registration verification OTP email."""
        subject = f"Your Land Stack India Verification Code: {otp_code}"

        text_content = (
            f"Land Stack India - National Land Records Portal\n\n"
            f"Your 6-digit registration verification code is: {otp_code}\n\n"
            f"This OTP is valid for 10 minutes. Please enter this code on the registration page to complete your email verification.\n\n"
            f"Security Advisory: Do NOT share this OTP with anyone. Land Stack officials will never ask for your OTP.\n"
            f"If you did not request this verification, please disregard this email."
        )

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f5; margin: 0; padding: 20px; color: #1e293b; }}
    .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 12px rgba(0,0,0,0.06); }}
    .header {{ background: linear-gradient(135deg, #0b5d3b 0%, #15803d 100%); color: #ffffff; padding: 28px 24px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; letter-spacing: 0.5px; }}
    .header p {{ margin: 6px 0 0 0; font-size: 13px; opacity: 0.9; color: #dcfce7; }}
    .content {{ padding: 32px 28px; }}
    .otp-box {{ background: #f0fdf4; border: 2px dashed #22c55e; border-radius: 10px; text-align: center; padding: 20px; margin: 24px 0; }}
    .otp-code {{ font-size: 34px; font-weight: 800; color: #0b5d3b; letter-spacing: 8px; font-family: 'Courier New', monospace; }}
    .otp-expiry {{ font-size: 12px; color: #64748b; margin-top: 8px; }}
    .advisory {{ background: #fffbeb; border-left: 4px solid #f59e0b; padding: 12px 16px; margin: 20px 0; font-size: 12.5px; color: #92400e; border-radius: 0 6px 6px 0; }}
    .footer {{ background: #f8fafc; padding: 20px; text-align: center; font-size: 11.5px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🏛️ Land Stack India • BhooNetra</h1>
      <p>National Digital Public Infrastructure for Land Governance</p>
    </div>
    <div class="content">
      <h2 style="font-size: 18px; margin-top: 0; color: #0f172a;">Verify Your Registration Email</h2>
      <p style="font-size: 14px; line-height: 1.6; color: #475569;">
        Thank you for joining <strong>Land Stack India</strong>. To verify your email address (<code>{to_email}</code>) and activate your account, please enter the One-Time Password (OTP) below:
      </p>
      <div class="otp-box">
        <div class="otp-code">{otp_code}</div>
        <div class="otp-expiry">⏱️ Valid for 10 minutes</div>
      </div>
      <div class="advisory">
        🔒 <strong>Security Warning:</strong> Never share your verification OTP with anyone. Government officials or platform administrators will never ask for your verification code.
      </div>
      <p style="font-size: 12.5px; color: #64748b; line-height: 1.5;">
        If you did not initiate this registration request, please ignore this email or contact support.
      </p>
    </div>
    <div class="footer">
      © {settings.PROJECT_NAME} • National Informatics Centre & Land Governance Council
    </div>
  </div>
</body>
</html>"""

        return self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )


email_service = EmailService()
