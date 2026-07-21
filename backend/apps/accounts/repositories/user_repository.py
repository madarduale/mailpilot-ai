from __future__ import annotations

from typing import Any

from django.db.models import QuerySet

from apps.accounts.models import User


class UserRepository:
    """Persistence boundary for user queries and mutations."""

    @staticmethod
    def active() -> QuerySet[User]:
        return User.objects.filter(is_active=True)

    @staticmethod
    def email_exists(email: str) -> bool:
        return User.objects.filter(email__iexact=email.strip()).exists()

    @staticmethod
    def get_by_email(email: str) -> User | None:
        return User.objects.filter(email__iexact=email.strip()).first()

    @staticmethod
    def create(*, email: str, password: str, **profile: Any) -> User:
        return User.objects.create_user(email=email, password=password, **profile)

    @staticmethod
    def save_profile(user: User, *, first_name: str, last_name: str) -> User:
        user.first_name = first_name
        user.last_name = last_name
        user.save(update_fields=("first_name", "last_name", "updated_at"))
        return user

