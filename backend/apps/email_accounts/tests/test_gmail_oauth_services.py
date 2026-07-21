from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.email_accounts.models import EmailAccount, EmailSyncStatus
from apps.email_accounts.services import GmailOAuthService, OAuthStateService, OAuthTokenCipher
from apps.email_accounts.services.exceptions import InvalidOAuthState, OAuthExchangeFailed

pytestmark = pytest.mark.django_db

FERNET_KEY = Fernet.generate_key().decode()
OAUTH_SETTINGS = override_settings(
    GOOGLE_OAUTH_CLIENT_ID="test-client-id",
    GOOGLE_OAUTH_CLIENT_SECRET="test-client-secret",
    GOOGLE_OAUTH_REDIRECT_URI="https://api.example.com/api/v1/oauth/gmail/callback/",
    GOOGLE_OAUTH_SCOPES=["openid", "email", "profile"],
    GOOGLE_OAUTH_STATE_TTL_SECONDS=600,
    GOOGLE_OAUTH_CLOCK_SKEW_SECONDS=30,
    OAUTH_MOBILE_REDIRECT_SCHEMES=["mailpilot"],
    OAUTH_TOKEN_ENCRYPTION_KEYS=[FERNET_KEY],
)


@OAUTH_SETTINGS
def test_oauth_state_is_single_use_and_bound_to_mobile_callback() -> None:
    service = OAuthStateService()
    state = service.issue(
        user_uuid="32e774a2-8798-4db0-a04d-bbc770acb321",
        client_redirect_uri="mailpilot://oauth/gmail",
        code_verifier="test-code-verifier",
    )

    result = service.consume(state)

    assert result.user_uuid == "32e774a2-8798-4db0-a04d-bbc770acb321"
    assert result.client_redirect_uri == "mailpilot://oauth/gmail"
    assert result.code_verifier == "test-code-verifier"
    with pytest.raises(InvalidOAuthState):
        service.consume(state)


@OAUTH_SETTINGS
def test_token_cipher_never_persists_plaintext() -> None:
    cipher = OAuthTokenCipher()

    ciphertext = cipher.encrypt("sensitive-refresh-token")

    assert ciphertext != "sensitive-refresh-token"
    assert cipher.decrypt(ciphertext) == "sensitive-refresh-token"


@OAUTH_SETTINGS
def test_callback_verifies_identity_and_stores_encrypted_tokens() -> None:
    user = User.objects.create_user(email="oauth-owner@example.com")
    state_service = OAuthStateService()
    state = state_service.issue(
        user_uuid=str(user.uuid),
        client_redirect_uri="mailpilot://oauth/gmail",
        code_verifier="test-code-verifier",
    )
    credentials = SimpleNamespace(
        id_token="signed-google-id-token",
        token="access-token",
        refresh_token="refresh-token",
        expiry=timezone.now() + timedelta(hours=1),
        scopes=["openid", "email", "profile"],
    )
    flow = MagicMock(credentials=credentials)
    service = GmailOAuthService(state_service=state_service)

    with (
        patch.object(GmailOAuthService, "_flow", return_value=flow),
        patch(
            "apps.email_accounts.services.gmail_oauth_service.id_token.verify_oauth2_token",
            return_value={
                "sub": "google-account-123",
                "email": "owner@gmail.com",
                "email_verified": True,
                "name": "Mail Owner",
            },
        ),
    ):
        connection = service.complete(code="authorization-code", signed_state=state)

    account = EmailAccount.objects.get(uuid=connection.account.uuid)
    assert account.sync_status == EmailSyncStatus.ACTIVE
    assert account.access_token_encrypted != "access-token"
    assert account.refresh_token_encrypted != "refresh-token"
    assert service.cipher.decrypt(account.refresh_token_encrypted) == "refresh-token"
    assert connection.client_redirect_uri == "mailpilot://oauth/gmail"


@OAUTH_SETTINGS
def test_pkce_verifier_is_reused_for_callback_code_exchange() -> None:
    user = User.objects.create_user(email="pkce-owner@example.com")
    service = GmailOAuthService()
    authorization_flow = MagicMock()
    authorization_flow.authorization_url.return_value = (
        "https://accounts.google.com/o/oauth2/v2/auth",
        "unused-library-state",
    )

    with patch.object(
        GmailOAuthService,
        "_flow",
        return_value=authorization_flow,
    ) as flow_factory:
        service.authorization_url(
            user=user,
            client_redirect_uri="mailpilot://oauth/gmail",
        )

    start_kwargs = flow_factory.call_args.kwargs
    signed_state = start_kwargs["state"]
    code_verifier = start_kwargs["code_verifier"]
    assert 43 <= len(code_verifier) <= 128

    callback_flow = MagicMock()
    callback_flow.credentials = SimpleNamespace(
        id_token="signed-google-id-token",
        token="access-token",
        refresh_token="refresh-token",
        expiry=timezone.now() + timedelta(hours=1),
        scopes=["openid", "email", "profile"],
    )
    with (
        patch.object(
            GmailOAuthService,
            "_flow",
            return_value=callback_flow,
        ) as callback_flow_factory,
        patch(
            "apps.email_accounts.services.gmail_oauth_service.id_token.verify_oauth2_token",
            return_value={
                "sub": "google-account-pkce",
                "email": "pkce-owner@gmail.com",
                "email_verified": True,
            },
        ),
    ):
        service.complete(code="authorization-code", signed_state=signed_state)

    callback_flow_factory.assert_called_once_with(
        state=signed_state,
        code_verifier=code_verifier,
    )
    callback_flow.fetch_token.assert_called_once_with(code="authorization-code")


@OAUTH_SETTINGS
def test_google_scope_aliases_are_normalized() -> None:
    assert GmailOAuthService._oauth_scopes() == [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]


@OAUTH_SETTINGS
def test_scope_change_warning_becomes_safe_exchange_error() -> None:
    user = User.objects.create_user(email="scope-owner@example.com")
    state_service = OAuthStateService()
    state = state_service.issue(
        user_uuid=str(user.uuid),
        client_redirect_uri="mailpilot://oauth/gmail",
        code_verifier="test-code-verifier",
    )
    flow = MagicMock()
    flow.fetch_token.side_effect = Warning("Scope changed")
    service = GmailOAuthService(state_service=state_service)

    with (
        patch.object(GmailOAuthService, "_flow", return_value=flow),
        pytest.raises(OAuthExchangeFailed),
    ):
        service.complete(code="authorization-code", signed_state=state)


@OAUTH_SETTINGS
def test_missing_id_token_uses_google_userinfo() -> None:
    credentials = SimpleNamespace(id_token=None, token="access-token")
    response = MagicMock()
    response.json.return_value = {
        "sub": "google-userinfo-123",
        "email": "userinfo-owner@gmail.com",
        "email_verified": True,
    }

    with patch(
        "apps.email_accounts.services.gmail_oauth_service.http_get",
        return_value=response,
    ) as get_userinfo:
        claims = GmailOAuthService._identity_claims(credentials)

    assert claims["sub"] == "google-userinfo-123"
    get_userinfo.assert_called_once_with(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": "Bearer access-token"},
        timeout=30,
    )
    response.raise_for_status.assert_called_once_with()


@OAUTH_SETTINGS
def test_id_token_verification_allows_bounded_clock_skew() -> None:
    credentials = SimpleNamespace(id_token="signed-google-id-token", token="access-token")
    expected_claims = {
        "sub": "google-clock-skew-123",
        "email": "clock-owner@gmail.com",
        "email_verified": True,
    }

    with patch(
        "apps.email_accounts.services.gmail_oauth_service.id_token.verify_oauth2_token",
        return_value=expected_claims,
    ) as verify_token:
        claims = GmailOAuthService._identity_claims(credentials)

    assert claims == expected_claims
    verify_token.assert_called_once()
    assert verify_token.call_args.args[0] == "signed-google-id-token"
    assert verify_token.call_args.args[2] == "test-client-id"
    assert verify_token.call_args.kwargs == {"clock_skew_in_seconds": 30}


def test_google_credentials_receive_naive_utc_expiry() -> None:
    aware = timezone.now()
    normalized = GmailOAuthService._google_expiry(aware)
    assert normalized is not None
    assert timezone.is_naive(normalized)


def test_database_expiry_is_timezone_aware() -> None:
    naive = timezone.now().replace(tzinfo=None)
    normalized = GmailOAuthService._database_expiry(naive)
    assert normalized is not None
    assert timezone.is_aware(normalized)
