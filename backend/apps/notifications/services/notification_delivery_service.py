from __future__ import annotations

import logging

from django.utils import timezone

from apps.emails.models import Email
from apps.notifications.integrations import ExpoPushGateway
from apps.notifications.models import Notification, NotificationStatus, PushDevice

logger = logging.getLogger(__name__)


class NotificationDeliveryService:
    """Delivers one notification to active devices and persists provider state."""

    def __init__(self, gateway: ExpoPushGateway | None = None) -> None:
        self.gateway = gateway or ExpoPushGateway()

    def deliver(self, notification: Notification) -> Notification:
        tokens = list(
            PushDevice.objects.filter(
                user=notification.user,
                is_active=True,
                provider="expo",
            ).values_list("token", flat=True)[:100]
        )
        if not tokens:
            logger.info(
                "Notification skipped",
                extra={"notification_uuid": str(notification.uuid), "reason": "no_active_devices"},
            )
            return notification
        tickets = self.gateway.send(
            [
                {
                    "to": token,
                    "sound": "default",
                    "priority": "high",
                    "channelId": "important-email",
                    "badge": Email.objects.filter(
                        account__user=notification.user, is_read=False
                    ).count(),
                    "title": notification.title,
                    "body": notification.body,
                    "data": notification.data,
                }
                for token in tokens
            ]
        )
        errors = [ticket for ticket in tickets if ticket.get("status") == "error"]
        if errors:
            notification.status = NotificationStatus.FAILED
            notification.failure_reason = "; ".join(
                str(ticket.get("message", "Expo rejected the notification.")) for ticket in errors
            )[:2000]
            logger.warning(
                "Notification failed",
                extra={
                    "notification_uuid": str(notification.uuid),
                    "reason": notification.failure_reason,
                },
            )
        else:
            notification.status = NotificationStatus.SENT
            notification.sent_at = timezone.now()
            ticket_ids = [str(ticket["id"]) for ticket in tickets if ticket.get("id")]
            notification.provider_message_id = ",".join(ticket_ids)[:255]
            logger.info(
                "Notification sent",
                extra={"notification_uuid": str(notification.uuid), "device_count": len(tokens)},
            )
        notification.save(
            update_fields=(
                "status",
                "failure_reason",
                "sent_at",
                "provider_message_id",
                "updated_at",
            )
        )
        return notification
