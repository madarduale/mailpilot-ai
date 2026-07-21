from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.utils import timezone

from apps.emails.models import Email
from apps.notifications.models import Notification, NotificationChannel
from apps.notifications.tasks import send_push_notification
from apps.proactive_assistant.enums import DeliveryMethod, HistoryEvent, SuggestionStatus
from apps.proactive_assistant.models import AssistantSuggestion, SuggestionHistory
from apps.proactive_assistant.services import ProactiveAssistantService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def evaluate_analyzed_email(self: Any, email_uuid: str) -> str | None:
    """Evaluate one committed AI analysis and queue its appropriate delivery."""

    try:
        email = Email.objects.select_related(
            "account__user",
            "ai_summary__category",
        ).get(uuid=email_uuid)
    except Email.DoesNotExist:
        logger.warning("Cannot evaluate missing email", extra={"email_uuid": email_uuid})
        return None

    _, suggestion = ProactiveAssistantService().evaluate_email(email)
    if suggestion is None:
        return None
    if suggestion.delivery_method != DeliveryMethod.IN_APP:
        deliver_suggestion.delay(str(suggestion.uuid))
    return str(suggestion.uuid)


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def deliver_suggestion(self: Any, suggestion_uuid: str) -> str | None:
    """Persist a delivery request for the configured notification provider worker."""

    try:
        suggestion = AssistantSuggestion.objects.select_related("email").get(
            uuid=suggestion_uuid,
            status=SuggestionStatus.PENDING,
        )
    except AssistantSuggestion.DoesNotExist:
        return None

    channel = (
        NotificationChannel.PUSH
        if suggestion.delivery_method == DeliveryMethod.PUSH
        else NotificationChannel.IN_APP
    )
    notification = Notification.objects.create(
        user=suggestion.user,
        email=suggestion.email,
        channel=channel,
        notification_type="proactive_assistant",
        title=suggestion.title,
        body=suggestion.message,
        data={
            "suggestion_uuid": str(suggestion.uuid),
            "suggestion_type": suggestion.suggestion_type,
            "recommended_action": suggestion.recommended_action,
            "delivery_method": suggestion.delivery_method,
            "reason": suggestion.reason,
        },
        importance_score=suggestion.interruption_priority,
    )
    SuggestionHistory.objects.create(
        suggestion=suggestion,
        user=suggestion.user,
        event=HistoryEvent.PRESENTED,
        channel=suggestion.delivery_method,
        details={"notification_uuid": str(notification.uuid)},
    )
    suggestion.status = SuggestionStatus.SHOWN
    suggestion.save(update_fields=("status", "updated_at"))
    if channel == NotificationChannel.PUSH:
        send_push_notification.delay(str(notification.uuid))
    return str(notification.uuid)


@shared_task
def expire_stale_suggestions() -> int:
    """Expire pending recommendations whose underlying opportunity has passed."""

    now = timezone.now()
    stale = AssistantSuggestion.objects.filter(
        status__in=(SuggestionStatus.PENDING, SuggestionStatus.SHOWN),
        expires_at__lte=now,
    )
    identities = list(stale.values_list("uuid", "user_id"))
    updated = stale.update(status=SuggestionStatus.EXPIRED, updated_at=now)
    SuggestionHistory.objects.bulk_create(
        [
            SuggestionHistory(
                suggestion_id=suggestion_uuid,
                user_id=user_uuid,
                event=HistoryEvent.EXPIRED,
                details={"expired_at": now.isoformat()},
            )
            for suggestion_uuid, user_uuid in identities
        ]
    )
    return updated
