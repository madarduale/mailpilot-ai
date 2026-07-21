from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import UUIDTimestampedModel


class EmailProvider(models.TextChoices):
    GMAIL = "gmail", "Gmail"


class EmailSyncStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SYNCING = "syncing", "Syncing"
    ACTIVE = "active", "Active"
    REAUTH_REQUIRED = "reauth_required", "Reauthorization required"
    FAILED = "failed", "Failed"
    DISCONNECTED = "disconnected", "Disconnected"


class EmailAccount(UUIDTimestampedModel):
    """An external mailbox and its encrypted OAuth credentials."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_accounts",
    )
    provider = models.CharField(
        max_length=32,
        choices=EmailProvider.choices,
        default=EmailProvider.GMAIL,
    )
    provider_account_id = models.CharField(max_length=255)
    email_address = models.EmailField(max_length=254)
    display_name = models.CharField(max_length=255, blank=True)

    # Only authenticated ciphertext is persisted. Decryption belongs to the
    # OAuth credential service, never to this model.
    access_token_encrypted = models.TextField()
    refresh_token_encrypted = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    encryption_key_version = models.PositiveSmallIntegerField(default=1)
    oauth_scopes = models.JSONField(default=list, blank=True)

    sync_status = models.CharField(
        max_length=32,
        choices=EmailSyncStatus.choices,
        default=EmailSyncStatus.PENDING,
        db_index=True,
    )
    sync_cursor = models.CharField(max_length=512, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_sync_error = models.TextField(blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta(UUIDTimestampedModel.Meta):
        db_table = "email_accounts"
        constraints = (
            models.UniqueConstraint(
                fields=("user", "provider", "provider_account_id"),
                name="uniq_user_provider_account",
            ),
            models.UniqueConstraint(
                fields=("user", "provider", "email_address"),
                name="uniq_user_provider_email",
            ),
        )
        indexes = (
            models.Index(fields=("user", "sync_status"), name="email_acct_sync_idx"),
        )

    def __str__(self) -> str:
        return f"{self.email_address} ({self.provider})"
