"""Plain SMTP delivery. Off until SMTP_HOST is set; the digest text can always be copied instead."""

import smtplib
from email.message import EmailMessage

from app.core.config import get_settings


class MailError(Exception):
    """Sending failed; the message is safe to show the owner."""


def configured() -> bool:
    return get_settings().smtp_host is not None


def send_email(to: list[str], subject: str, text: str, html: str) -> None:
    s = get_settings()
    if s.smtp_host is None:
        raise MailError("Email sending is not configured on this server.")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = s.smtp_from
    msg["To"] = ", ".join(to)
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
            if s.smtp_starttls:
                smtp.starttls()
            if s.smtp_user and s.smtp_password:
                smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(msg)
    except (OSError, smtplib.SMTPException) as exc:
        raise MailError("The email could not be sent. Check the mail server settings.") from exc
