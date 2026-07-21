from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import UUIDTimestampedModel


class AISummary(UUIDTimestampedModel):
    """Persisted structured analysis generated for one email."""

    email = models.OneToOneField(
        "emails.Email",
        on_delete=models.CASCADE,
        related_name="ai_summary",
    )
    category = models.ForeignKey(
        "intelligence.AICategory",
        on_delete=models.PROTECT,
        related_name="summaries",
    )
    summary = models.TextField()
    importance_score = models.PositiveSmallIntegerField(
        validators=(MinValueValidator(0), MaxValueValidator(100)),
        db_index=True,
    )
    sender_priority = models.PositiveSmallIntegerField(
        default=50,
        validators=(MinValueValidator(0), MaxValueValidator(100)),
        help_text="Learned priority of the sender for this user.",
    )
    action_required = models.BooleanField(default=False, db_index=True)
    deadline = models.DateTimeField(null=True, blank=True, db_index=True)
    meeting_date = models.DateTimeField(null=True, blank=True)
    phishing_score = models.PositiveSmallIntegerField(
        validators=(MinValueValidator(0), MaxValueValidator(100)),
    )
    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        validators=(MinValueValidator(0), MaxValueValidator(1)),
    )
    reasoning = models.TextField()
    model_name = models.CharField(max_length=100)
    prompt_version = models.CharField(max_length=32)
    input_tokens = models.PositiveIntegerField(null=True, blank=True)
    output_tokens = models.PositiveIntegerField(null=True, blank=True)
    processed_at = models.DateTimeField()

    class Meta(UUIDTimestampedModel.Meta):
        db_table = "ai_summaries"
        ordering = ("-processed_at",)
        indexes = (
            models.Index(
                fields=("importance_score", "-processed_at"),
                name="ai_importance_idx",
            ),
            models.Index(
                fields=("action_required", "deadline"),
                name="ai_action_deadline_idx",
            ),
        )
        constraints = (
            models.CheckConstraint(
                condition=models.Q(importance_score__gte=0, importance_score__lte=100),
                name="ai_importance_0_100",
            ),
            models.CheckConstraint(
                condition=models.Q(phishing_score__gte=0, phishing_score__lte=100),
                name="ai_phishing_0_100",
            ),
            models.CheckConstraint(
                condition=models.Q(sender_priority__gte=0, sender_priority__lte=100),
                name="ai_sender_priority_0_100",
            ),
            models.CheckConstraint(
                condition=models.Q(confidence__gte=0, confidence__lte=1),
                name="ai_confidence_0_1",
            ),
        )

    def __str__(self) -> str:
        return f"AI analysis for {self.email_id}"
