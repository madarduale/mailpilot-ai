from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimestampedModel


class ConversationStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class VoiceConversation(UUIDTimestampedModel):
    """Voice assistant session with ordered conversational history."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="voice_conversations",
    )
    title = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=16,
        choices=ConversationStatus.choices,
        default=ConversationStatus.ACTIVE,
        db_index=True,
    )
    language = models.CharField(max_length=16, default="en")
    messages = models.JSONField(default=list, blank=True)
    context = models.JSONField(default=dict, blank=True)
    last_interaction_at = models.DateTimeField(null=True, blank=True, db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta(UUIDTimestampedModel.Meta):
        db_table = "voice_conversations"
        indexes = (
            models.Index(
                fields=("user", "status", "-last_interaction_at"),
                name="voice_user_active_idx",
            ),
        )

    def __str__(self) -> str:
        return self.title or f"Conversation {self.uuid}"
