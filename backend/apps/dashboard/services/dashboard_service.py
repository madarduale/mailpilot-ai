from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone

from apps.accounts.models import User
from apps.dashboard.repositories import DashboardRepository
from apps.dashboard.repositories.dashboard_repository import DashboardStats
from apps.emails.models import Email
from apps.reminders.models import Reminder


@dataclass(frozen=True, slots=True)
class DashboardResult:
    briefing: str
    stats: DashboardStats
    important_emails: list[Email]
    reminders: list[Reminder]
    unread_notifications: int


class DashboardService:
    """Builds the current user's timezone-aware priority dashboard."""

    def __init__(self, repository: DashboardRepository | None = None) -> None:
        self.repository = repository or DashboardRepository()

    @staticmethod
    def _timezone(name: str) -> ZoneInfo:
        try:
            return ZoneInfo(name)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")

    @staticmethod
    def _briefing(stats: DashboardStats) -> str:
        important = stats["important"]
        action_required = stats["action_required"]
        if important == 0 and action_required == 0:
            return (
                "Your priority inbox is clear today. "
                "MailPilot will keep watching for what matters."
            )

        important_label = "email" if important == 1 else "emails"
        action_label = "message needs" if action_required == 1 else "messages need"
        return (
            f"You have {important} important {important_label} today, and "
            f"{action_required} {action_label} your action."
        )

    def get_dashboard(self, user: User) -> DashboardResult:
        preferences = self.repository.get_preferences(user)
        user_timezone = self._timezone(preferences.timezone)
        local_date = timezone.now().astimezone(user_timezone).date()
        start = datetime.combine(local_date, time.min, tzinfo=user_timezone).astimezone(UTC)
        end = datetime.combine(
            local_date + timedelta(days=1),
            time.min,
            tzinfo=user_timezone,
        ).astimezone(UTC)

        stats = self.repository.get_stats(
            user,
            start=start,
            end=end,
            importance_threshold=preferences.importance_threshold,
        )
        return DashboardResult(
            briefing=self._briefing(stats),
            stats=stats,
            important_emails=self.repository.list_important_emails(
                user,
                start=start,
                end=end,
                importance_threshold=preferences.importance_threshold,
            ),
            reminders=self.repository.list_upcoming_reminders(user),
            unread_notifications=self.repository.count_unread_notifications(user),
        )
