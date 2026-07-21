from __future__ import annotations

from typing import Any

from celery import shared_task
from django.core.cache import cache
from openai import OpenAIError

from apps.emails.models import Email
from apps.intelligence.models import AISummary
from apps.intelligence.services import AIEmailAnalysisService


@shared_task(
    bind=True,
    autoretry_for=(OpenAIError, ValueError, ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def analyze_email(
    self: Any,
    email_uuid: str,
    notify_user: bool = False,
) -> str | None:
    if AISummary.objects.filter(email_id=email_uuid).exists():
        return email_uuid
    lock_key = f"mailpilot:email-analysis:{email_uuid}"
    if not cache.add(lock_key, "locked", timeout=300):
        return email_uuid
    try:
        try:
            email = Email.objects.select_related("account__user").get(uuid=email_uuid)
        except Email.DoesNotExist:
            return None
        if AISummary.objects.filter(email=email).exists():
            return str(email.uuid)
        AIEmailAnalysisService().analyze(email, notify_user=notify_user)
        return str(email.uuid)
    finally:
        cache.delete(lock_key)


__all__ = ["analyze_email"]
