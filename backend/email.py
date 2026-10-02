"""
Email service — three delivery paths in priority order:
  1. SendGrid API  (SENDGRID_API_KEY is set)
  2. SMTP          (SMTP_HOST is set)
  3. Dev stdout    (neither configured — logs content instead of sending)
"""

import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from backend.config import settings

logger = logging.getLogger(__name__)


# ── Score helpers ────────────────────────────────────────────────────────────


def _score_label(score: float, capped: bool) -> str:
    if capped or score < 50:
        return "Needs Improvement"
    if score < 80:
        return "Good Match"
    return "Strong Match"


def _score_color(score: float, capped: bool) -> str:
    if capped or score < 50:
        return "#ef4444"
    if score < 80:
        return "#f59e0b"
    return "#22c55e"


def _score_bg(score: float, capped: bool) -> str:
    if capped or score < 50:
        return "rgba(239,68,68,0.12)"
    if score < 80:
        return "rgba(245,158,11,0.12)"
    return "rgba(34,197,94,0.12)"


# ── Transport ────────────────────────────────────────────────────────────────


async def _send_via_sendgrid(to: str, subject: str, html: str, plain: str) -> None:
    import sendgrid
    from sendgrid.helpers.mail import Mail

    sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)
    message = Mail(
        from_email=settings.smtp_from,
        to_emails=to,
        subject=subject,
        html_content=html,
    )
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, sg.send, message)
    logger.info("SendGrid %s for %s", response.status_code, to)


async def _send_via_smtp(to: str, subject: str, html: str, plain: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        start_tls=True,
    )


async def _deliver(to: str, subject: str, html: str, plain: str) -> None:
    if settings.sendgrid_api_key:
        await _send_via_sendgrid(to, subject, html, plain)
    elif settings.smtp_host:
        await _send_via_smtp(to, subject, html, plain)
    else:
        logger.info(
            "EMAIL (no transport configured)\nTo: %s\nSubject: %s\n\n%s",
            to,
            subject,
            plain,
        )


# ── Public API ───────────────────────────────────────────────────────────────


async def send_verification_email(to_email: str, token: str) -> None:
    url = f"{settings.app_url}/auth/verify-email?token={token}"
    subject = "Verify your email — ResumeReviewerDV"
    plain = (
        "Welcome to ResumeReviewerDV!\n\n"
        f"Verify your email address:\n\n{url}\n\n"
        "This link expires in 24 hours.\n"
        "If you did not create an account, ignore this email."
    )
    html = f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;
max-width:560px;margin:0 auto;padding:24px;color:#1e293b">
<h2 style="margin-top:0">Welcome to ResumeReviewerDV</h2>
<p>Click the button below to verify your email address.</p>
<p><a href="{url}" style="background:#2563eb;color:#fff;padding:12px 24px;
border-radius:6px;text-decoration:none;display:inline-block;font-weight:600">
Verify Email</a></p>
<p style="color:#64748b;font-size:13px">Or copy this link:<br>
<a href="{url}">{url}</a></p>
<p style="color:#94a3b8;font-size:12px">This link expires in 24 hours.
If you did not create an account, ignore this email.</p>
</body></html>"""

    await _deliver(to_email, subject, html, plain)
    logger.info("Verification email dispatched to %s", to_email)


async def send_results_email(
    to_email: str,
    submission_id: str,
    score: float,
    capped_by_must_have: bool,
    profile_title: str,
) -> None:
    # submission_id is the submission's public (filename-based) ID
    results_url = f"{settings.frontend_url}/submissions/{submission_id}"
    color = _score_color(score, capped_by_must_have)
    bg = _score_bg(score, capped_by_must_have)
    label = _score_label(score, capped_by_must_have)
    capped_notice = (
        f'<div style="color:#ef4444;font-size:12px;margin-top:8px">'
        f"Score capped: a must-have requirement was not met.</div>"
        if capped_by_must_have
        else ""
    )

    subject = f"Your resume scored {score:.0f}/100 for {profile_title}"
    plain = (
        "Resume scoring complete.\n\n"
        f"Profile: {profile_title}\n"
        f"Score: {score:.0f}/100 — {label}\n"
        + ("Note: Score capped — a must-have requirement was not met.\n" if capped_by_must_have else "")
        + f"\nView your full results:\n{results_url}"
    )
    html = f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;
max-width:560px;margin:0 auto;padding:24px;color:#1e293b">
<h2 style="margin-top:0">Resume Scoring Complete</h2>
<p style="color:#475569">Profile evaluated: <strong>{profile_title}</strong></p>
<table width="100%" cellpadding="0" cellspacing="0"
style="background:#f8fafc;border-radius:12px;margin:24px 0">
<tr><td style="padding:32px;text-align:center">
<div style="font-size:56px;font-weight:700;line-height:1;color:{color}">{score:.0f}</div>
<div style="color:#94a3b8;font-size:14px;margin-top:4px">out of 100</div>
<div style="display:inline-block;background:{bg};color:{color};font-weight:600;
font-size:14px;padding:4px 16px;border-radius:999px;margin-top:12px">{label}</div>
{capped_notice}
</td></tr></table>
<p><a href="{results_url}" style="background:#2563eb;color:#fff;padding:12px 24px;
border-radius:6px;text-decoration:none;display:inline-block;font-weight:600">
View Full Results</a></p>
<p style="color:#94a3b8;font-size:12px;margin-top:32px">
ResumeReviewerDV — AI-powered resume screening</p>
</body></html>"""

    await _deliver(to_email, subject, html, plain)
    logger.info(
        "Results email dispatched to %s (submission %s, score %.1f)",
        to_email,
        submission_id,
        score,
    )
