from __future__ import annotations

from typing import Any

import httplib2
from django.conf import settings
from google_auth_httplib2 import AuthorizedHttp
from googleapiclient.discovery import Resource, build

from apps.email_accounts.models import EmailAccount
from apps.email_accounts.services.gmail_oauth_service import GmailOAuthService


class GmailClientFactory:
    """Build an authenticated Gmail client with refreshed credentials and a timeout."""

    def __init__(self, oauth_service: GmailOAuthService | None = None) -> None:
        self.oauth_service = oauth_service or GmailOAuthService()

    def build(self, account: EmailAccount) -> Resource:
        credentials = self.oauth_service.credentials_for(account)
        transport = AuthorizedHttp(
            credentials,
            http=httplib2.Http(timeout=settings.GOOGLE_API_TIMEOUT_SECONDS),
        )
        return build(
            "gmail",
            "v1",
            http=transport,
            cache_discovery=False,
        )

    def profile(self, account: EmailAccount) -> dict[str, Any]:
        return self.build(account).users().getProfile(userId="me").execute()
