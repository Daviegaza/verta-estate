"""
Email service for Vestra — transactional emails, password resets, notifications.
Uses SMTP (SendGrid / Mailgun / AWS SES compatible).
"""
from __future__ import annotations

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("vestra")


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> bool:
    """Send a transactional email. Returns True on success."""
    if not settings.SMTP_HOST:
        logger.warning('{"event":"email_skipped","to":"%s","reason":"SMTP not configured"}', to_email)
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        if text_body:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Use a thread executor to avoid blocking the async event loop
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            _send_smtp,
            msg,
            to_email,
        )
        logger.info('{"event":"email_sent","to":"%s","subject":"%s"}', to_email, subject)
        return True
    except Exception as e:
        logger.error('{"event":"email_failed","to":"%s","error":"%s"}', to_email, str(e))
        return False


def _send_smtp(msg: MIMEMultipart, to_email: str) -> None:
    """Blocking SMTP send — runs in thread executor."""
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
        server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())


# ── Email Templates ────────────────────────────────────────────────────────────

def _base_template(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#f9fafb;">
  <div style="background:#fff;border-radius:16px;padding:32px;border:1px solid #e5e7eb;">
    <div style="margin-bottom:24px;">
      <span style="font-size:24px;font-weight:800;color:#059669;">V</span><span style="font-size:20px;font-weight:700;color:#111827;">estra</span>
    </div>
    <h1 style="font-size:20px;color:#111827;margin-bottom:16px;">{title}</h1>
    {body}
    <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
    <p style="font-size:12px;color:#9ca3af;">This email was sent by Vestra. If you didn't request this, please ignore it.</p>
  </div>
</body></html>"""


async def send_verification_email(to_email: str, full_name: str, token: str) -> bool:
    """Send email verification link."""
    verify_url = f"{settings.BASE_URL}/auth/verify-email?token={token}"
    body = f"""
    <p style="color:#374151;line-height:1.6;">Hi {full_name},</p>
    <p style="color:#374151;line-height:1.6;">Welcome to Vestra! Please verify your email address to get started.</p>
    <a href="{verify_url}" style="display:inline-block;background:#059669;color:#fff;padding:12px 24px;border-radius:12px;text-decoration:none;font-weight:600;margin:16px 0;">Verify Email</a>
    <p style="color:#6b7280;font-size:13px;">This link expires in 24 hours. If the button doesn't work, copy this link:<br>{verify_url}</p>
    """
    return await send_email(to_email, "Verify your Vestra account", _base_template("Verify your email", body))


async def send_password_reset_email(to_email: str, full_name: str, token: str) -> bool:
    """Send password reset link."""
    reset_url = f"{settings.BASE_URL}/auth/reset-password?token={token}"
    body = f"""
    <p style="color:#374151;line-height:1.6;">Hi {full_name},</p>
    <p style="color:#374151;line-height:1.6;">We received a request to reset your password. Click the button below to set a new one.</p>
    <a href="{reset_url}" style="display:inline-block;background:#059669;color:#fff;padding:12px 24px;border-radius:12px;text-decoration:none;font-weight:600;margin:16px 0;">Reset Password</a>
    <p style="color:#6b7280;font-size:13px;">This link expires in 30 minutes. If you didn't request this, you can safely ignore this email.</p>
    """
    return await send_email(to_email, "Reset your Vestra password", _base_template("Reset your password", body))


async def send_welcome_email(to_email: str, full_name: str) -> bool:
    """Send welcome email after successful registration + verification."""
    body = f"""
    <p style="color:#374151;line-height:1.6;">Hi {full_name},</p>
    <p style="color:#374151;line-height:1.6;">Your email is verified — welcome to Vestra, Africa's most trusted property platform!</p>
    <p style="color:#374151;line-height:1.6;">Here's what you can do:</p>
    <ul style="color:#374151;line-height:1.8;">
      <li>Browse &mdash; Search thousands of verified properties across Kenya</li>
      <li>Verify &mdash; Get AI-powered Trust Reports on any property for KES 500</li>
      <li>List &mdash; Sell or rent your property with a Trust Score badge</li>
    </ul>
    """
    return await send_email(to_email, "Welcome to Vestra!", _base_template("Welcome!", body))
