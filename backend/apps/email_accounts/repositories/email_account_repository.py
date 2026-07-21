from __future__ import annotations

from django.db import transaction

from apps.accounts.models import User
from apps.email_accounts.models import EmailAccount, EmailProvider, EmailSyncStatus


class EmailAccountRepository:
    @staticmethod
    def get_for_user(user: User, account_uuid: str) -> EmailAccount | None:
        return EmailAccount.objects.filter(user=user, uuid=account_uuid).first()

    @staticmethod
    @transaction.atomic
    def save_gmail_credentials(
        *,
        user: User,
        provider_account_id: str,
        email_address: str,
        display_name: str,
        access_token_encrypted: str,
        refresh_token_encrypted: str,
        token_expires_at: object,
        oauth_scopes: list[str],
        encryption_key_version: int,
    ) -> EmailAccount:
        account, _ = EmailAccount.objects.update_or_create(
            user=user,
            provider=EmailProvider.GMAIL,
            provider_account_id=provider_account_id,
            defaults={
                "email_address": email_address,
                "display_name": display_name,
                "access_token_encrypted": access_token_encrypted,
                "refresh_token_encrypted": refresh_token_encrypted,
                "token_expires_at": token_expires_at,
                "oauth_scopes": oauth_scopes,
                "encryption_key_version": encryption_key_version,
                "sync_status": EmailSyncStatus.ACTIVE,
                "last_sync_error": "",
            },
        )
        if not EmailAccount.objects.filter(user=user, is_primary=True).exists():
            account.is_primary = True
            account.save(update_fields=("is_primary", "updated_at"))
        return account

    @staticmethod
    def save_refreshed_credentials(
        account: EmailAccount,
        *,
        access_token_encrypted: str,
        refresh_token_encrypted: str,
        token_expires_at: object,
        encryption_key_version: int,
    ) -> EmailAccount:
        account.access_token_encrypted = access_token_encrypted
        account.refresh_token_encrypted = refresh_token_encrypted
        account.token_expires_at = token_expires_at
        account.encryption_key_version = encryption_key_version
        account.sync_status = EmailSyncStatus.ACTIVE
        account.last_sync_error = ""
        account.save(
            update_fields=(
                "access_token_encrypted",
                "refresh_token_encrypted",
                "token_expires_at",
                "encryption_key_version",
                "sync_status",
                "last_sync_error",
                "updated_at",
            )
        )
        return account
