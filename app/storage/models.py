from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


class EmailRecord(Base):
    __tablename__ = "email_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sender: Mapped[str] = mapped_column(String(512))
    subject: Mapped[str] = mapped_column(String(1024))
    received_at: Mapped[datetime] = mapped_column(DateTime)
    body_text: Mapped[str] = mapped_column(Text)
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    attachments_json: Mapped[str] = mapped_column(Text, default="[]")
    attachment_summary: Mapped[str] = mapped_column(Text, default="")

    summary: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(128))
    needs_reply: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_follow_up: Mapped[bool] = mapped_column(Boolean, default=False)
    opportunity_score: Mapped[int] = mapped_column(Integer, default=0)
    quality_score: Mapped[int] = mapped_column(Integer, default=0)
    quality_label: Mapped[str] = mapped_column(String(32), default="unknown")
    deadline: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, default=0)

    key_points_json: Mapped[str] = mapped_column(Text, default="[]")
    action_items_json: Mapped[str] = mapped_column(Text, default="[]")
    analysis_json: Mapped[str] = mapped_column(Text, default="{}")

    processed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
