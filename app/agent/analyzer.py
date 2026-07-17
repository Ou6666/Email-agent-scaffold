from __future__ import annotations

import re

from app.agent.schemas import EmailAnalysis, EmailMessage


class RuleBasedEmailAnalyzer:
    def analyze(self, message: EmailMessage) -> EmailAnalysis:
        text = f"{message.subject}\n{message.body_text}".lower()
        category = self._category(text)
        priority = self._priority(text, category, bool(message.attachments))
        needs_reply = self._needs_reply(text)
        needs_follow_up = needs_reply or category in {
            "job_opportunity",
            "academic_opportunity",
            "meeting",
        }
        deadline = self._deadline(text)
        opportunity_score = self._opportunity_score(text, category)
        quality_score = self._quality_score(priority, opportunity_score, category)

        return EmailAnalysis(
            priority=priority,
            category=category,
            needs_reply=needs_reply,
            needs_follow_up=needs_follow_up,
            summary=self._summary(message),
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

    def _category(self, text: str) -> str:
        if _contains(text, ["internship", "job", "career", "position", "recruiter"]):
            return "job_opportunity"
        if _contains(text, ["scholarship", "research", "conference", "call for papers"]):
            return "academic_opportunity"
        if _contains(text, ["meeting", "calendar", "confirm", "rsvp"]):
            return "meeting"
        if _contains(text, ["invoice", "payment", "security", "password"]):
            return "account_or_security"
        if _contains(text, ["sale", "discount", "newsletter", "promo", "offer"]):
            return "promotion"
        return "general"

    def _priority(self, text: str, category: str, has_attachments: bool) -> int:
        if _contains(text, ["urgent", "today", "tomorrow", "final reminder", "interview"]):
            return 5
        if category in {"job_opportunity", "academic_opportunity"}:
            return 4 if _contains(text, ["deadline", "apply", "application"]) else 3
        if category in {"meeting", "account_or_security"}:
            return 4
        if has_attachments and _contains(text, ["review", "sign", "submit"]):
            return 4
        if category == "promotion":
            return 2
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
            r"deadline is ([^.,\n]+)",
            r"due ([^.,\n]+)",
            r"by ([^.,\n]+)",
            r"closes? ([^.,\n]+)",
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
        else:
            score = 3

        if _contains(text, ["data", "ai", "analysis", "research"]):
            score += 1
        if _contains(text, ["deadline", "apply", "application"]):
            score += 1
        return min(score, 10)

    def _quality_score(self, priority: int, opportunity_score: int, category: str) -> int:
        if category == "promotion":
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

    def _summary(self, message: EmailMessage) -> str:
        first_sentence = re.split(r"(?<=[.!?])\s+", message.body_text.strip())[0]
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
        if category in {"job_opportunity", "academic_opportunity"}:
            items.append("Review the opportunity details")
        if _contains(text, ["cv", "resume"]):
            items.append("Prepare or update CV")
        if deadline:
            items.append(f"Plan before deadline: {deadline}")
        return items or ["No immediate action required"]


def _contains(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)
