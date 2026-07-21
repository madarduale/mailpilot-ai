from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import UUIDTimestampedModel


class DigestFrequency(models.TextChoices):
    NEVER = "never", "Never"
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"


class NotificationMode(models.TextChoices):
    IMPORTANT_ONLY = "important_only", "Important emails only"
    ALL_EMAILS = "all_emails", "All emails"


class UserPreference(UUIDTimestampedModel):
    """Per-user notification, locale, and voice assistant preferences."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preferences",
    )
    importance_threshold = models.PositiveSmallIntegerField(
        default=75,
        validators=(MinValueValidator(0), MaxValueValidator(100)),
    )
    push_notifications_enabled = models.BooleanField(default=True)
    notification_mode = models.CharField(max_length=24, choices=NotificationMode.choices, default=NotificationMode.IMPORTANT_ONLY)
    reminder_notifications_enabled = models.BooleanField(default=True)
    reminder_lead_time_minutes = models.PositiveSmallIntegerField(
        default=30,
        validators=(MinValueValidator(0), MaxValueValidator(1440)),
    )
    notify_categories = models.JSONField(default=list, blank=True)
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    locale = models.CharField(max_length=16, default="en")
    voice_language = models.CharField(max_length=16, default="en")
    tts_voice = models.CharField(max_length=64, default="alloy")
    digest_frequency = models.CharField(
        max_length=16,
        choices=DigestFrequency.choices,
        default=DigestFrequency.NEVER,
    )

    class Meta(UUIDTimestampedModel.Meta):
        db_table = "user_preferences"
        constraints = (
            models.CheckConstraint(
                condition=models.Q(
                    importance_threshold__gte=0,
                    importance_threshold__lte=100,
                ),
                name="pref_importance_0_100",
            ),
        )

    def __str__(self) -> str:
        return f"Preferences for {self.user_id}"
