from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TypedDict, cast

from django.db.models import Count, Q

from apps.accounts.models import User
from apps.emails.models import Email
from apps.notifications.models import Notification, NotificationStatus
from apps.preferences.models import UserPreference
from apps.reminders.models import Reminder, ReminderStatus


@dataclass(frozen=True, slots=True)
class DashboardPreferences:
    importance_threshold: int = 75
    timezone: str = "UTC"


class DashboardStats(TypedDict):
    important: int
    action_required: int
    unread: int


class DashboardRepository:
    """Optimized, user-scoped dashboard read queries."""

    @staticmethod
    def get_preferences(user: User) -> DashboardPreferences:
        values = (
            UserPreference.objects.filter(user=user)
            .values("importance_threshold", "timezone")
            .first()
        )
        if values is None:
            return DashboardPreferences()
        return DashboardPreferences(
            importance_threshold=int(values["importance_threshold"]),
            timezone=str(values["timezone"]),
        )

    @staticmethod
    def get_stats(
        user: User,
        *,
        start: datetime,
        end: datetime,
        importance_threshold: int,
    ) -> DashboardStats:
        values = Email.objects.filter(
            account__user=user,
            is_done=False,
            received_at__gte=start,
            received_at__lt=end,
        ).aggregate(
            important=Count(
                "uuid",
                filter=Q(ai_summary__importance_score__gt=importance_threshold),
            ),
            action_required=Count(
                "uuid",
                filter=Q(ai_summary__action_required=True),
            ),
            unread=Count("uuid", filter=Q(is_read=False)),
        )
        return cast(DashboardStats, values)

    @staticmethod
    def list_important_emails(
        user: User,
        *,
        start: datetime,
        end: datetime,
        importance_threshold: int,
        limit: int = 5,
    ) -> list[Email]:
        queryset = (
            Email.objects.filter(
                account__user=user,
                received_at__gte=start,
                received_at__lt=end,
                ai_summary__importance_score__gt=importance_threshold,
                is_done=False,
            )
            .select_related("ai_summary__category")
            .order_by("-ai_summary__importance_score", "-received_at")
        )
        return list(queryset[:limit])

    @staticmethod
    def list_upcoming_reminders(user: User, *, limit: int = 5) -> list[Reminder]:
        queryset = Reminder.objects.filter(
            user=user,
            status__in=(ReminderStatus.PENDING, ReminderStatus.SNOOZED),
        ).order_by("due_at")
        return list(queryset[:limit])

    @staticmethod
    def count_unread_notifications(user: User) -> int:
        return (
            Notification.objects.filter(user=user, read_at__isnull=True)
            .exclude(status__in=(NotificationStatus.READ, NotificationStatus.FAILED))
            .count()
        )

    @staticmethod
    def count_unread_emails(user: User) -> int:
        return Email.objects.filter(account__user=user, is_read=False).count()
