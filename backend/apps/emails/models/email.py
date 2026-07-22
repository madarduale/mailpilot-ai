from __future__ import annotations

from django.db import models

from apps.common.models import UUIDTimestampedModel


class Email(UUIDTimestampedModel):
    """Normalized provider message retained for search and AI processing."""

    account = models.ForeignKey(
        "email_accounts.EmailAccount",
        on_delete=models.CASCADE,
        related_name="emails",
    )
    provider_message_id = models.CharField(max_length=255)
    thread_id = models.CharField(max_length=255, db_index=True)
    subject = models.TextField(blank=True)
    sender = models.EmailField(max_length=254)
    sender_name = models.CharField(max_length=255, blank=True)
    recipients = models.JSONField(default=list)
    cc_recipients = models.JSONField(default=list, blank=True)
    bcc_recipients = models.JSONField(default=list, blank=True)
    reply_to = models.EmailField(max_length=254, blank=True)
    body = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    snippet = models.TextField(blank=True)
    received_at = models.DateTimeField(db_index=True)
    attachments = models.JSONField(default=list, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    is_done = models.BooleanField(default=False, db_index=True)
    is_starred = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=False)
    labels = models.JSONField(default=list, blank=True)
    headers = models.JSONField(default=dict, blank=True)

    class Meta(UUIDTimestampedModel.Meta):
        db_table = "emails"
        ordering = ("-received_at", "-created_at")  # type: ignore[assignment]
        constraints = (
            models.UniqueConstraint(
                fields=("account", "provider_message_id"),
                name="uniq_account_provider_msg",
            ),
        )
        indexes = (
            models.Index(fields=("account", "-received_at"), name="email_acct_recv_idx"),
            models.Index(fields=("account", "thread_id"), name="email_acct_thread_idx"),
            models.Index(
                fields=("account", "is_read", "-received_at"),
                name="email_read_recv_idx",
            ),
        )

    def __str__(self) -> str:
        return self.subject or "(no subject)"
