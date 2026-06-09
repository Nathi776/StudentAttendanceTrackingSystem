from __future__ import annotations

import json
import logging
from email.utils import parseaddr
from urllib import error, request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class SendGridEmailBackend(BaseEmailBackend):
    """Send Django email messages through the SendGrid transactional email API."""

    api_url = "https://api.sendgrid.com/v3/mail/send"

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent_count = 0
        for email_message in email_messages:
            self._send_message(email_message)
            sent_count += 1
        return sent_count

    def _send_message(self, email_message):
        api_key = getattr(settings, "SENDGRID_API_KEY", "").strip()
        from_email = getattr(settings, "SENDGRID_FROM_EMAIL", "").strip() or email_message.from_email

        if not api_key:
            raise ValueError("SENDGRID_API_KEY is not configured.")

        payload = {
            "personalizations": [
                {
                    "to": [{"email": self._normalize_address(recipient)} for recipient in email_message.to],
                }
            ],
            "from": {"email": self._normalize_address(from_email)},
            "subject": email_message.subject,
            "content": self._build_content(email_message),
        }

        if email_message.reply_to:
            payload["reply_to"] = {"email": self._normalize_address(email_message.reply_to[0])}

        if email_message.cc:
            payload["personalizations"][0]["cc"] = [
                {"email": self._normalize_address(recipient)} for recipient in email_message.cc
            ]

        if email_message.bcc:
            payload["personalizations"][0]["bcc"] = [
                {"email": self._normalize_address(recipient)} for recipient in email_message.bcc
            ]

        req = request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

        timeout = getattr(settings, "EMAIL_TIMEOUT", 10)
        try:
            with request.urlopen(req, timeout=timeout) as response:
                if response.status not in (200, 202):
                    raise error.HTTPError(self.api_url, response.status, response.reason, response.headers, None)
        except error.HTTPError:
            logger.exception("SendGrid returned an error response")
            raise
        except error.URLError:
            logger.exception("Failed to connect to SendGrid")
            raise

    def _build_content(self, email_message):
        content = []

        if email_message.body:
            content.append({"type": "text/plain", "value": email_message.body})

        html_body = None
        for alternative, mimetype in getattr(email_message, "alternatives", []):
            if mimetype == "text/html":
                html_body = alternative
                break

        if html_body:
            content.append({"type": "text/html", "value": html_body})

        if not content:
            content.append({"type": "text/plain", "value": ""})

        return content

    @staticmethod
    def _normalize_address(value):
        _, addr = parseaddr(value)
        return addr or value
