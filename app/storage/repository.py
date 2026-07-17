from datetime import datetime
import json

from sqlalchemy import func, or_, select

from app.agent.schemas import EmailAnalysis, EmailMessage
from app.parser.attachment_parser import summarize_attachments
from app.storage.database import SessionLocal
from app.storage.models import EmailRecord


class EmailRepository:
    def email_exists(self, email_id: str) -> bool:
        with SessionLocal() as session:
            result = session.execute(
                select(EmailRecord.id).where(EmailRecord.email_id == email_id)
            ).first()
            return result is not None

    def save_analysis(
        self,
        message: EmailMessage,
        analysis: EmailAnalysis,
        *,
        notified: bool = False,
    ) -> EmailRecord:
        with SessionLocal() as session:
            existing = session.execute(
                select(EmailRecord).where(EmailRecord.email_id == message.email_id)
            ).scalar_one_or_none()

            record = existing or EmailRecord(email_id=message.email_id)
            record.thread_id = message.thread_id
            record.sender = message.sender
            record.subject = message.subject
            record.received_at = message.received_at
            record.body_text = message.body_text
            record.has_attachments = len(message.attachments) > 0
            record.attachments_json = json.dumps(
                [attachment.model_dump() for attachment in message.attachments],
                ensure_ascii=False,
            )
            record.attachment_summary = summarize_attachments(message.attachments)

            record.summary = analysis.summary
            record.priority = analysis.priority
            record.category = analysis.category
            record.needs_reply = analysis.needs_reply
            record.needs_follow_up = analysis.needs_follow_up
            record.opportunity_score = analysis.opportunity_score
            record.quality_score = analysis.quality_score
            record.quality_label = analysis.quality_label
            record.deadline = analysis.deadline
            record.confidence = int(analysis.confidence * 100)
            record.key_points_json = json.dumps(analysis.key_points, ensure_ascii=False)
            record.action_items_json = json.dumps(
                analysis.action_items, ensure_ascii=False
            )
            record.analysis_json = analysis.model_dump_json()
            record.processed_at = datetime.utcnow()
            record.notified = notified

            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def list_high_priority(self, minimum_priority: int = 4) -> list[EmailRecord]:
        with SessionLocal() as session:
            records = session.execute(
                select(EmailRecord)
                .where(EmailRecord.priority >= minimum_priority)
                .order_by(EmailRecord.received_at.desc())
            ).scalars()
            return list(records)

    def list_recent(self, limit: int = 20) -> list[EmailRecord]:
        with SessionLocal() as session:
            records = session.execute(
                select(EmailRecord)
                .order_by(EmailRecord.received_at.desc())
                .limit(limit)
            ).scalars()
            return list(records)

    def list_by_quality(self, quality_label: str, limit: int = 20) -> list[EmailRecord]:
        with SessionLocal() as session:
            records = session.execute(
                select(EmailRecord)
                .where(EmailRecord.quality_label == quality_label)
                .order_by(EmailRecord.received_at.desc())
                .limit(limit)
            ).scalars()
            return list(records)

    def quality_summary(self) -> dict[str, int]:
        with SessionLocal() as session:
            rows = session.execute(
                select(EmailRecord.quality_label, func.count(EmailRecord.id))
                .group_by(EmailRecord.quality_label)
            ).all()
            return {label or "unknown": count for label, count in rows}

    def backfill_quality_fields(self) -> int:
        updated = 0
        with SessionLocal() as session:
            records = session.execute(
                select(EmailRecord).where(
                    or_(
                        EmailRecord.quality_label.is_(None),
                        EmailRecord.quality_label == "unknown",
                    )
                )
            ).scalars()

            for record in records:
                record.quality_score = _estimate_quality_score(
                    priority=record.priority,
                    opportunity_score=record.opportunity_score,
                    category=record.category,
                )
                record.quality_label = _quality_label(record.quality_score)
                updated += 1

            session.commit()
        return updated

    def count(self) -> int:
        with SessionLocal() as session:
            return len(session.execute(select(EmailRecord.id)).all())


def _estimate_quality_score(
    *,
    priority: int,
    opportunity_score: int,
    category: str,
) -> int:
    if category == "promotion":
        return 2 if priority <= 2 else 4
    score = max(priority * 2, opportunity_score)
    if category in {"job_opportunity", "academic_opportunity", "meeting"}:
        score += 1
    return min(score, 10)


def _quality_label(quality_score: int) -> str:
    if quality_score >= 7:
        return "high"
    if quality_score >= 4:
        return "medium"
    return "low"
