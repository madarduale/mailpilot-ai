from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import UUIDTimestampedModel


class NotificationChannel(models.TextChoices):
    PUSH = "push", "Push"
    IN_APP = "in_app", "In-app"


class NotificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    FAILED = "failed", "Failed"
    READ = "read", "Read"


class Notification(UUIDTimestampedModel):
    """A persisted notification and provider delivery state."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    email = models.ForeignKey(
        "emails.Email",
        on_delete=models.SET_NULL,
        related_name="notifications",
        null=True,
        blank=True,
    )
    reminder = models.ForeignKey(
        "reminders.Reminder",
        on_delete=models.SET_NULL,
        related_name="notifications",
        null=True,
        blank=True,
    )
    channel = models.CharField(
        max_length=16,
        choices=NotificationChannel.choices,
        default=NotificationChannel.PUSH,
    )
    status = models.CharField(
        max_length=16,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        db_index=True,
    )
    notification_type = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=255)
    body = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    importance_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=(MinValueValidator(0), MaxValueValidator(100)),
    )
    provider_message_id = models.CharField(max_length=255, blank=True)
    failure_reason = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta(UUIDTimestampedModel.Meta):
        db_table = "notifications"
        indexes = (
            models.Index(fields=("user", "status", "-created_at"), name="notif_user_status_idx"),
        )
        constraints = (
            models.CheckConstraint(
                condition=(
                    models.Q(importance_score__isnull=True)
                    | models.Q(importance_score__gte=0, importance_score__lte=100)
                ),
                name="notif_importance_0_100",
            ),
        )

    def __str__(self) -> str:
        return self.title
