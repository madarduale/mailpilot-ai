from __future__ import annotations

from django.db.models import QuerySet

from apps.accounts.models import User
from apps.email_accounts.models import EmailAccount, EmailSyncStatus


class GmailAccountNotFoundError(Exception):
    pass


class GmailAccountService:
    @staticmethod
    def list_for_user(user: User) -> QuerySet[EmailAccount]:
        return EmailAccount.objects.filter(user=user).order_by("-is_primary", "email_address")

    @staticmethod
    def disconnect(user: User, account_uuid: str) -> None:
        account = EmailAccount.objects.filter(user=user, uuid=account_uuid).first()
        if account is None:
            raise GmailAccountNotFoundError
        account.access_token_encrypted = ""
        account.refresh_token_encrypted = ""
        account.sync_status = EmailSyncStatus.DISCONNECTED
        account.sync_cursor = ""
        account.save(
            update_fields=(
                "access_token_encrypted",
                "refresh_token_encrypted",
                "sync_status",
                "sync_cursor",
                "updated_at",
            )
        )
