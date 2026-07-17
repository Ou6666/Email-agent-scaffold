from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings


settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db() -> None:
    from app.storage import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()


def _ensure_sqlite_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    required_columns = {
        "attachments_json": "TEXT DEFAULT '[]'",
        "attachment_summary": "TEXT DEFAULT ''",
        "quality_score": "INTEGER DEFAULT 0",
        "quality_label": "VARCHAR(32) DEFAULT 'unknown'",
    }

    with engine.begin() as connection:
        existing_columns = {
            row[1]
            for row in connection.exec_driver_sql(
                "PRAGMA table_info(email_records)"
            ).all()
        }
        for column_name, column_definition in required_columns.items():
            if column_name not in existing_columns:
                connection.exec_driver_sql(
                    f"ALTER TABLE email_records ADD COLUMN {column_name} {column_definition}"
                )
