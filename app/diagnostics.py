from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import json

from googleapiclient.errors import HttpError
from twilio.base.exceptions import TwilioRestException

from app.config import BASE_DIR, Settings, get_settings
from app.email_client.gmail_client import GmailClient, GmailClientError
from app.notification.whatsapp import (
    WhatsAppConfigError,
    WhatsAppNotifier,
    parse_content_variables,
)


@dataclass(frozen=True)
class DiagnosticResult:
    name: str
    ok: bool
    message: str


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check Gmail and WhatsApp connectivity for Email Agent."
    )
    parser.add_argument(
        "--gmail-live",
        action="store_true",
        help="Try to read one real Gmail message. May open browser OAuth login.",
    )
    parser.add_argument(
        "--whatsapp-send",
        action="store_true",
        help="Send a real WhatsApp test message through Twilio.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all live tests.",
    )
    args = parser.parse_args()

    settings = get_settings()
    results = [
        check_gmail_config(settings),
        check_whatsapp_config(settings),
    ]

    if args.gmail_live or args.all:
        results.append(test_gmail_connection(settings))

    if args.whatsapp_send or args.all:
        results.append(send_whatsapp_test(settings))

    print_results(results)

    if any(not result.ok for result in results):
        raise SystemExit(1)


def check_gmail_config(settings: Settings) -> DiagnosticResult:
    credentials_path = _resolve_project_path(settings.gmail_credentials_path)
    token_path = _resolve_project_path(settings.gmail_token_path)

    if not settings.gmail_user_email:
        return DiagnosticResult("Gmail config", False, "GMAIL_USER_EMAIL is missing.")

    if not credentials_path.exists():
        return DiagnosticResult(
            "Gmail config",
            False,
            f"Missing credentials file: {credentials_path}",
        )

    credential_type = _google_credentials_type(credentials_path)
    if credential_type == "web":
        return DiagnosticResult(
            "Gmail config",
            False,
            (
                "credentials.json is a Web application OAuth client. Create a new "
                "OAuth Client ID with Application type 'Desktop app', download it, "
                "and replace credentials.json."
            ),
        )
    if credential_type != "installed":
        return DiagnosticResult(
            "Gmail config",
            False,
            "credentials.json is not a recognized Desktop OAuth client file.",
        )

    token_note = "token.json exists" if token_path.exists() else "token.json not created yet"
    return DiagnosticResult(
        "Gmail config",
        True,
        f"Credentials ready for {settings.gmail_user_email}; {token_note}.",
    )


def test_gmail_connection(settings: Settings) -> DiagnosticResult:
    try:
        client = GmailClient(settings)
        messages = client.list_recent_messages(limit=1)
    except GmailClientError as error:
        return DiagnosticResult("Gmail live test", False, str(error))
    except HttpError as error:
        return DiagnosticResult("Gmail live test", False, f"Gmail API error: {error}")
    except Exception as error:
        return DiagnosticResult("Gmail live test", False, f"Unexpected error: {error}")

    if not messages:
        return DiagnosticResult("Gmail live test", True, "Connected. Inbox returned no messages.")

    message = messages[0]
    return DiagnosticResult(
        "Gmail live test",
        True,
        f"Connected. Latest message: {message.subject} from {message.sender}",
    )


def check_whatsapp_config(settings: Settings) -> DiagnosticResult:
    missing = [
        name
        for name, value in {
            "TWILIO_ACCOUNT_SID": settings.twilio_account_sid,
            "TWILIO_AUTH_TOKEN": settings.twilio_auth_token,
            "TWILIO_WHATSAPP_FROM": settings.twilio_whatsapp_from,
            "WHATSAPP_TO": settings.whatsapp_to,
        }.items()
        if not value
    ]
    if missing:
        return DiagnosticResult(
            "WhatsApp config",
            False,
            "Missing config: " + ", ".join(missing),
        )

    try:
        parse_content_variables(settings.twilio_content_variables)
    except Exception as error:
        return DiagnosticResult(
            "WhatsApp config",
            False,
            f"TWILIO_CONTENT_VARIABLES is not valid JSON: {error}",
        )

    return DiagnosticResult(
        "WhatsApp config",
        True,
        (
            f"Twilio config present. From {_mask(settings.twilio_whatsapp_from)} "
            f"to {_mask(settings.whatsapp_to)}."
        ),
    )


def send_whatsapp_test(settings: Settings) -> DiagnosticResult:
    body = (
        "Email Agent environment test: WhatsApp delivery is connected. "
        "Next step is linking this to Gmail analysis."
    )
    try:
        notifier = WhatsAppNotifier(settings)
        sid = notifier.send_message(body)
    except WhatsAppConfigError as error:
        return DiagnosticResult("WhatsApp send test", False, str(error))
    except TwilioRestException as error:
        return DiagnosticResult("WhatsApp send test", False, f"Twilio error: {error}")
    except Exception as error:
        return DiagnosticResult("WhatsApp send test", False, f"Unexpected error: {error}")

    return DiagnosticResult("WhatsApp send test", True, f"Message sent. SID: {sid}")


def print_results(results: list[DiagnosticResult]) -> None:
    print("Email Agent Diagnostics")
    print("=" * 32)
    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"[{status}] {result.name}")
        print(result.message)
        print("-" * 32)


def _resolve_project_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else BASE_DIR / path


def _google_credentials_type(path: Path) -> str:
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return "invalid"
    if "installed" in payload:
        return "installed"
    if "web" in payload:
        return "web"
    return "unknown"


def _mask(value: str | None) -> str:
    if not value:
        return "(missing)"
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


if __name__ == "__main__":
    main()
