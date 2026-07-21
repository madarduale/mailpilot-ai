from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import getaddresses, parseaddr
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.email_accounts.integrations.gmail.client import GmailClientFactory
from apps.email_accounts.models import EmailAccount, EmailSyncStatus
from apps.emails.repositories import EmailRepository
from apps.intelligence.models import AISummary

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GmailSyncResult:
    created: int
    updated: int


class GmailSyncService:
    """Synchronize normalized Gmail messages and queue high-value notifications."""

    def __init__(
        self,
        client_factory: GmailClientFactory | None = None,
        repository: EmailRepository | None = None,
    ) -> None:
        self.client_factory = client_factory or GmailClientFactory()
        self.repository = repository or EmailRepository()

    @staticmethod
    def _decode(data: str | None) -> str:
        if not data:
            return ""
        try:
            return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode(
                "utf-8", errors="replace"
            )
        except (ValueError, TypeError):
            return ""

    @classmethod
    def _parts(cls, payload: dict[str, Any]) -> tuple[str, str, list[dict[str, Any]]]:
        plain = ""
        html = ""
        attachments: list[dict[str, Any]] = []

        def visit(part: dict[str, Any]) -> None:
            nonlocal plain, html
            mime_type = str(part.get("mimeType", ""))
            filename = str(part.get("filename", ""))
            body = part.get("body") or {}
            if filename and body.get("attachmentId"):
                attachment_id = str(body["attachmentId"])
                attachments.append(
                    {
                        "uuid": attachment_id,
                        "filename": filename,
                        "content_type": mime_type or "application/octet-stream",
                        "size": int(body.get("size") or 0),
                        "download_url": "",
                    }
                )
            elif mime_type == "text/plain" and not plain:
                plain = cls._decode(body.get("data"))
            elif mime_type == "text/html" and not html:
                html = cls._decode(body.get("data"))
            for child in part.get("parts") or []:
                visit(child)

        visit(payload)
        return plain, html, attachments

    @classmethod
    def _normalize(cls, message: dict[str, Any]) -> dict[str, Any]:
        payload = message.get("payload") or {}
        headers = {
            str(item.get("name", "")).lower(): str(item.get("value", ""))
            for item in payload.get("headers") or []
        }
        sender_name, sender = parseaddr(headers.get("from", ""))
        plain, html, attachments = cls._parts(payload)
        labels = [str(label) for label in message.get("labelIds") or []]
        return {
            "thread_id": str(message.get("threadId", "")),
            "subject": headers.get("subject", ""),
            "sender": (sender or "unknown@invalid.local")[:254],
            "sender_name": sender_name[:255],
            "recipients": [address for _, address in getaddresses([headers.get("to", "")])],
            "cc_recipients": [address for _, address in getaddresses([headers.get("cc", "")])],
            "bcc_recipients": [address for _, address in getaddresses([headers.get("bcc", "")])],
            "reply_to": parseaddr(headers.get("reply-to", ""))[1][:254],
            "body": plain,
            "body_html": html,
            "snippet": str(message.get("snippet", "")),
            "received_at": datetime.fromtimestamp(
                int(message.get("internalDate") or 0) / 1000, tz=UTC
            ),
            "attachments": attachments,
            "is_read": "UNREAD" not in labels,
            "is_starred": "STARRED" in labels,
            "is_draft": "DRAFT" in labels,
            "labels": labels,
            "headers": headers,
        }

    def sync(
        self, account: EmailAccount, *, notify_new: bool, max_messages: int = 50
    ) -> GmailSyncResult:
        # The first import establishes a baseline and must never notify for old mail.
        should_notify = notify_new and account.last_synced_at is not None
        gmail_query = (
            "newer_than:2d -in:spam -in:trash"
            if account.last_synced_at is not None
            else "newer_than:30d -in:spam -in:trash"
        )
        account.sync_status = EmailSyncStatus.SYNCING
        account.last_sync_error = ""
        account.save(update_fields=("sync_status", "last_sync_error", "updated_at"))
        try:
            client = self.client_factory.build(account)
            response = (
                client.users()
                .messages()
                .list(
                    userId="me",
                    maxResults=max_messages,
                    q=gmail_query,
                )
                .execute()
            )
            created_count = 0
            updated_count = 0
            for item in response.get("messages") or []:
                message_id = str(item.get("id", ""))
                if not message_id:
                    continue
                message = (
                    client.users()
                    .messages()
                    .get(userId="me", id=message_id, format="full")
                    .execute()
                )
                email, created = self.repository.upsert(
                    account=account,
                    provider_message_id=message_id,
                    defaults=self._normalize(message),
                )
                created_count += int(created)
                updated_count += int(not created)
                if created or not AISummary.objects.filter(email=email).exists():
                    from apps.intelligence.tasks import analyze_email

                    transaction.on_commit(
                        lambda email_uuid=str(email.uuid), notify=(should_notify and created): (
                            analyze_email.delay(email_uuid, notify)
                        )
                    )

            account.sync_status = EmailSyncStatus.ACTIVE
            account.sync_cursor = str(response.get("historyId") or account.sync_cursor)
            account.last_synced_at = timezone.now()
            account.last_sync_error = ""
            account.save(
                update_fields=(
                    "sync_status",
                    "sync_cursor",
                    "last_synced_at",
                    "last_sync_error",
                    "updated_at",
                )
            )
            return GmailSyncResult(created=created_count, updated=updated_count)
        except Exception as exc:
            account.sync_status = EmailSyncStatus.FAILED
            account.last_sync_error = str(exc)[:2000]
            account.save(update_fields=("sync_status", "last_sync_error", "updated_at"))
            logger.exception(
                "Gmail synchronization failed", extra={"account_uuid": str(account.uuid)}
            )
            raise
