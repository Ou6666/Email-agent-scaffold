from dataclasses import dataclass
from pathlib import Path
import os
import json

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _default_sqlite_url() -> str:
    db_path = BASE_DIR / "data" / "emails.db"
    return f"sqlite:///{db_path.as_posix()}"


def _default_outlook_token_cache_path() -> str:
    return str(BASE_DIR / ".outlook_token_cache.json")


def _default_gmail_credentials_path() -> str:
    return str(BASE_DIR / "credentials.json")


def _default_gmail_token_path() -> str:
    return str(BASE_DIR / "token.json")


def _parse_list(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default
    return [scope.strip() for scope in value.replace(",", " ").split() if scope.strip()]


def _parse_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _parse_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "email-agent"
    environment: str = "local"
    email_provider: str = "gmail"
    analyzer_provider: str = "rule"
    database_url: str = _default_sqlite_url()
    notification_provider: str = "console"
    fetch_limit: int = 10
    minimum_notify_priority: int = 4
    scheduler_interval_minutes: int = 60
    openai_model: str = "gpt-4.1-mini"
    llm_temperature: float = 0.0
    llm_enable_fallback: bool = True
    gmail_user_email: str | None = None
    gmail_credentials_path: str = _default_gmail_credentials_path()
    gmail_token_path: str = _default_gmail_token_path()
    gmail_scopes: list[str] | None = None
    outlook_client_id: str | None = None
    outlook_tenant_id: str = "organizations"
    outlook_user_email: str | None = None
    outlook_token_cache_path: str = _default_outlook_token_cache_path()
    outlook_scopes: list[str] | None = None
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_whatsapp_from: str | None = None
    whatsapp_to: str | None = None
    twilio_content_sid: str | None = None
    twilio_content_variables: str | None = None

    @property
    def outlook_authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.outlook_tenant_id}"


def get_settings() -> Settings:
    return Settings(
        environment=os.getenv("ENVIRONMENT", "local"),
        email_provider=os.getenv("EMAIL_PROVIDER", "gmail"),
        analyzer_provider=os.getenv("ANALYZER_PROVIDER", "rule"),
        database_url=os.getenv("DATABASE_URL", _default_sqlite_url()),
        notification_provider=os.getenv("NOTIFICATION_PROVIDER", "console"),
        fetch_limit=_parse_int(os.getenv("FETCH_LIMIT"), 10),
        minimum_notify_priority=_parse_int(os.getenv("MINIMUM_NOTIFY_PRIORITY"), 4),
        scheduler_interval_minutes=_parse_int(
            os.getenv("SCHEDULER_INTERVAL_MINUTES"), 60
        ),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        llm_temperature=_parse_float(os.getenv("LLM_TEMPERATURE"), 0.0),
        llm_enable_fallback=_parse_bool(os.getenv("LLM_ENABLE_FALLBACK"), True),
        gmail_user_email=os.getenv("GMAIL_USER_EMAIL") or None,
        gmail_credentials_path=os.getenv(
            "GMAIL_CREDENTIALS_PATH", _default_gmail_credentials_path()
        ),
        gmail_token_path=os.getenv("GMAIL_TOKEN_PATH", _default_gmail_token_path()),
        gmail_scopes=_parse_list(
            os.getenv("GMAIL_SCOPES"),
            ["https://www.googleapis.com/auth/gmail.readonly"],
        ),
        outlook_client_id=os.getenv("OUTLOOK_CLIENT_ID") or None,
        outlook_tenant_id=os.getenv("OUTLOOK_TENANT_ID", "organizations"),
        outlook_user_email=os.getenv("OUTLOOK_USER_EMAIL") or None,
        outlook_token_cache_path=os.getenv(
            "OUTLOOK_TOKEN_CACHE_PATH", _default_outlook_token_cache_path()
        ),
        outlook_scopes=_parse_list(
            os.getenv("OUTLOOK_SCOPES"),
            ["User.Read", "Mail.Read", "offline_access"],
        ),
        twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID") or None,
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN") or None,
        twilio_whatsapp_from=os.getenv("TWILIO_WHATSAPP_FROM") or None,
        whatsapp_to=os.getenv("WHATSAPP_TO") or None,
        twilio_content_sid=os.getenv("TWILIO_CONTENT_SID") or None,
        twilio_content_variables=os.getenv("TWILIO_CONTENT_VARIABLES")
        or json.dumps({"1": "Email Agent test", "2": "environment check"}),
    )
