from datetime import datetime, timezone

from app.agent.schemas import EmailAttachment, EmailMessage


class MockEmailClient:
    def list_recent_messages(
        self, limit: int = 10, query: str | None = None
    ) -> list[EmailMessage]:
        messages = [
            EmailMessage(
                email_id="mock-001",
                thread_id="mock-thread-001",
                sender="Career Center <career@example.edu>",
                subject="Data analyst internship deadline tomorrow",
                received_at=datetime.now(timezone.utc),
                body_text=(
                    "A data analyst internship is open for applications. "
                    "The deadline is tomorrow at 17:00. Please submit your CV "
                    "and portfolio through the application portal."
                ),
                attachments=[
                    EmailAttachment(
                        filename="internship_description.pdf",
                        mime_type="application/pdf",
                        size_bytes=245_000,
                        text_preview="Role description, requirements, and deadline.",
                    )
                ],
            ),
            EmailMessage(
                email_id="mock-002",
                thread_id="mock-thread-002",
                sender="Professor Silva <professor@example.edu>",
                subject="Please confirm your project meeting",
                received_at=datetime.now(timezone.utc),
                body_text=(
                    "Can you confirm if you are available for a project meeting "
                    "next Monday? Please reply with your preferred time."
                ),
            ),
            EmailMessage(
                email_id="mock-003",
                thread_id="mock-thread-003",
                sender="Promo Team <offers@example.com>",
                subject="Limited sale: 20% off productivity tools",
                received_at=datetime.now(timezone.utc),
                body_text=(
                    "This newsletter includes a discount for productivity tools. "
                    "No action is required unless you want to browse the offer."
                ),
            ),
        ]
        return messages[:limit]

