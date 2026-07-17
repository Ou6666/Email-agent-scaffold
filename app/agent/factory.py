from typing import Protocol

from app.agent.analyzer import RuleBasedEmailAnalyzer
from app.agent.openai_analyzer import LLMAnalyzerUnavailable, OpenAIEmailAnalyzer
from app.agent.schemas import EmailAnalysis, EmailMessage
from app.config import Settings


class EmailAnalyzer(Protocol):
    def analyze(self, message: EmailMessage) -> EmailAnalysis:
        ...


class FallbackEmailAnalyzer:
    def __init__(self, primary: EmailAnalyzer, fallback: EmailAnalyzer) -> None:
        self.primary = primary
        self.fallback = fallback

    def analyze(self, message: EmailMessage) -> EmailAnalysis:
        try:
            return self.primary.analyze(message)
        except Exception as error:
            analysis = self.fallback.analyze(message)
            return analysis.model_copy(
                update={
                    "raw": {
                        **analysis.raw,
                        "fallback_reason": str(error),
                    }
                }
            )


def build_analyzer(settings: Settings) -> EmailAnalyzer:
    provider = settings.analyzer_provider.lower()
    if provider in {"rule", "rules", "rule_based"}:
        return RuleBasedEmailAnalyzer()

    if provider in {"llm", "openai"}:
        fallback = RuleBasedEmailAnalyzer()
        try:
            primary = OpenAIEmailAnalyzer(settings)
        except LLMAnalyzerUnavailable as error:
            if settings.llm_enable_fallback:
                print(f"LLM unavailable, using rule-based analyzer: {error}")
                return fallback
            raise

        if settings.llm_enable_fallback:
            return FallbackEmailAnalyzer(primary=primary, fallback=fallback)
        return primary

    raise ValueError(f"Unsupported ANALYZER_PROVIDER: {settings.analyzer_provider}")
