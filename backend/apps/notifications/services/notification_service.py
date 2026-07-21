from __future__ import annotations

from django.db import transaction
import logging
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications.models import Notification, NotificationStatus, PushDevice

logger = logging.getLogger(__name__)


class NotificationService:
    """Owns user-scoped notification state and device registration."""

    @staticmethod
    def mark_read(user: User, notification_uuid: str) -> Notification | None:
        notification = Notification.objects.filter(user=user, uuid=notification_uuid).first()
        if notification is None:
            return None
        if notification.read_at is None:
            notification.status = NotificationStatus.READ
            notification.read_at = timezone.now()
            notification.save(update_fields=("status", "read_at", "updated_at"))
        return notification

    @staticmethod
    def mark_all_read(user: User) -> int:
        now = timezone.now()
        return Notification.objects.filter(user=user, read_at__isnull=True).update(
            status=NotificationStatus.READ,
            read_at=now,
            updated_at=now,
        )

    @staticmethod
    @transaction.atomic
    def register_device(
        *,
        user: User,
        token: str,
        platform: str,
        provider: str,
    ) -> PushDevice:
        device, created = PushDevice.objects.update_or_create(
            token=token,
            defaults={
                "user": user,
                "platform": platform,
                "provider": provider,
                "is_active": True,
                "last_registered_at": timezone.now(),
            },
        )
        logger.info("Device registered" if created else "Token updated", extra={"user_uuid": str(user.uuid), "platform": platform, "provider": provider})
        return device
