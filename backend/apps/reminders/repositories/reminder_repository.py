from __future__ import annotations

from django.db.models import QuerySet

from apps.accounts.models import User
from apps.reminders.models import Reminder


class ReminderRepository:
    @staticmethod
    def for_user(user: User) -> QuerySet[Reminder]:
        return Reminder.objects.filter(user=user).select_related("email")

    @classmethod
    def get(cls, user: User, uuid: str) -> Reminder | None:
        return cls.for_user(user).filter(uuid=uuid).first()
