from __future__ import annotations

from apps.accounts.models import User
from apps.preferences.models import UserPreference


class PreferenceService:
    @staticmethod
    def get_or_create(user: User) -> UserPreference:
        preference, _ = UserPreference.objects.get_or_create(user=user)
        return preference
