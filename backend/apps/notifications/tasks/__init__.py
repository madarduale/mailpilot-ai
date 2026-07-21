from __future__ import annotations

from typing import Any
from urllib.error import URLError

from celery import shared_task

from apps.notifications.models import Notification
from apps.notifications.services import NotificationDeliveryService


@shared_task(
    bind=True,
    autoretry_for=(URLError, TimeoutError, ConnectionError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_push_notification(self: Any, notification_uuid: str) -> str | None:
    try:
        notification = Notification.objects.select_related("user").get(
            uuid=notification_uuid
        )
    except Notification.DoesNotExist:
        return None
    NotificationDeliveryService().deliver(notification)
    return str(notification.uuid)
