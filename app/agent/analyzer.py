from __future__ import annotations

import html
import re

from app.agent.schemas import EmailAnalysis, EmailMessage


class RuleBasedEmailAnalyzer:
    def analyze(self, message: EmailMessage) -> EmailAnalysis:
        subject_text = _normalize_for_matching(message.subject)
        sender_text = _normalize_for_matching(message.sender)
        body_text = _normalize_for_matching(message.body_text)
        text = f"{subject_text} {sender_text} {body_text}"
        category = self._category(subject_text, sender_text, body_text)
        priority = self._priority(text, category, bool(message.attachments))
        needs_reply = self._needs_reply(text)
        needs_follow_up = needs_reply or category in {
            "job_opportunity",
            "academic_opportunity",
            "meeting",
            "account_or_security",
        }
        deadline = self._deadline(text)
        opportunity_score = self._opportunity_score(text, category)
        quality_score = self._quality_score(priority, opportunity_score, category)

        return EmailAnalysis(
            priority=priority,
            category=category,
            needs_reply=needs_reply,
            needs_follow_up=needs_follow_up,
            summary=self._summary(message, category),
            key_points=self._key_points(message, category, deadline),
            action_items=self._action_items(text, category, needs_reply, deadline),
            deadline=deadline,
            opportunity_score=opportunity_score,
            quality_score=quality_score,
            quality_label=self._quality_label(quality_score),
            confidence=0.62,
            reasoning=(
                "Rule-based MVP analysis. Replace this with an LLM analyzer once "
                "the mailbox and model credentials are ready."
            ),
            raw={"analyzer": "rule_based"},
        )

    def _category(self, subject: str, sender: str, body: str) -> str:
        if _contains(
            subject,
            [
                "internship",
                "job",
                "jobs",
                "career",
                "position",
                "recruiter",
                "hiring",
                "vacancy",
                "apply now",
            ],
        ) or _contains(
            body,
            ["we are hiring", "job opening", "job alert", "apply for this role"],
        ):
            return "job_opportunity"
        if _contains(
            subject,
            ["scholarship", "research", "conference", "call for papers"],
        ) or _contains(body, ["call for papers", "research opportunity"]):
            return "academic_opportunity"
        if _contains(subject, ["meeting", "calendar", "confirm", "rsvp"]):
            return "meeting"
        if _contains(
            subject,
            [
                "verify",
                "verification",
                "security",
                "password",
                "suspicious",
                "sign-in",
                "login",
            ],
        ):
            return "account_or_security"
        receipt_terms = [
            "receipt",
            "order",
            "invoice",
            "purchase confirmation",
            "recibo",
            "encomenda",
            "收据",
            "订单",
        ]
        if _contains(subject, receipt_terms) or _contains(sender, receipt_terms):
            return "receipt_or_transaction"
        promotion_terms = [
            "sale",
            "discount",
            "newsletter",
            "promo",
            "promotion",
            "offer",
            "deal",
            "% off",
            "last chance",
            "flash",
            "book now",
            "save now",
            "desconto",
            "oferta",
            "poupança",
            "últimos dias",
        ]
        if _contains(subject, promotion_terms) or _contains(body, promotion_terms):
            return "promotion"
        return "general"

    def _priority(self, text: str, category: str, has_attachments: bool) -> int:
        if category in {"promotion", "receipt_or_transaction"}:
            return 2
        if _contains(text, ["urgent", "today", "tomorrow", "final reminder", "interview"]):
            return 5
        if category in {"job_opportunity", "academic_opportunity"}:
            return 4 if _contains(text, ["deadline", "apply", "application"]) else 3
        if category in {"meeting", "account_or_security"}:
            return 4
        if has_attachments and _contains(text, ["review", "sign", "submit"]):
            return 4
        return 3

    def _needs_reply(self, text: str) -> bool:
        return _contains(
            text,
            [
                "please reply",
                "reply with",
                "respond",
                "confirm",
                "let me know",
                "can you",
                "could you",
                "rsvp",
            ],
        )

    def _deadline(self, text: str) -> str | None:
        patterns = [
            r"\bdeadline(?: is|:)? ([^.,;]{2,60})",
            r"\bdue(?: by| on|:)? ([^.,;]{2,60})",
            r"\bapply by ([^.,;]{2,60})",
            r"\bcloses?(?: on| at)? ([^.,;]{2,60})",
            r"\bby (today|tomorrow|midnight|end of day|end of week)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        if "tomorrow" in text:
            return "tomorrow"
        if "today" in text:
            return "today"
        return None

    def _opportunity_score(self, text: str, category: str) -> int:
        score = 0
        if category == "job_opportunity":
            score = 7
        elif category == "academic_opportunity":
            score = 6
        elif category == "promotion":
            score = 2
        elif category == "receipt_or_transaction":
            score = 1
        else:
            score = 3

        if _contains(text, ["data", "ai", "analysis", "research"]):
            score += 1
        if _contains(text, ["deadline", "apply", "application"]):
            score += 1
        return min(score, 10)

    def _quality_score(self, priority: int, opportunity_score: int, category: str) -> int:
        if category in {"promotion", "receipt_or_transaction"}:
            return 2 if priority <= 2 else 4
        score = max(priority * 2, opportunity_score)
        if category in {"job_opportunity", "academic_opportunity", "meeting"}:
            score += 1
        return min(score, 10)

    def _quality_label(self, quality_score: int) -> str:
        if quality_score >= 7:
            return "high"
        if quality_score >= 4:
            return "medium"
        return "low"

    def _summary(self, message: EmailMessage, category: str) -> str:
        if category == "promotion":
            return f"Promotional email: {message.subject}"
        if category == "receipt_or_transaction":
            return f"Receipt or order update: {message.subject}"

        visible_text = _visible_text(message.body_text)
        first_sentence = re.split(r"(?<=[.!?])\s+", visible_text)[0]
        if len(first_sentence) > 240:
            first_sentence = first_sentence[:237].rstrip() + "..."
        return first_sentence or message.subject

    def _key_points(
        self, message: EmailMessage, category: str, deadline: str | None
    ) -> list[str]:
        points = [f"Category: {category}"]
        if deadline:
            points.append(f"Deadline: {deadline}")
        if message.attachments:
            points.append(f"Attachments: {len(message.attachments)}")
        return points

    def _action_items(
        self,
        text: str,
        category: str,
        needs_reply: bool,
        deadline: str | None,
    ) -> list[str]:
        items: list[str] = []
        if needs_reply:
            items.append("Draft and send a reply")
        if category == "account_or_security":
            if _contains(text, ["verify", "verification"]):
                items.append("Complete the account verification")
            else:
                items.append("Review the account or security notice")
        if category in {"job_opportunity", "academic_opportunity"}:
            items.append("Review the opportunity details")
        if _contains(text, ["cv", "resume"]):
            items.append("Prepare or update CV")
        if deadline and category not in {"promotion", "receipt_or_transaction"}:
            items.append(f"Plan before deadline: {deadline}")
        return items or ["No immediate action required"]


def _contains(text: str, keywords: list[str]) -> bool:
    for keyword in keywords:
        normalized_keyword = keyword.lower()
        if not normalized_keyword.isascii():
            if normalized_keyword in text:
                return True
            continue
        left_boundary = r"(?<![a-z0-9])" if normalized_keyword[0].isalnum() else ""
        right_boundary = r"(?![a-z0-9])" if normalized_keyword[-1].isalnum() else ""
        pattern = f"{left_boundary}{re.escape(normalized_keyword)}{right_boundary}"
        if re.search(pattern, text):
            return True
    return False


def _normalize_for_matching(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"https?://\S+|www\.\S+", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]", "", value)
    return re.sub(r"\s+", " ", value).strip().lower()


def _visible_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"https?://\S+|www\.\S+", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]", "", value)

    lines: list[str] = []
    for raw_line in value.splitlines():
        line = raw_line.strip(" \t|*-#")
        if not line or not any(character.isalnum() for character in line):
            continue
        if _contains(
            line.lower(),
            ["unsubscribe", "view this email in your browser", "manage preferences"],
        ):
            continue
        lines.append(line)

    return re.sub(r"\s+", " ", " ".join(lines[:4])).strip()
