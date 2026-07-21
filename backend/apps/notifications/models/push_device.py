from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import UUIDTimestampedModel


class DevicePlatform(models.TextChoices):
    IOS = "ios", "iOS"
    ANDROID = "android", "Android"
    WEB = "web", "Web"


class PushDevice(UUIDTimestampedModel):
    """A rotatable Expo push token associated with the current device owner."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_devices",
    )
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=16, choices=DevicePlatform.choices)
    provider = models.CharField(max_length=16, default="expo")
    is_active = models.BooleanField(default=True, db_index=True)
    last_registered_at = models.DateTimeField(default=timezone.now)

    class Meta(UUIDTimestampedModel.Meta):
        db_table = "push_devices"
        indexes = (
            models.Index(fields=("user", "is_active"), name="push_device_user_active_idx"),
        )

    def __str__(self) -> str:
        return f"{self.platform}: {self.user_id}"
