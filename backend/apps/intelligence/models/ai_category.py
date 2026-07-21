from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimestampedModel


class AICategory(UUIDTimestampedModel):
    """System-defined or user-defined email classification category."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_categories",
        null=True,
        blank=True,
        help_text="Null for a system category; set for a private user category.",
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#64748B")
    icon = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta(UUIDTimestampedModel.Meta):
        db_table = "ai_categories"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name
