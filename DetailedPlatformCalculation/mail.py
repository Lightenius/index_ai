"""Send formatted email with optional file attachments."""

from __future__ import annotations

import mimetypes
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

import dotenv


SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
DEFAULT_SUBJECT = "Kamera Sistemi Ekipman Özeti"
ENV_PATH = Path(__file__).with_name(".env")


def _setting(name: str) -> str | None:
    return os.environ.get(name) or dotenv.get_key(str(ENV_PATH), name)


def send_mail(
    message: str,
    receiver_email: str,
    *,
    subject: str = DEFAULT_SUBJECT,
    html_body: str | None = None,
    attachments: Iterable[Path] = (),
) -> None:
    """Send an email to the requested receiver, attaching any existing files."""
    sender_email = _setting("SENDER_EMAIL")
    app_password = _setting("MAIL_PASS")
    if not sender_email or not app_password:
        raise RuntimeError(
            f"SENDER_EMAIL and MAIL_PASS must be configured in {ENV_PATH.name} "
            "or the environment."
        )
    if not receiver_email.strip():
        raise ValueError("A receiver email address is required.")

    email = EmailMessage()
    email["Subject"] = subject
    email["From"] = sender_email
    email["To"] = receiver_email.strip()
    email.set_content(message)
    if html_body:
        email.add_alternative(html_body, subtype="html")

    for path in attachments:
        attachment_path = Path(path)
        if not attachment_path.is_file():
            raise FileNotFoundError(f"Email attachment not found: {attachment_path}")
        content_type, _ = mimetypes.guess_type(attachment_path.name)
        if attachment_path.suffix.casefold() == ".xlsx":
            content_type = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        if content_type is None:
            content_type = "application/octet-stream"
        maintype, subtype = content_type.split("/", maxsplit=1)
        email.add_attachment(
            attachment_path.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            filename=attachment_path.name,
        )

    try:
        with smtplib.SMTP_SSL(
            SMTP_SERVER,
            SMTP_PORT,
            context=ssl.create_default_context(),
        ) as server:
            server.login(sender_email, app_password)
            server.send_message(email)
    except (smtplib.SMTPException, OSError) as error:
        raise RuntimeError("Email delivery failed. Check SMTP configuration.") from error


def Mail(
    message: str,
    receiver_email: str | None = None,
    *,
    subject: str = DEFAULT_SUBJECT,
    html_body: str | None = None,
    attachments: Iterable[Path] = (),
) -> None:
    """Compatibility wrapper using the configured default recipient if omitted."""
    recipient = receiver_email or _setting("DEFAULT_RECEIVER_EMAIL")
    if not recipient:
        raise RuntimeError(
            "receiver_email is required when DEFAULT_RECEIVER_EMAIL is not configured."
        )
    send_mail(
        message,
        recipient,
        subject=subject,
        html_body=html_body,
        attachments=attachments,
    )
