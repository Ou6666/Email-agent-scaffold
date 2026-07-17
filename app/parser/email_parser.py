import re

from app.agent.schemas import EmailMessage


MAX_BODY_CHARS = 12_000


class EmailParser:
    def normalize(self, message: EmailMessage) -> EmailMessage:
        clean_body = self._clean_body(message.body_text)
        return message.model_copy(update={"body_text": clean_body})

    def _clean_body(self, body: str) -> str:
        body = body.replace("\r\n", "\n").replace("\r", "\n")
        body = re.sub(r"\n{3,}", "\n\n", body)
        body = re.sub(r"[ \t]+", " ", body)
        body = self._trim_quoted_replies(body)
        return body.strip()[:MAX_BODY_CHARS]

    def _trim_quoted_replies(self, body: str) -> str:
        markers = [
            "\nOn ",
            "\nFrom:",
            "\nSent:",
            "\n-----Original Message-----",
            "\n________________________________",
        ]
        cut_positions = [body.find(marker) for marker in markers if body.find(marker) > 0]
        if not cut_positions:
            return body
        return body[: min(cut_positions)]

