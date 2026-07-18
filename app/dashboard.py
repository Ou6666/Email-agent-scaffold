import sys
from typing import TextIO

from app.storage.database import init_db
from app.storage.repository import EmailRepository


def _configure_utf8_output(stream: TextIO) -> None:
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    _configure_utf8_output(sys.stdout)
    init_db()
    repository = EmailRepository()
    backfilled = repository.backfill_quality_fields()
    summary = repository.quality_summary()
    recent_records = repository.list_recent(limit=10)

    print("Email Quality Dashboard")
    print("=" * 32)
    print(f"Total analyzed emails: {repository.count()}")
    if backfilled:
        print(f"Backfilled quality labels: {backfilled}")
    print(f"High quality: {summary.get('high', 0)}")
    print(f"Medium quality: {summary.get('medium', 0)}")
    print(f"Low quality: {summary.get('low', 0)}")
    unknown = summary.get("unknown", 0)
    if unknown:
        print(f"Unknown quality: {unknown}")

    print("\nRecent analysis records")
    print("-" * 32)
    if not recent_records:
        print("No records yet.")
        return

    for record in recent_records:
        print(
            f"[{record.quality_label.upper()} | P{record.priority} | "
            f"opp {record.opportunity_score}/10] {record.subject}"
        )
        print(f"From: {record.sender}")
        print(f"Summary: {record.summary}")
        if record.deadline:
            print(f"Deadline: {record.deadline}")
        print("-" * 32)


if __name__ == "__main__":
    main()
