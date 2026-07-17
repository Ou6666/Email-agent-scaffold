from apscheduler.schedulers.blocking import BlockingScheduler

from app.config import get_settings
from app.storage.database import init_db
from app.workflow import EmailAgentWorkflow


def start_scheduler() -> None:
    settings = get_settings()
    init_db()

    workflow = EmailAgentWorkflow(settings)
    scheduler = BlockingScheduler()
    scheduler.add_job(
        workflow.run_once,
        "interval",
        minutes=settings.scheduler_interval_minutes,
        id="email-agent-hourly-check",
        replace_existing=True,
    )

    print(
        f"Scheduler started. Checking emails every "
        f"{settings.scheduler_interval_minutes} minutes."
    )
    workflow.run_once()
    scheduler.start()


if __name__ == "__main__":
    start_scheduler()

