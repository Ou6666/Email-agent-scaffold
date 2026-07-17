from app.config import get_settings
from app.storage.database import init_db
from app.storage.repository import EmailRepository
from app.workflow import EmailAgentWorkflow


def main() -> None:
    settings = get_settings()
    init_db()

    workflow = EmailAgentWorkflow(settings)
    processed = workflow.run_once()
    repository = EmailRepository()

    print(f"{settings.app_name} initialized")
    print(f"Provider: {settings.email_provider}")
    print(f"Database: {settings.database_url}")
    print(f"Processed new emails: {len(processed)}")
    print(f"Total saved emails: {repository.count()}")


if __name__ == "__main__":
    main()
