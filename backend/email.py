import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from backend.config import settings

logger = logging.getLogger(__name__)


async def send_verification_email(to_email: str, token: str) -> None:
    verification_url = f"{settings.app_url}/auth/verify-email?token={token}"

    if not settings.smtp_host:
        # Dev mode — log the link so you can click it without an email server
        logger.info("EMAIL VERIFICATION LINK (no SMTP configured) → %s", verification_url)
        return

    message = MIMEMultipart("alternative")
    message["Subject"] = "Verify your email — ResumeReviewerDV"
    message["From"] = settings.smtp_from
    message["To"] = to_email

    plain = (
        f"Welcome to ResumeReviewerDV!\n\n"
        f"Click the link below to verify your email address:\n\n"
        f"{verification_url}\n\n"
        f"This link expires in 24 hours.\n\n"
        f"If you did not create an account, you can ignore this email."
    )
    html = f"""
    <html><body>
    <h2>Welcome to ResumeReviewerDV</h2>
    <p>Click the button below to verify your email address.</p>
    <p><a href="{verification_url}" style="background:#2563eb;color:#fff;padding:12px 24px;
       border-radius:6px;text-decoration:none;display:inline-block;">Verify Email</a></p>
    <p>Or copy this link: <a href="{verification_url}">{verification_url}</a></p>
    <p><small>This link expires in 24 hours. If you did not create an account, ignore this email.</small></p>
    </body></html>
    """
    message.attach(MIMEText(plain, "plain"))
    message.attach(MIMEText(html, "html"))

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=True,
        )
        logger.info("Verification email sent to %s", to_email)
    except Exception as exc:
        logger.error("Failed to send verification email to %s: %s", to_email, exc)
        raise
