from __future__ import annotations

import json
import os

from openai import OpenAI
from pydantic import ValidationError

from app.agent.prompts import (
    EMAIL_ANALYSIS_SYSTEM_PROMPT,
    build_email_analysis_user_prompt,
)
from app.agent.schemas import EmailAnalysis, EmailMessage
from app.config import Settings, get_settings


class LLMAnalyzerUnavailable(RuntimeError):
    pass


class LLMAnalyzerError(RuntimeError):
    pass


class OpenAIEmailAnalyzer:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not os.getenv("OPENAI_API_KEY"):
            raise LLMAnalyzerUnavailable("OPENAI_API_KEY is not set.")
        self.client = OpenAI()

    def analyze(self, message: EmailMessage) -> EmailAnalysis:
        response = self.client.chat.completions.create(
            model=self.settings.openai_model,
            temperature=self.settings.llm_temperature,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": EMAIL_ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": build_email_analysis_user_prompt(message)},
            ],
        )

        content = response.choices[0].message.content
        if not content:
            raise LLMAnalyzerError("OpenAI returned an empty analysis response.")

        try:
            payload = json.loads(content)
            analysis = EmailAnalysis.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as error:
            raise LLMAnalyzerError(f"Invalid LLM analysis payload: {error}") from error

        return analysis.model_copy(
            update={
                "raw": {
                    **analysis.raw,
                    "analyzer": "openai",
                    "model": self.settings.openai_model,
                }
            }
        )

