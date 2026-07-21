from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from django.conf import settings
from django.utils import timezone
from google.auth.exceptions import GoogleAuthError, RefreshError
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from oauthlib.oauth2 import OAuth2Error
from requests import get as http_get
from requests.exceptions import RequestException

from apps.accounts.models import User
from apps.email_accounts.models import EmailAccount, EmailProvider, EmailSyncStatus
from apps.email_accounts.repositories import EmailAccountRepository

from .exceptions import (
    OAuthConfigurationError,
    OAuthExchangeFailed,
    OAuthIdentityInvalid,
    RefreshTokenUnavailable,
)
from .oauth_state_service import OAuthStateService
from .token_cipher import OAuthTokenCipher

logger = logging.getLogger(__name__)

GOOGLE_SCOPE_ALIASES = {
    "email": "https://www.googleapis.com/auth/userinfo.email",
    "profile": "https://www.googleapis.com/auth/userinfo.profile",
}
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class TimeoutRequest(Request):
    def __call__(self, *args: Any, timeout: float | None = None, **kwargs: Any) -> Any:
        return super().__call__(
            *args,
            timeout=timeout or settings.GOOGLE_API_TIMEOUT_SECONDS,
            **kwargs,
        )


@dataclass(frozen=True, slots=True)
class GmailConnection:
    account: EmailAccount
    client_redirect_uri: str


class GmailOAuthService:
    def __init__(
        self,
        repository: EmailAccountRepository | None = None,
        state_service: OAuthStateService | None = None,
        cipher: OAuthTokenCipher | None = None,
    ) -> None:
        self.repository = repository or EmailAccountRepository()
        self.state_service = state_service or OAuthStateService()
        self.cipher = cipher or OAuthTokenCipher()

    @staticmethod
    def _client_config() -> dict[str, object]:
        if not all(
            (
                settings.GOOGLE_OAUTH_CLIENT_ID,
                settings.GOOGLE_OAUTH_CLIENT_SECRET,
                settings.GOOGLE_OAUTH_REDIRECT_URI,
            )
        ):
            raise OAuthConfigurationError("Google OAuth is not configured.")
        return {
            "web": {
                "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

    @staticmethod
    def _oauth_scopes() -> list[str]:
        """Use Google's canonical scope names to avoid false scope-change failures."""
        canonical = (
            GOOGLE_SCOPE_ALIASES.get(str(scope), str(scope))
            for scope in settings.GOOGLE_OAUTH_SCOPES
        )
        return list(dict.fromkeys(canonical))

    @staticmethod
    def _database_expiry(value: datetime | None) -> datetime | None:
        if value is not None and timezone.is_naive(value):
            return timezone.make_aware(value, UTC)
        return value

    @staticmethod
    def _google_expiry(value: datetime | None) -> datetime | None:
        if value is not None and timezone.is_aware(value):
            return timezone.make_naive(value, UTC)
        return value

    @classmethod
    def _flow(
        cls,
        *,
        state: str | None = None,
        code_verifier: str | None = None,
    ) -> Flow:
        flow = Flow.from_client_config(
            cls._client_config(),
            scopes=cls._oauth_scopes(),
            state=state,
            code_verifier=code_verifier,
        )
        flow.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI
        return flow

    def authorization_url(self, *, user: User, client_redirect_uri: str) -> str:
        # PKCE binds the authorization request to the later code exchange. The
        # verifier remains server-side in the same single-use cache entry as state.
        code_verifier = secrets.token_urlsafe(96)
        state = self.state_service.issue(
            user_uuid=str(user.uuid),
            client_redirect_uri=client_redirect_uri,
            code_verifier=code_verifier,
        )
        authorization_url, _ = self._flow(
            state=state,
            code_verifier=code_verifier,
        ).authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return authorization_url

    @staticmethod
    def _identity_claims(credentials: Credentials) -> dict[str, Any]:
        if credentials.id_token:
            try:
                return id_token.verify_oauth2_token(
                    credentials.id_token,
                    TimeoutRequest(),
                    settings.GOOGLE_OAUTH_CLIENT_ID,
                    clock_skew_in_seconds=settings.GOOGLE_OAUTH_CLOCK_SKEW_SECONDS,
                )
            except (GoogleAuthError, ValueError) as exc:
                logger.warning("Google OAuth ID token verification failed", exc_info=True)
                raise OAuthIdentityInvalid("Google identity verification failed.") from exc

        # Google normally returns an ID token for the openid scope. UserInfo is
        # the standards-based fallback when a valid access token is returned without it.
        logger.info("Google OAuth response omitted ID token; using UserInfo fallback")
        try:
            response = http_get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {credentials.token}"},
                timeout=settings.GOOGLE_API_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            claims = response.json()
        except (RequestException, ValueError) as exc:
            logger.warning("Google OAuth UserInfo request failed", exc_info=True)
            raise OAuthIdentityInvalid("Google identity verification failed.") from exc
        if not isinstance(claims, dict):
            logger.warning("Google OAuth UserInfo returned an invalid payload")
            raise OAuthIdentityInvalid("Google identity verification failed.")
        return claims

    def complete(self, *, code: str, signed_state: str) -> GmailConnection:
        oauth_state = self.state_service.consume(signed_state)
        try:
            user = User.objects.get(uuid=oauth_state.user_uuid, is_active=True)
        except User.DoesNotExist as exc:
            raise OAuthIdentityInvalid("The MailPilot user no longer exists.") from exc

        flow = self._flow(
            state=signed_state,
            code_verifier=oauth_state.code_verifier,
        )
        try:
            flow.fetch_token(code=code)
        except (GoogleAuthError, OAuth2Error, RequestException, ValueError, Warning) as exc:
            logger.warning("Google OAuth code exchange failed", exc_info=True)
            raise OAuthExchangeFailed("Google authorization could not be completed.") from exc

        credentials = flow.credentials
        claims = self._identity_claims(credentials)

        provider_id = str(claims.get("sub", ""))
        email = str(claims.get("email", "")).lower()
        if not provider_id or not email or not claims.get("email_verified"):
            logger.warning(
                "Google OAuth identity claims were incomplete",
                extra={
                    "has_provider_id": bool(provider_id),
                    "has_email": bool(email),
                    "email_verified": bool(claims.get("email_verified")),
                },
            )
            raise OAuthIdentityInvalid("Google did not return a verified email identity.")

        existing = EmailAccount.objects.filter(
            user=user,
            provider=EmailProvider.GMAIL,
            provider_account_id=provider_id,
        ).first()
        refresh_encrypted = (
            self.cipher.encrypt(credentials.refresh_token)
            if credentials.refresh_token
            else existing.refresh_token_encrypted if existing else ""
        )
        if not refresh_encrypted:
            logger.warning(
                "Google OAuth refresh token unavailable",
                extra={"existing_account": existing is not None},
            )
            raise RefreshTokenUnavailable(
                "Google did not issue offline credentials; reconnect and grant consent."
            )

        account = self.repository.save_gmail_credentials(
            user=user,
            provider_account_id=provider_id,
            email_address=email,
            display_name=str(claims.get("name", "")),
            access_token_encrypted=self.cipher.encrypt(credentials.token),
            refresh_token_encrypted=refresh_encrypted,
            token_expires_at=self._database_expiry(credentials.expiry),
            oauth_scopes=list(credentials.scopes or self._oauth_scopes()),
            encryption_key_version=self.cipher.active_key_version,
        )
        return GmailConnection(account=account, client_redirect_uri=oauth_state.client_redirect_uri)

    def credentials_for(self, account: EmailAccount) -> Credentials:
        if not account.refresh_token_encrypted:
            account.sync_status = EmailSyncStatus.REAUTH_REQUIRED
            account.save(update_fields=("sync_status", "updated_at"))
            raise RefreshTokenUnavailable("The Gmail account must be reauthorized.")

        credentials = Credentials(
            token=self.cipher.decrypt(account.access_token_encrypted),
            refresh_token=self.cipher.decrypt(account.refresh_token_encrypted),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            scopes=account.oauth_scopes,
            expiry=self._google_expiry(account.token_expires_at),
        )
        if credentials.expired:
            try:
                credentials.refresh(TimeoutRequest())
            except RefreshError as exc:
                account.sync_status = EmailSyncStatus.REAUTH_REQUIRED
                account.last_sync_error = "Google credentials require reauthorization."
                account.save(
                    update_fields=("sync_status", "last_sync_error", "updated_at")
                )
                raise RefreshTokenUnavailable("The Gmail account must be reauthorized.") from exc
            self.repository.save_refreshed_credentials(
                account,
                access_token_encrypted=self.cipher.encrypt(credentials.token),
                refresh_token_encrypted=self.cipher.encrypt(
                    credentials.refresh_token or self.cipher.decrypt(
                        account.refresh_token_encrypted
                    )
                ),
                token_expires_at=self._database_expiry(credentials.expiry),
                encryption_key_version=self.cipher.active_key_version,
            )
        return credentials
