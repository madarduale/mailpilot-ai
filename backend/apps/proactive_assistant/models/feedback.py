from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import UUIDTimestampedModel
from apps.proactive_assistant.enums import FeedbackType
from apps.proactive_assistant.models.suggestion import AssistantSuggestion


class SuggestionFeedback(UUIDTimestampedModel):
    """Explicit user response used for suppression and future ranking."""

    suggestion = models.ForeignKey(
        AssistantSuggestion,
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistant_feedback",
    )
    feedback_type = models.CharField(
        max_length=16,
        choices=FeedbackType.choices,
        db_index=True,
    )
    comment = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta(UUIDTimestampedModel.Meta):
        db_table = "suggestion_feedback"
        ordering = ("-occurred_at",)
        indexes = (
            models.Index(
                fields=("user", "feedback_type", "-occurred_at"),
                name="feedback_user_type_time_idx",
            ),
        )

    def __str__(self) -> str:
        return f"{self.feedback_type}: {self.suggestion_id}"
