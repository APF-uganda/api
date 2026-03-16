import base64
from email.utils import formataddr, parseaddr
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class EmailBackend(BaseEmailBackend):
    """Django email backend that sends messages using the Gmail API."""

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.scopes = getattr(
            settings,
            "GMAIL_SCOPES",
            ["https://www.googleapis.com/auth/gmail.send"],
        )
        self.user_id = getattr(settings, "GMAIL_USER_ID", "me")
        token_file = getattr(settings, "GMAIL_TOKEN_FILE", "token.json")
        token_path = Path(token_file)
        if not token_path.is_absolute():
            token_path = Path(settings.BASE_DIR) / token_file
        self.token_path = token_path
        self._service = None

    def _load_credentials(self):
        if not self.token_path.exists():
            raise ImproperlyConfigured(
                f"Gmail token file not found: {self.token_path}"
            )

        creds = Credentials.from_authorized_user_file(str(self.token_path), self.scopes)

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self.token_path.write_text(creds.to_json(), encoding="utf-8")

        if not creds.valid:
            raise ImproperlyConfigured(
                "Gmail credentials are invalid. Re-run gmail_auth.py to generate token.json."
            )

        return creds

    def _get_service(self):
        if self._service is None:
            creds = self._load_credentials()
            self._service = build("gmail", "v1", credentials=creds)
        return self._service

    def _normalize_from_email(self, from_email):
        default_from = getattr(settings, "DEFAULT_FROM_EMAIL", "")
        default_name, default_addr = parseaddr(default_from)
        from_name, from_addr = parseaddr(from_email or "")

        # Keep the sender address, but ensure a display name is always present.
        sender_addr = from_addr or default_addr
        sender_name = from_name or default_name or "APF Uganda"

        if not sender_addr:
            raise ImproperlyConfigured(
                "No sender address configured. Set DEFAULT_FROM_EMAIL in settings/.env."
            )

        return formataddr((sender_name, sender_addr))

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        try:
            service = self._get_service()
        except Exception:
            if self.fail_silently:
                return 0
            raise

        sent = 0
        for email_message in email_messages:
            try:
                email_message.from_email = self._normalize_from_email(
                    getattr(email_message, "from_email", "")
                )
                mime_message = email_message.message()
                # Django keeps bcc outside MIME headers; include it for Gmail API delivery.
                if getattr(email_message, "bcc", None):
                    mime_message["Bcc"] = ", ".join(email_message.bcc)

                raw = base64.urlsafe_b64encode(
                    mime_message.as_bytes()
                ).decode("utf-8")

                service.users().messages().send(
                    userId=self.user_id,
                    body={"raw": raw},
                ).execute()
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise

        return sent
