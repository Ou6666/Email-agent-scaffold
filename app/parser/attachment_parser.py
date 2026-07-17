from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from app.agent.schemas import EmailAttachment


MAX_ATTACHMENT_TEXT_CHARS = 40_000
MAX_ATTACHMENT_PREVIEW_CHARS = 1_500


@dataclass(frozen=True)
class AttachmentParseResult:
    filename: str
    mime_type: str | None
    size_bytes: int
    text: str
    text_preview: str
    supported: bool
    error: str | None = None


class AttachmentParser:
    def parse_file(
        self,
        path: str | Path,
        *,
        mime_type: str | None = None,
    ) -> AttachmentParseResult:
        file_path = Path(path)
        size_bytes = file_path.stat().st_size
        suffix = file_path.suffix.lower()

        try:
            if suffix in {".txt", ".md", ".csv", ".json", ".log"}:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            elif suffix == ".pdf":
                text = self._extract_pdf(file_path)
            elif suffix == ".docx":
                text = self._extract_docx(file_path)
            else:
                return AttachmentParseResult(
                    filename=file_path.name,
                    mime_type=mime_type,
                    size_bytes=size_bytes,
                    text="",
                    text_preview="",
                    supported=False,
                    error=f"Unsupported attachment type: {suffix or 'unknown'}",
                )
        except Exception as error:
            return AttachmentParseResult(
                filename=file_path.name,
                mime_type=mime_type,
                size_bytes=size_bytes,
                text="",
                text_preview="",
                supported=False,
                error=str(error),
            )

        text = _normalize_text(text)[:MAX_ATTACHMENT_TEXT_CHARS]
        return AttachmentParseResult(
            filename=file_path.name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            text=text,
            text_preview=text[:MAX_ATTACHMENT_PREVIEW_CHARS],
            supported=True,
        )

    def to_email_attachment(
        self,
        path: str | Path,
        *,
        mime_type: str | None = None,
    ) -> EmailAttachment:
        result = self.parse_file(path, mime_type=mime_type)
        return EmailAttachment(
            filename=result.filename,
            mime_type=result.mime_type,
            size_bytes=result.size_bytes,
            text_preview=result.text_preview or result.error,
        )

    def _extract_pdf(self, file_path: Path) -> str:
        reader = PdfReader(str(file_path))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n\n".join(pages)

    def _extract_docx(self, file_path: Path) -> str:
        document = Document(str(file_path))
        paragraphs = [paragraph.text for paragraph in document.paragraphs]
        return "\n".join(paragraphs)


def summarize_attachments(attachments: list[EmailAttachment]) -> str:
    if not attachments:
        return ""

    lines = []
    for attachment in attachments:
        preview = attachment.text_preview or "No text preview available."
        lines.append(f"{attachment.filename}: {preview}")
    return "\n".join(lines)


def _normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    collapsed = "\n".join(line for line in lines if line)
    return collapsed.strip()
