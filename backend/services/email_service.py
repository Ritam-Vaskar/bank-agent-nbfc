"""
Email Service
Supports Resend API (preferred) and SMTP fallback for OTP and loan reports.
"""

import asyncio
import base64
import logging
import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from typing import Iterable, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def _normalized_resend_from_email(self) -> str:
        raw_value = (settings.RESEND_FROM_EMAIL or "").strip()
        if not raw_value:
            return raw_value

        name, address = parseaddr(raw_value)
        if address and "@" in address:
            return formataddr((name, address)) if name else address

        import re

        malformed = re.match(r"^\s*<([^>]+)>\s*([^<>\s]+@[^<>\s]+)\s*$", raw_value)
        if malformed:
            return formataddr((malformed.group(1).strip(), malformed.group(2).strip()))

        return raw_value

    def resend_missing_config_fields(self) -> list[str]:
        required = {
            "RESEND_API_KEY": settings.RESEND_API_KEY,
            "RESEND_FROM_EMAIL": settings.RESEND_FROM_EMAIL,
        }
        return [key for key, value in required.items() if not value]

    def smtp_missing_config_fields(self) -> list[str]:
        required = {
            "SMTP_HOST": settings.SMTP_HOST,
            "SMTP_PORT": settings.SMTP_PORT,
            "SMTP_USERNAME": settings.SMTP_USERNAME,
            "SMTP_PASSWORD": settings.SMTP_PASSWORD,
            "SMTP_FROM_EMAIL": settings.SMTP_FROM_EMAIL,
        }
        return [key for key, value in required.items() if not value]

    def missing_config_fields(self) -> list[str]:
        if self.has_resend_config:
            return []
        if self.has_smtp_config:
            return []
        return [
            *self.resend_missing_config_fields(),
            *self.smtp_missing_config_fields(),
        ]

    @property
    def has_resend_config(self) -> bool:
        return len(self.resend_missing_config_fields()) == 0

    @property
    def has_smtp_config(self) -> bool:
        return len(self.smtp_missing_config_fields()) == 0

    @property
    def is_configured(self) -> bool:
        return self.has_resend_config or self.has_smtp_config

    @property
    def active_provider(self) -> str:
        if self.has_resend_config:
            return "resend"
        if self.has_smtp_config:
            return "smtp"
        return "none"

    async def _send_via_resend(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[Iterable[str]] = None,
    ) -> bool:
        payload: dict = {
            "from": self._normalized_resend_from_email(),
            "to": [to_email],
            "subject": subject,
            "text": body_text,
        }

        if body_html:
            payload["html"] = body_html

        resend_attachments = []
        for file_path in attachments or []:
            if not file_path or not os.path.exists(file_path):
                continue
            with open(file_path, "rb") as file_handle:
                data = file_handle.read()
            resend_attachments.append(
                {
                    "filename": os.path.basename(file_path),
                    "content": base64.b64encode(data).decode("utf-8"),
                }
            )

        if resend_attachments:
            payload["attachments"] = resend_attachments

        headers = {
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
        }
        url = f"{settings.RESEND_API_BASE_URL.rstrip('/')}/emails"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
            logger.info("Email sent via Resend to %s with subject '%s'", to_email, subject)
            return True
        except httpx.HTTPStatusError as error:
            response_text = ""
            try:
                response_text = error.response.text
            except Exception:
                response_text = ""
            logger.error(
                "Resend send failed for %s: status=%s response=%s",
                to_email,
                getattr(error.response, "status_code", "unknown"),
                response_text,
                exc_info=True,
            )
            return False
        except Exception as error:
            logger.error("Resend send failed for %s: %s", to_email, error, exc_info=True)
            return False

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
        provider = self.active_provider

        if provider == "resend":
            return await self._send_via_resend(
                to_email=to_email,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                attachments=attachments,
            )

        if provider == "smtp":
            try:
                await asyncio.to_thread(
                    self._send_sync,
                    to_email,
                    subject,
                    body_text,
                    body_html,
                    attachments,
                )
                logger.info("Email sent via SMTP to %s with subject '%s'", to_email, subject)
                return True
            except Exception as error:
                logger.error("SMTP send failed for %s: %s", to_email, error, exc_info=True)
                return False

        if not self.is_configured:
            logger.warning(
                "Email provider not configured. Missing: %s. Skipping email for %s",
                ", ".join(self.missing_config_fields()),
                to_email,
            )
            return False

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
