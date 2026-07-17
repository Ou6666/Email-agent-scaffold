from __future__ import annotations

import json

from twilio.rest import Client

from app.agent.schemas import ProcessedEmail
from app.config import Settings, get_settings


class WhatsAppConfigError(RuntimeError):
    pass


class WhatsAppNotifier:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._validate_config()
        self.client = Client(
            self.settings.twilio_account_sid,
            self.settings.twilio_auth_token,
        )

    def send_message(self, body: str) -> str:
        kwargs = {
            "from_": _whatsapp_address(self.settings.twilio_whatsapp_from),
            "to": _whatsapp_address(self.settings.whatsapp_to),
        }

        if self.settings.twilio_content_sid:
            kwargs["content_sid"] = self.settings.twilio_content_sid
            kwargs["content_variables"] = parse_content_variables(
                self.settings.twilio_content_variables
            )
        else:
            kwargs["body"] = body

        message = self.client.messages.create(**kwargs)
        return message.sid

    def send_digest(self, emails: list[ProcessedEmail]) -> None:
        if not emails:
            return
        body = _format_digest(emails)
        sid = self.send_message(body)
        print(f"WhatsApp digest sent: {sid}")

    def _validate_config(self) -> None:
        missing = [
            name
            for name, value in {
                "TWILIO_ACCOUNT_SID": self.settings.twilio_account_sid,
                "TWILIO_AUTH_TOKEN": self.settings.twilio_auth_token,
                "TWILIO_WHATSAPP_FROM": self.settings.twilio_whatsapp_from,
                "WHATSAPP_TO": self.settings.whatsapp_to,
            }.items()
            if not value
        ]
        if missing:
            raise WhatsAppConfigError(
                "Missing WhatsApp/Twilio config: " + ", ".join(missing)
            )


def _whatsapp_address(value: str | None) -> str:
    if not value:
        raise WhatsAppConfigError("WhatsApp number is missing.")
    value = value.strip()
    if value.startswith("whatsapp:"):
        return value
    return f"whatsapp:{value}"


def _format_digest(emails: list[ProcessedEmail]) -> str:
    lines = ["Email Agent digest"]
    for processed in emails[:5]:
        message = processed.message
        analysis = processed.analysis
        lines.append("")
        lines.append(f"[P{analysis.priority}] {message.subject}")
        lines.append(f"From: {message.sender}")
        lines.append(f"Summary: {analysis.summary}")
        if analysis.deadline:
            lines.append(f"Deadline: {analysis.deadline}")
        if analysis.action_items:
            lines.append("Actions: " + "; ".join(analysis.action_items[:3]))
    return "\n".join(lines)


def parse_content_variables(value: str | None) -> str:
    if not value:
        return "{}"
    json.loads(value)
    return value
