from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.common.models import UUIDTimestampedModel


class AssistantMemory(UUIDTimestampedModel):
    """Durable, explainable preference learned for one user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistant_memories",
    )
    namespace = models.CharField(max_length=64, db_index=True)
    key = models.CharField(max_length=191)
    value = models.JSONField(default=dict)
    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
        validators=(MinValueValidator(0), MaxValueValidator(1)),
    )
    evidence_count = models.PositiveIntegerField(default=1)
    source = models.CharField(max_length=32, default="observed_behavior")
    is_active = models.BooleanField(default=True, db_index=True)
    last_reinforced_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta(UUIDTimestampedModel.Meta):
        db_table = "assistant_memories"
        constraints = (
            models.UniqueConstraint(
                fields=("user", "namespace", "key"),
                name="uniq_user_memory_key",
            ),
            models.CheckConstraint(
                condition=models.Q(confidence__gte=0, confidence__lte=1),
                name="memory_confidence_0_1",
            ),
        )
        indexes = (
            models.Index(
                fields=("user", "namespace", "is_active"),
                name="memory_user_namespace_idx",
            ),
        )

    def __str__(self) -> str:
        return f"{self.namespace}.{self.key}"
