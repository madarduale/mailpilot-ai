from __future__ import annotations

from typing import Any

from apps.email_accounts.models import EmailAccount
from apps.emails.models import Email


class EmailRepository:
    @staticmethod
    def upsert(
        *, account: EmailAccount, provider_message_id: str, defaults: dict[str, Any]
    ) -> tuple[Email, bool]:
        return Email.objects.update_or_create(
            account=account,
            provider_message_id=provider_message_id,
            defaults=defaults,
        )
