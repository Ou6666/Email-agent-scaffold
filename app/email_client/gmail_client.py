from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import html2text
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.agent.schemas import EmailAttachment, EmailMessage
from app.config import BASE_DIR, Settings, get_settings


class GmailClientError(RuntimeError):
    pass


class GmailClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.scopes = self.settings.gmail_scopes or [
            "https://www.googleapis.com/auth/gmail.readonly"
        ]
        self.credentials_path = _resolve_path(self.settings.gmail_credentials_path)
        self.token_path = _resolve_path(self.settings.gmail_token_path)

    def list_recent_messages(self, limit: int = 10, query: str | None = None) -> list[EmailMessage]:
        service = self._build_service()
        request = (
            service.users()
            .messages()
            .list(
                userId="me",
                maxResults=limit,
                q=query,
                includeSpamTrash=False,
            )
        )
        result = request.execute()
        messages = result.get("messages", [])

        return [self.get_message(message["id"], service=service) for message in messages]

    def get_message(self, message_id: str, service: Any | None = None) -> EmailMessage:
        service = service or self._build_service()
        raw_message = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        return self._to_email_message(raw_message)

    def _build_service(self) -> Any:
        creds = self._load_credentials()
        return build("gmail", "v1", credentials=creds)

    def _load_credentials(self) -> Credentials:
        creds = None
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), self.scopes)

        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not self.credentials_path.exists():
                raise GmailClientError(
                    "Gmail credentials file is missing. Download OAuth Desktop app "
                    f"credentials from Google Cloud and save it at {self.credentials_path}."
                )
            self._validate_credentials_file()
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self.credentials_path), self.scopes
            )
            creds = flow.run_local_server(port=0)

        self.token_path.write_text(creds.to_json())
        return creds

    def _validate_credentials_file(self) -> None:
        payload = json.loads(self.credentials_path.read_text())
        if "installed" in payload:
            return
        if "web" in payload:
            raise GmailClientError(
                "credentials.json is a Web application OAuth client. Create an "
                "OAuth Client ID with Application type 'Desktop app', download it, "
                "and replace credentials.json."
            )
        raise GmailClientError(
            "credentials.json is not a recognized Google OAuth client file."
        )

    def _to_email_message(self, raw_message: dict[str, Any]) -> EmailMessage:
        payload = raw_message.get("payload", {})
        headers = payload.get("headers", [])
        subject = _get_header(headers, "Subject") or "(no subject)"
        sender = _get_header(headers, "From") or "unknown"
        received_at = _parse_received_at(raw_message, headers)
        body_text, attachments = _extract_message_content(payload)

        return EmailMessage(
            email_id=raw_message["id"],
            thread_id=raw_message.get("threadId"),
            sender=sender,
            subject=subject,
            received_at=received_at,
            body_text=body_text.strip(),
            attachments=attachments,
        )


def _resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else BASE_DIR / path


def _get_header(headers: list[dict[str, str]], name: str) -> str | None:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value")
    return None


def _parse_received_at(raw_message: dict[str, Any], headers: list[dict[str, str]]) -> datetime:
    internal_date = raw_message.get("internalDate")
    if internal_date:
        return datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)

    date_header = _get_header(headers, "Date")
    if date_header:
        parsed = parsedate_to_datetime(date_header)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    return datetime.now(timezone.utc)


def _extract_message_content(payload: dict[str, Any]) -> tuple[str, list[EmailAttachment]]:
    text_parts: list[str] = []
    html_parts: list[str] = []
    attachments: list[EmailAttachment] = []

    def walk(part: dict[str, Any]) -> None:
        filename = part.get("filename")
        mime_type = part.get("mimeType")
        body = part.get("body", {})

        if filename:
            attachments.append(
                EmailAttachment(
                    filename=filename,
                    mime_type=mime_type,
                    size_bytes=body.get("size"),
                )
            )
            return

        data = body.get("data")
        if data and mime_type in {"text/plain", "text/html"}:
            decoded = _decode_base64url(data)
            if mime_type == "text/plain":
                text_parts.append(decoded)
            else:
                html_parts.append(_html_to_text(decoded))

        for child in part.get("parts", []) or []:
            walk(child)

    walk(payload)

    body_text = "\n\n".join(part for part in text_parts if part.strip())
    if not body_text:
        body_text = "\n\n".join(part for part in html_parts if part.strip())

    return body_text, attachments


def _decode_base64url(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    decoded = base64.urlsafe_b64decode(value + padding)
    return decoded.decode("utf-8", errors="replace")


def _html_to_text(value: str) -> str:
    converter = html2text.HTML2Text()
    converter.body_width = 0
    converter.ignore_images = True
    converter.ignore_emphasis = True
    converter.ignore_links = False
    return converter.handle(value)


def main() -> None:
    client = GmailClient()
    try:
        messages = client.list_recent_messages(limit=5)
    except HttpError as error:
        raise GmailClientError(f"Gmail API request failed: {error}") from error

    print(f"Fetched {len(messages)} Gmail messages")
    for message in messages:
        attachment_note = f" ({len(message.attachments)} attachments)" if message.attachments else ""
        print(f"- {message.received_at} | {message.sender} | {message.subject}{attachment_note}")


if __name__ == "__main__":
    main()
