from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EmailAttachment(BaseModel):
    filename: str
    mime_type: str | None = None
    size_bytes: int | None = None
    text_preview: str | None = None


class EmailMessage(BaseModel):
    email_id: str
    thread_id: str | None = None
    sender: str
    subject: str
    received_at: datetime
    body_text: str
    attachments: list[EmailAttachment] = Field(default_factory=list)


class EmailAnalysis(BaseModel):
    priority: int = Field(ge=1, le=5)
    category: str
    needs_reply: bool = False
    needs_follow_up: bool = False
    summary: str
    key_points: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    deadline: str | None = None
    opportunity_score: int = Field(default=0, ge=0, le=10)
    quality_score: int = Field(default=0, ge=0, le=10)
    quality_label: str = "unknown"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class ProcessedEmail(BaseModel):
    message: EmailMessage
    analysis: EmailAnalysis
    processed_at: datetime
    notified: bool = False
