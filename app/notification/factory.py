from app.config import Settings
from app.notification.console import ConsoleNotifier
from app.notification.whatsapp import WhatsAppNotifier


def build_notifier(settings: Settings):
    provider = settings.notification_provider.lower()
    if provider in {"console", "local"}:
        return ConsoleNotifier()
    if provider in {"whatsapp", "twilio"}:
        return WhatsAppNotifier(settings)
    raise ValueError(f"Unsupported NOTIFICATION_PROVIDER: {settings.notification_provider}")
