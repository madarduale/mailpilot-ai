from __future__ import annotations

import logging
from typing import Any

from celery import shared_task

from apps.email_accounts.models import EmailAccount, EmailSyncStatus
from apps.email_accounts.services.gmail_sync_service import GmailSyncService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def sync_gmail_account(
    self: Any,
    account_uuid: str,
    notify_new: bool = True,
) -> dict[str, int] | None:
    try:
        account = EmailAccount.objects.select_related("user").get(uuid=account_uuid)
    except EmailAccount.DoesNotExist:
        logger.warning("Cannot sync missing Gmail account", extra={"account_uuid": account_uuid})
        return None
    result = GmailSyncService().sync(account, notify_new=notify_new)
    return {"created": result.created, "updated": result.updated}


@shared_task
def sync_all_gmail_accounts() -> int:
    account_ids = EmailAccount.objects.filter(
        sync_status=EmailSyncStatus.ACTIVE,
    ).values_list("uuid", flat=True)
    queued = 0
    for account_uuid in account_ids.iterator():
        sync_gmail_account.delay(str(account_uuid), True)
        queued += 1
    return queued
