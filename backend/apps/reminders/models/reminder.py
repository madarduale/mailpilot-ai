from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimestampedModel


class ReminderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    SNOOZED = "snoozed", "Snoozed"
    CANCELLED = "cancelled", "Cancelled"


class Reminder(UUIDTimestampedModel):
    """A user reminder optionally extracted from an email."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reminders",
    )
    email = models.ForeignKey(
        "emails.Email",
        on_delete=models.SET_NULL,
        related_name="reminders",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_at = models.DateTimeField(db_index=True)
    priority = models.PositiveSmallIntegerField(default=50)
    status = models.CharField(
        max_length=16,
        choices=ReminderStatus.choices,
        default=ReminderStatus.PENDING,
        db_index=True,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    lead_notification_sent = models.BooleanField(default=False, db_index=True)
    lead_notification_sent_at = models.DateTimeField(null=True, blank=True)
    notification_sent = models.BooleanField(default=False, db_index=True)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    snoozed_until = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=32, default="manual")

    class Meta(UUIDTimestampedModel.Meta):
        db_table = "reminders"
        ordering = ("due_at",)
        indexes = (
            models.Index(fields=("user", "status", "due_at"), name="rem_user_due_idx"),
            models.Index(
                fields=("status", "notification_sent", "due_at"),
                name="rem_delivery_due_idx",
            ),
            models.Index(
                fields=("status", "lead_notification_sent", "due_at"),
                name="rem_delivery_lead_idx",
            ),
        )

    def __str__(self) -> str:
        return self.title
