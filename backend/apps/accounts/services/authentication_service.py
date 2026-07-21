from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.db import IntegrityError, transaction
from django.http import HttpRequest
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.accounts.repositories import UserRepository
from apps.accounts.services.exceptions import (
    EmailAlreadyRegistered,
    IncorrectCurrentPassword,
    InvalidCredentials,
    InvalidRefreshToken,
)


@dataclass(frozen=True, slots=True)
class TokenPair:
    access: str
    refresh: str
    token_type: str = "Bearer"


@dataclass(frozen=True, slots=True)
class AuthenticationResult:
    user: User
    tokens: TokenPair


class AuthenticationService:
    """Application service for account and JWT authentication use cases."""

    def __init__(self, repository: UserRepository | None = None) -> None:
        self.repository = repository or UserRepository()

    @staticmethod
    def _issue_tokens(user: User) -> TokenPair:
        refresh = RefreshToken.for_user(user)
        refresh["email"] = user.email
        return TokenPair(access=str(refresh.access_token), refresh=str(refresh))

    @transaction.atomic
    def register(
        self,
        *,
        email: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
    ) -> AuthenticationResult:
        normalized_email = email.strip().lower()
        if self.repository.email_exists(normalized_email):
            raise EmailAlreadyRegistered

        try:
            user = self.repository.create(
                email=normalized_email,
                password=password,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
            )
        except IntegrityError as exc:
            raise EmailAlreadyRegistered from exc

        return AuthenticationResult(user=user, tokens=self._issue_tokens(user))

    def login(
        self,
        *,
        request: HttpRequest,
        email: str,
        password: str,
    ) -> AuthenticationResult:
        user = authenticate(request=request, email=email.strip().lower(), password=password)
        if user is None or not isinstance(user, User) or not user.is_active:
            raise InvalidCredentials

        update_last_login(sender=type(user), user=user)
        return AuthenticationResult(user=user, tokens=self._issue_tokens(user))

    @staticmethod
    def refresh(refresh_token: str) -> TokenPair:
        try:
            old_refresh = RefreshToken(refresh_token)  # type: ignore[arg-type]
            user_id = old_refresh.get("user_id")
            user = UserRepository.active().filter(uuid=user_id).first()
            if user is None:
                raise InvalidRefreshToken

            old_refresh.blacklist()
            return AuthenticationService._issue_tokens(user)
        except (TokenError, ValueError, TypeError) as exc:
            raise InvalidRefreshToken from exc

    @staticmethod
    def logout(refresh_token: str, *, user: User) -> None:
        try:
            token = RefreshToken(refresh_token)  # type: ignore[arg-type]
            if str(token.get("user_id")) != str(user.uuid):
                raise InvalidRefreshToken
            token.blacklist()
        except (TokenError, ValueError, TypeError) as exc:
            raise InvalidRefreshToken from exc

    @staticmethod
    def _revoke_all_refresh_tokens(user: User) -> None:
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        for token in OutstandingToken.objects.filter(user=user).iterator():
            BlacklistedToken.objects.get_or_create(token=token)

    @transaction.atomic
    def change_password(
        self,
        *,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        if not user.check_password(current_password):
            raise IncorrectCurrentPassword

        user.set_password(new_password)
        user.save(update_fields=("password", "updated_at"))
        self._revoke_all_refresh_tokens(user)

    def update_profile(self, user: User, **validated_data: Any) -> User:
        return self.repository.save_profile(
            user,
            first_name=validated_data.get("first_name", user.first_name),
            last_name=validated_data.get("last_name", user.last_name),
        )
