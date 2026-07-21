from __future__ import annotations

import uuid

from django.db import models


class UUIDTimestampedModel(models.Model):
    """Shared identity and audit timestamps for all persisted domain entities."""

    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        serialize=False,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("-created_at",)
