"""
Email Service
Handles SMTP-based mail delivery for OTP and loan reports.
"""

import asyncio
import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Iterable, Optional

from config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def missing_config_fields(self) -> list[str]:
        required = {
            "SMTP_HOST": settings.SMTP_HOST,
            "SMTP_PORT": settings.SMTP_PORT,
            "SMTP_USERNAME": settings.SMTP_USERNAME,
            "SMTP_PASSWORD": settings.SMTP_PASSWORD,
            "SMTP_FROM_EMAIL": settings.SMTP_FROM_EMAIL,
        }
        return [key for key, value in required.items() if not value]

    @property
    def is_configured(self) -> bool:
        return len(self.missing_config_fields()) == 0

    def _send_sync(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[Iterable[str]] = None,
    ) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = to_email
        message.set_content(body_text)

        if body_html:
            message.add_alternative(body_html, subtype="html")

        for file_path in attachments or []:
            if not file_path or not os.path.exists(file_path):
                continue
            with open(file_path, "rb") as file_handle:
                data = file_handle.read()
                filename = os.path.basename(file_path)
                message.add_attachment(
                    data,
                    maintype="application",
                    subtype="octet-stream",
                    filename=filename,
                )

        if settings.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(message)
            return

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
            server.ehlo()
            if settings.SMTP_USE_TLS:
                server.starttls()
                server.ehlo()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[Iterable[str]] = None,
    ) -> bool:
        if not self.is_configured:
            logger.warning(
                "SMTP not configured. Missing: %s. Skipping email for %s",
                ", ".join(self.missing_config_fields()),
                to_email,
            )
            return False

        try:
            await asyncio.to_thread(
                self._send_sync,
                to_email,
                subject,
                body_text,
                body_html,
                attachments,
            )
            logger.info("Email sent to %s with subject '%s'", to_email, subject)
            return True
        except Exception as error:
            logger.error("Failed to send email to %s: %s", to_email, error, exc_info=True)
            return False

    async def send_otp_email(self, to_email: str, otp: str, expiry_minutes: int) -> bool:
        subject = "Your NBFC Loan Platform OTP"
        body = (
            "Dear Customer,\n\n"
            f"Your OTP is: {otp}\n"
            f"This OTP is valid for {expiry_minutes} minutes.\n\n"
            "Do not share this OTP with anyone.\n\n"
            "Regards,\n"
            "NBFC Loan Platform"
        )
        return await self.send_email(to_email=to_email, subject=subject, body_text=body)


email_service = EmailService()
