from datetime import datetime, timezone

from app.agent.analyzer import RuleBasedEmailAnalyzer
from app.agent.schemas import EmailMessage


def _message(subject: str, body: str, sender: str = "sender@example.com") -> EmailMessage:
    return EmailMessage(
        email_id="message-1",
        sender=sender,
        subject=subject,
        received_at=datetime.now(timezone.utc),
        body_text=body,
    )


def test_promotion_is_not_escalated_by_footer_noise() -> None:
    message = _message(
        "Friday Flash: up to 20% off",
        "Today only. Manage preferences by clicking "
        "https://example.com/jobs/data/ai/cv.",
    )

    analysis = RuleBasedEmailAnalyzer().analyze(message)

    assert analysis.category == "promotion"
    assert analysis.priority == 2
    assert analysis.quality_label == "low"
    assert analysis.deadline == "today"
    assert analysis.action_items == ["No immediate action required"]


def test_percentage_discount_is_recognized_as_promotion() -> None:
    message = _message("Save 20% off", "A limited rental discount is available.")

    analysis = RuleBasedEmailAnalyzer().analyze(message)

    assert analysis.category == "promotion"
    assert analysis.priority == 2


def test_tracking_url_does_not_create_job_opportunity() -> None:
    message = _message(
        "Ouhao, não estávamos à espera disto",
        "Book now and save on your next rental. "
        "https://example.com/job/data/ai/cv",
        sender="SIXT <offers@example.com>",
    )

    analysis = RuleBasedEmailAnalyzer().analyze(message)

    assert analysis.category == "promotion"
    assert analysis.priority == 2
    assert analysis.opportunity_score == 2
    assert "Prepare or update CV" not in analysis.action_items


def test_job_alert_remains_high_value() -> None:
    message = _message(
        "Content Innovation Specialist and 8 more jobs. Apply Now.",
        "Several roles in Portugal are open for applications.",
        sender="Glassdoor Jobs <noreply@glassdoor.com>",
    )

    analysis = RuleBasedEmailAnalyzer().analyze(message)

    assert analysis.category == "job_opportunity"
    assert analysis.priority == 4
    assert analysis.needs_follow_up is True
    assert analysis.opportunity_score >= 8
    assert analysis.quality_label == "high"


def test_account_verification_gets_relevant_action() -> None:
    message = _message(
        "Verify your Email",
        "Verify your email address to continue using your account.",
    )

    analysis = RuleBasedEmailAnalyzer().analyze(message)

    assert analysis.category == "account_or_security"
    assert analysis.priority == 4
    assert analysis.needs_follow_up is True
    assert analysis.action_items == ["Complete the account verification"]


def test_chinese_receipt_is_transactional() -> None:
    message = _message(
        "您星期四下午的 Uber Eats 优食订单",
        "感谢您的订购。这是您的收据。总计 €10.65。",
        sender="优步收据 <noreply@uber.com>",
    )

    analysis = RuleBasedEmailAnalyzer().analyze(message)

    assert analysis.category == "receipt_or_transaction"
    assert analysis.priority == 2
    assert analysis.quality_label == "low"
