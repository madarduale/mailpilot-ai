from __future__ import annotations

import secrets
from dataclasses import dataclass
from urllib.parse import urlparse

from django.conf import settings
from django.core import signing
from django.core.cache import cache

from .exceptions import InvalidOAuthState

STATE_SALT = "mailpilot.gmail.oauth-state.v1"


@dataclass(frozen=True, slots=True)
class OAuthState:
    user_uuid: str
    client_redirect_uri: str
    code_verifier: str


class OAuthStateService:
    @staticmethod
    def _validate_redirect_uri(uri: str) -> None:
        parsed = urlparse(uri)
        if parsed.scheme not in settings.OAUTH_MOBILE_REDIRECT_SCHEMES:
            raise InvalidOAuthState("Unsupported mobile callback URI.")
        if parsed.username or parsed.password:
            raise InvalidOAuthState("Invalid mobile callback URI.")

    def issue(
        self,
        *,
        user_uuid: str,
        client_redirect_uri: str,
        code_verifier: str,
    ) -> str:
        self._validate_redirect_uri(client_redirect_uri)
        nonce = secrets.token_urlsafe(32)
        cache_key = f"gmail-oauth-state:{nonce}"
        cache.set(
            cache_key,
            {"user_uuid": user_uuid, "code_verifier": code_verifier},
            timeout=settings.GOOGLE_OAUTH_STATE_TTL_SECONDS,
        )
        return signing.dumps(
            {"nonce": nonce, "user_uuid": user_uuid, "redirect_uri": client_redirect_uri},
            salt=STATE_SALT,
            compress=True,
        )

    def consume(self, signed_state: str) -> OAuthState:
        try:
            payload = signing.loads(
                signed_state,
                salt=STATE_SALT,
                max_age=settings.GOOGLE_OAUTH_STATE_TTL_SECONDS,
            )
            nonce = str(payload["nonce"])
            user_uuid = str(payload["user_uuid"])
            redirect_uri = str(payload["redirect_uri"])
        except (signing.BadSignature, KeyError, TypeError, ValueError) as exc:
            raise InvalidOAuthState("OAuth state is invalid or expired.") from exc

        self._validate_redirect_uri(redirect_uri)
        cache_key = f"gmail-oauth-state:{nonce}"
        cached_state = cache.get(cache_key)
        if not isinstance(cached_state, dict) or cached_state.get("user_uuid") != user_uuid:
            raise InvalidOAuthState("OAuth state was already used or expired.")
        code_verifier = cached_state.get("code_verifier")
        if not isinstance(code_verifier, str) or not code_verifier:
            raise InvalidOAuthState("OAuth state is incomplete; restart authorization.")
        cache.delete(cache_key)
        return OAuthState(
            user_uuid=user_uuid,
            client_redirect_uri=redirect_uri,
            code_verifier=code_verifier,
        )
