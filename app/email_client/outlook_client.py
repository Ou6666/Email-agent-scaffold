from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import msal
import requests

from app.agent.schemas import EmailMessage
from app.config import Settings, get_settings


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


class OutlookClientError(RuntimeError):
    pass


class OutlookClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.outlook_client_id:
            raise OutlookClientError(
                "OUTLOOK_CLIENT_ID is missing. Create a Microsoft Entra app "
                "registration and put its Application (client) ID in .env."
            )

        self.token_cache_path = Path(self.settings.outlook_token_cache_path)
        self.token_cache = msal.SerializableTokenCache()
        if self.token_cache_path.exists():
            self.token_cache.deserialize(self.token_cache_path.read_text())

        self.app = msal.PublicClientApplication(
            client_id=self.settings.outlook_client_id,
            authority=self.settings.outlook_authority,
            token_cache=self.token_cache,
        )

    def get_access_token(self) -> str:
        account = self._find_cached_account()
        result = None
        scopes = self.settings.outlook_scopes or ["User.Read", "Mail.Read"]

        if account:
            result = self.app.acquire_token_silent(scopes=scopes, account=account)

        if not result:
            flow = self.app.initiate_device_flow(scopes=scopes)
            if "user_code" not in flow:
                raise OutlookClientError(f"Could not create device flow: {flow}")

            print(flow["message"])
            result = self.app.acquire_token_by_device_flow(flow)

        self._save_token_cache()

        if "access_token" not in result:
            error = result.get("error", "unknown_error")
            description = result.get("error_description", "")
            raise OutlookClientError(f"Could not acquire token: {error} {description}")

        return result["access_token"]

    def list_recent_messages(self, limit: int = 10) -> list[EmailMessage]:
        token = self.get_access_token()
        response = requests.get(
            f"{GRAPH_BASE_URL}/me/messages",
            headers={
                "Authorization": f"Bearer {token}",
                "Prefer": 'outlook.body-content-type="text"',
            },
            params={
                "$top": str(limit),
                "$orderby": "receivedDateTime desc",
                "$select": (
                    "id,conversationId,sender,subject,receivedDateTime,"
                    "body,hasAttachments"
                ),
            },
            timeout=30,
        )

        if response.status_code >= 400:
            raise OutlookClientError(
                f"Graph request failed: {response.status_code} {response.text}"
            )

        payload = response.json()
        return [self._to_email_message(item) for item in payload.get("value", [])]

    def _find_cached_account(self) -> dict[str, Any] | None:
        accounts = self.app.get_accounts(username=self.settings.outlook_user_email)
        if accounts:
            return accounts[0]

        accounts = self.app.get_accounts()
        return accounts[0] if accounts else None

    def _save_token_cache(self) -> None:
        if self.token_cache.has_state_changed:
            self.token_cache_path.write_text(self.token_cache.serialize())

    def _to_email_message(self, item: dict[str, Any]) -> EmailMessage:
        sender = item.get("sender", {}).get("emailAddress", {})
        sender_name = sender.get("name")
        sender_address = sender.get("address", "unknown")
        sender_text = (
            f"{sender_name} <{sender_address}>" if sender_name else sender_address
        )

        received_at = _parse_graph_datetime(item.get("receivedDateTime"))
        body = item.get("body", {}) or {}

        return EmailMessage(
            email_id=item["id"],
            thread_id=item.get("conversationId"),
            sender=sender_text,
            subject=item.get("subject") or "(no subject)",
            received_at=received_at,
            body_text=body.get("content") or "",
            attachments=[],
        )


def _parse_graph_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.utcnow()
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> None:
    client = OutlookClient()
    messages = client.list_recent_messages(limit=5)

    print(f"Fetched {len(messages)} Outlook messages")
    for message in messages:
        print(f"- {message.received_at} | {message.sender} | {message.subject}")


if __name__ == "__main__":
    main()
