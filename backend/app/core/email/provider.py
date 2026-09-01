from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import html
from loguru import logger

class EmailProvider(ABC):
    @abstractmethod
    def send_email(self, to_email: str, subject: str, body_text: str, body_html: Optional[str] = None) -> bool:
        pass

class MockEmailProvider(EmailProvider):
    def __init__(self):
        self.sent_emails = []

    def send_email(self, to_email: str, subject: str, body_text: str, body_html: Optional[str] = None) -> bool:
        # Sanitize HTML / escape
        safe_subject = html.escape(subject)
        safe_text = html.escape(body_text)
        self.sent_emails.append({
            "to": to_email,
            "subject": safe_subject,
            "body": safe_text,
            "html": body_html
        })
        logger.info(f"[MockEmail] Dispatched email to {to_email}: {safe_subject}")
        return True

_provider_instance: Optional[EmailProvider] = None

def get_email_provider() -> EmailProvider:
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = MockEmailProvider()
    return _provider_instance

def set_email_provider(provider: EmailProvider):
    global _provider_instance
    _provider_instance = provider
