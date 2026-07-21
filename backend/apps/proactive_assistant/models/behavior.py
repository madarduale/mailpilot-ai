from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import UUIDTimestampedModel
from apps.proactive_assistant.enums import BehaviorType


class UserBehavior(UUIDTimestampedModel):
    """Append-only behavioral evidence used to learn assistant preferences."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistant_behaviors",
    )
    email = models.ForeignKey(
        "emails.Email",
        on_delete=models.SET_NULL,
        related_name="user_behaviors",
        null=True,
        blank=True,
    )
    behavior_type = models.CharField(
        max_length=32,
        choices=BehaviorType.choices,
        db_index=True,
    )
    target = models.CharField(max_length=255, blank=True, db_index=True)
    context = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta(UUIDTimestampedModel.Meta):
        db_table = "user_behaviors"
        ordering = ("-occurred_at",)
        indexes = (
            models.Index(
                fields=("user", "behavior_type", "-occurred_at"),
                name="behavior_user_type_time_idx",
            ),
        )

    def __str__(self) -> str:
        return f"{self.user_id}: {self.behavior_type}"
