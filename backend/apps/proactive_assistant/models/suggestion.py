from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.common.models import UUIDTimestampedModel
from apps.proactive_assistant.enums import (
    DeliveryMethod,
    HistoryEvent,
    SuggestedAction,
    SuggestionStatus,
    SuggestionType,
)


class AssistantSuggestion(UUIDTimestampedModel):
    """A deduplicated recommendation produced by the decision engine."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistant_suggestions",
    )
    email = models.ForeignKey(
        "emails.Email",
        on_delete=models.SET_NULL,
        related_name="assistant_suggestions",
        null=True,
        blank=True,
    )
    suggestion_type = models.CharField(
        max_length=32,
        choices=SuggestionType.choices,
        db_index=True,
    )
    recommended_action = models.CharField(
        max_length=32,
        choices=SuggestedAction.choices,
        default=SuggestedAction.NONE,
    )
    status = models.CharField(
        max_length=16,
        choices=SuggestionStatus.choices,
        default=SuggestionStatus.PENDING,
        db_index=True,
    )
    delivery_method = models.CharField(
        max_length=16,
        choices=DeliveryMethod.choices,
        default=DeliveryMethod.IN_APP,
    )
    interruption_priority = models.PositiveSmallIntegerField(
        validators=(MinValueValidator(0), MaxValueValidator(100)),
        db_index=True,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    reason = models.TextField()
    action_payload = models.JSONField(default=dict, blank=True)
    deduplication_key = models.CharField(max_length=64)
    semantic_key = models.CharField(max_length=255, db_index=True)
    scheduled_for = models.DateTimeField(null=True, blank=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    acted_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=32, default="decision_engine")
    model_name = models.CharField(max_length=100, blank=True)

    class Meta(UUIDTimestampedModel.Meta):
        db_table = "assistant_suggestions"
        ordering = ("-interruption_priority", "-created_at")
        constraints = (
            models.UniqueConstraint(
                fields=("user", "deduplication_key"),
                name="uniq_user_suggestion_dedupe",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    interruption_priority__gte=0,
                    interruption_priority__lte=100,
                ),
                name="suggest_priority_0_100",
            ),
        )
        indexes = (
            models.Index(
                fields=("user", "status", "-interruption_priority"),
                name="suggest_user_status_prio_idx",
            ),
            models.Index(
                fields=("user", "scheduled_for"),
                name="suggest_user_schedule_idx",
            ),
        )

    def __str__(self) -> str:
        return self.title


class SuggestionHistory(UUIDTimestampedModel):
    """Immutable audit trail of a suggestion's lifecycle and delivery."""

    suggestion = models.ForeignKey(
        AssistantSuggestion,
        on_delete=models.CASCADE,
        related_name="history",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistant_suggestion_history",
    )
    event = models.CharField(max_length=16, choices=HistoryEvent.choices, db_index=True)
    channel = models.CharField(
        max_length=16,
        choices=DeliveryMethod.choices,
        default=DeliveryMethod.NONE,
    )
    details = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta(UUIDTimestampedModel.Meta):
        db_table = "suggestion_history"
        ordering = ("-occurred_at",)
        indexes = (
            models.Index(
                fields=("user", "-occurred_at"),
                name="suggest_hist_user_time_idx",
            ),
        )

    def __str__(self) -> str:
        return f"{self.event}: {self.suggestion_id}"
