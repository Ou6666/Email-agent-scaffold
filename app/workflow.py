from datetime import datetime, timezone

from app.agent.factory import build_analyzer
from app.agent.schemas import EmailMessage, ProcessedEmail
from app.config import Settings, get_settings
from app.email_client.mock_client import MockEmailClient
from app.notification.factory import build_notifier
from app.parser.email_parser import EmailParser
from app.storage.repository import EmailRepository


class EmailAgentWorkflow:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.repository = EmailRepository()
        self.parser = EmailParser()
        self.analyzer = build_analyzer(self.settings)
        self.notifier = build_notifier(self.settings)

    def run_once(self) -> list[ProcessedEmail]:
        client = self._build_email_client()
        messages = client.list_recent_messages(limit=self.settings.fetch_limit)

        processed: list[ProcessedEmail] = []
        high_priority: list[ProcessedEmail] = []

        for message in messages:
            if self.repository.email_exists(message.email_id):
                continue

            clean_message = self.parser.normalize(message)
            analysis = self.analyzer.analyze(clean_message)
            should_notify = analysis.priority >= self.settings.minimum_notify_priority

            self.repository.save_analysis(
                clean_message,
                analysis,
                notified=should_notify,
            )

            processed_email = ProcessedEmail(
                message=clean_message,
                analysis=analysis,
                processed_at=datetime.now(timezone.utc),
                notified=should_notify,
            )
            processed.append(processed_email)
            if should_notify:
                high_priority.append(processed_email)

        self.notifier.send_digest(high_priority)
        return processed

    def _build_email_client(self):
        provider = self.settings.email_provider.lower()
        if provider == "mock":
            return MockEmailClient()
        if provider == "gmail":
            from app.email_client.gmail_client import GmailClient

            return GmailClient(self.settings)
        if provider == "outlook":
            from app.email_client.outlook_client import OutlookClient

            return OutlookClient(self.settings)
        raise ValueError(f"Unsupported EMAIL_PROVIDER: {self.settings.email_provider}")
