from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings

from .exceptions import OAuthConfigurationError


class OAuthTokenCipher:
    """Encrypt OAuth credentials with authenticated encryption and key rotation."""

    def __init__(self, keys: list[str] | None = None) -> None:
        configured = keys if keys is not None else settings.OAUTH_TOKEN_ENCRYPTION_KEYS
        if not configured:
            raise OAuthConfigurationError("OAuth token encryption is not configured.")
        try:
            self._fernets = [Fernet(key.encode()) for key in configured]
        except (TypeError, ValueError) as exc:
            raise OAuthConfigurationError("OAuth token encryption keys are invalid.") from exc
        self._cipher = MultiFernet(self._fernets)

    @property
    def active_key_version(self) -> int:
        return 1

    def encrypt(self, value: str) -> str:
        return self._fernets[0].encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        try:
            return self._cipher.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise OAuthConfigurationError("Stored OAuth credentials cannot be decrypted.") from exc
