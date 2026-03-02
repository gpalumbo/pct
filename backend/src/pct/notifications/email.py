"""Email — async SMTP sending.

Sends notification emails using aiosmtplib. Skips silently when no
SMTP configuration is provided, so callers don't need to check.
"""

from __future__ import annotations

import logging

from pct.models.core import SmtpConfig

logger = logging.getLogger(__name__)


async def send_email(
    smtp_config: SmtpConfig | None,
    to_address: str,
    subject: str,
    body: str,
) -> bool:
    """Send an email via SMTP.

    Skips silently (returns False) if smtp_config is None or if
    aiosmtplib is not installed.

    Args:
        smtp_config: SMTP connection parameters. None means skip.
        to_address: Recipient email address.
        subject: Email subject line.
        body: Plain text email body.

    Returns:
        True if email was sent successfully, False otherwise.
    """
    if smtp_config is None:
        logger.debug("No SMTP config — skipping email to %s", to_address)
        return False

    try:
        from email.message import EmailMessage

        import aiosmtplib

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp_config.username
        msg["To"] = to_address
        msg.set_content(body)

        await aiosmtplib.send(
            msg,
            hostname=smtp_config.server,
            port=smtp_config.port,
            username=smtp_config.username,
            password=smtp_config.password,
            use_tls=smtp_config.tls,
        )

        logger.info("Sent email to %s: %s", to_address, subject)
        return True

    except ImportError:
        logger.debug("aiosmtplib not installed — skipping email to %s", to_address)
        return False

    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_address, e)
        return False


async def send_notification_email(
    smtp_config: SmtpConfig | None,
    to_address: str,
    event_type: str,
    message: str,
    feature_id: str | None = None,
    task_id: str | None = None,
) -> bool:
    """Send a formatted notification email.

    Convenience wrapper that formats a notification event into an email.
    """
    subject = f"[PCT] {event_type}"
    if feature_id:
        subject += f" — {feature_id}"
    if task_id:
        subject += f"/{task_id}"

    body_lines = [
        f"Notification: {event_type}",
        "",
        message,
        "",
    ]
    if feature_id:
        body_lines.append(f"Feature: {feature_id}")
    if task_id:
        body_lines.append(f"Task: {task_id}")

    body = "\n".join(body_lines)

    return await send_email(smtp_config, to_address, subject, body)
