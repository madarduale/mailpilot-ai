from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.emails.models import Email
from apps.reminders.models import Reminder, ReminderStatus
from apps.reminders.repositories import ReminderRepository


class ReminderNotFoundError(Exception):
    pass


class ReminderEmailNotFoundError(Exception):
    pass


class ReminderService:
    def __init__(self, repository: ReminderRepository | None = None) -> None:
        self.repository = repository or ReminderRepository()

    @transaction.atomic
    def create(self, user: User, values: dict[str, Any]) -> Reminder:
        email = self._email(user, values.pop("email_uuid", None))
        return Reminder.objects.create(user=user, email=email, source="manual", **values)

    @transaction.atomic
    def update(self, user: User, uuid: str, values: dict[str, Any]) -> Reminder:
        reminder = self.repository.get(user, uuid)
        if reminder is None:
            raise ReminderNotFoundError
        if "email_uuid" in values:
            reminder.email = self._email(user, values.pop("email_uuid"))
        for field, value in values.items():
            setattr(reminder, field, value)
        if reminder.status == ReminderStatus.COMPLETED and reminder.completed_at is None:
            reminder.completed_at = timezone.now()
        elif reminder.status != ReminderStatus.COMPLETED:
            reminder.completed_at = None
        reminder.save()
        return reminder

    @transaction.atomic
    def delete(self, user: User, uuid: str) -> None:
        reminder = self.repository.get(user, uuid)
        if reminder is None:
            raise ReminderNotFoundError
        reminder.delete()

    @transaction.atomic
    def complete(self, user: User, uuid: str) -> Reminder:
        """Mark a user-owned reminder complete."""

        reminder = self.repository.get(user, uuid)
        if reminder is None:
            raise ReminderNotFoundError
        if reminder.status != ReminderStatus.COMPLETED:
            reminder.status = ReminderStatus.COMPLETED
            reminder.completed_at = timezone.now()
            reminder.save(update_fields=("status", "completed_at", "updated_at"))
        return reminder

    @staticmethod
    def _email(user: User, uuid: object) -> Email | None:
        if uuid is None:
            return None
        email = Email.objects.filter(account__user=user, uuid=uuid).first()
        if email is None:
            raise ReminderEmailNotFoundError
        return email
