from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone

from apps.accounts.models import User
from apps.emails.models import Email
from apps.preferences.models import UserPreference
from apps.proactive_assistant.enums import SuggestionType
from apps.proactive_assistant.models import AssistantSuggestion
from apps.proactive_assistant.repositories import BriefingRepository
from apps.reminders.models import Reminder, ReminderStatus


@dataclass(frozen=True, slots=True)
class BriefingCounts:
    received: int
    attention: int
    urgent: int
    unanswered_urgent: int


@dataclass(frozen=True, slots=True)
class TodayBriefing:
    generated_at: datetime
    greeting: str
    narrative: str
    counts: BriefingCounts
    important_emails: list[Email]
    deadlines: list[AssistantSuggestion]
    meetings: list[AssistantSuggestion]
    suggested_replies: list[AssistantSuggestion]
    smart_actions: list[AssistantSuggestion]
    pending_follow_ups: list[AssistantSuggestion]
    risk_alerts: list[AssistantSuggestion]


class BriefingService:
    """Builds a calm, timezone-aware executive summary of the user's inbox."""

    DEADLINE_TYPES = {
        SuggestionType.DEADLINE_REMINDER,
        SuggestionType.GOVERNMENT_DEADLINE,
        SuggestionType.VISA_REMINDER,
        SuggestionType.BILL_DUE,
        SuggestionType.PAYMENT_REMINDER,
    }
    MEETING_TYPES = {
        SuggestionType.MEETING_REMINDER,
        SuggestionType.INTERVIEW_REMINDER,
        SuggestionType.HOSPITAL_APPOINTMENT,
        SuggestionType.CALENDAR_EVENT,
    }
    REPLY_TYPES = {SuggestionType.REPLY_SUGGESTION}
    FOLLOW_UP_TYPES = {SuggestionType.FOLLOW_UP_REMINDER}
    RISK_TYPES = {SuggestionType.PHISHING_WARNING, SuggestionType.SPAM_WARNING}

    def __init__(self, repository: BriefingRepository | None = None) -> None:
        self.repository = repository or BriefingRepository()

    @staticmethod
    def _timezone(name: str) -> ZoneInfo:
        try:
            return ZoneInfo(name)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")

    @staticmethod
    def _greeting(local_hour: int, language: str) -> str:
        if language.lower().startswith("so"):
            if local_hour < 12:
                return "Subax wanaagsan."
            if local_hour < 18:
                return "Galab wanaagsan."
            return "Habeen wanaagsan."
        if local_hour < 12:
            return "Good morning."
        if local_hour < 18:
            return "Good afternoon."
        return "Good evening."

    @staticmethod
    def _narrative(
        counts: BriefingCounts,
        suggestions: list[AssistantSuggestion],
        language: str,
        reminders: list[Reminder],
        overdue_count: int,
    ) -> str:
        if language.lower().startswith("so"):
            if counts.received == 0:
                parts = ["Sanduuqa fariimahaagu waa deggan yahay."]
                if reminders:
                    parts.append(f"Waxaad leedahay {len(reminders)} xusuusin oo maanta taagan.")
                if overdue_count:
                    parts.append(f"{overdue_count} hawlood ayaa dib u dhacay.")
                if not reminders and not overdue_count:
                    parts.append("Ma jiraan wax degdeg ah.")
                return " ".join(parts)
            parts = [f"Waxaad maanta heshay {counts.received} iimayl."]
            if counts.attention:
                parts.append(f"{counts.attention} waxay u baahan yihiin dareenkaaga.")
            else:
                parts.append("Midna uma baahna tallaabo degdeg ah.")
            if suggestions:
                parts.append(f"Arrinta ugu muhiimsan waa: {suggestions[0].title}.")
            if counts.unanswered_urgent == 0:
                parts.append("Ma lihid iimaylo degdeg ah oo aan laga jawaabin.")
            if reminders:
                parts.append(f"Waxaad leedahay {len(reminders)} xusuusin oo maanta taagan.")
            if overdue_count:
                parts.append(f"{overdue_count} hawlood ayaa dib u dhacay.")
            return " ".join(parts)
        if counts.received == 0:
            parts = ["Your inbox is quiet."]
            if reminders:
                parts.append(
                    f"You have {len(reminders)} reminder{'s' if len(reminders) != 1 else ''} due today, including {reminders[0].title}."
                )
            if overdue_count:
                parts.append(f"{overdue_count} task{'s are' if overdue_count != 1 else ' is'} overdue.")
            if not reminders and not overdue_count:
                parts.append("There is nothing urgent requiring your attention.")
            return " ".join(parts)
        parts = [f"You received {counts.received} emails today."]
        if counts.attention:
            noun = "message requires" if counts.attention == 1 else "messages require"
            parts.append(f"{counts.attention} {noun} your attention.")
        else:
            parts.append("None require immediate attention.")
        if suggestions:
            parts.append(f"The highest priority item is: {suggestions[0].title}.")
        if counts.unanswered_urgent == 0:
            parts.append("You have no unanswered urgent emails.")
        if reminders:
            parts.append(f"You have {len(reminders)} reminder{'s' if len(reminders) != 1 else ''} due today, including {reminders[0].title}.")
        if overdue_count:
            parts.append(f"{overdue_count} task{'s are' if overdue_count != 1 else ' is'} overdue.")
        return " ".join(parts)

    def get_today(self, user: User, *, now: datetime | None = None) -> TodayBriefing:
        current = now or timezone.now()
        preferences, _ = UserPreference.objects.get_or_create(user=user)
        user_timezone = self._timezone(preferences.timezone)
        local_now = current.astimezone(user_timezone)
        start = datetime.combine(local_now.date(), time.min, tzinfo=user_timezone).astimezone(UTC)
        emails = self.repository.recent_emails(user, since=start)
        received = emails.count()
        attention = emails.filter(ai_summary__action_required=True).count()
        important = self.repository.important_emails(
            user,
            since=start,
            threshold=preferences.importance_threshold,
        )
        suggestions = self.repository.pending_suggestions(user, now=current)
        reminders = list(Reminder.objects.filter(user=user, status=ReminderStatus.PENDING, due_at__date=local_now.date()).order_by("due_at")[:5])
        overdue_count = Reminder.objects.filter(user=user, status=ReminderStatus.PENDING, due_at__lt=current).count()
        language = preferences.voice_language or preferences.locale
        urgent = sum(item.interruption_priority >= 90 for item in suggestions)
        counts = BriefingCounts(
            received=received,
            attention=attention,
            urgent=urgent,
            unanswered_urgent=urgent,
        )

        def of_types(types: set[str]) -> list[AssistantSuggestion]:
            return [item for item in suggestions if item.suggestion_type in types]

        reserved = (
            self.DEADLINE_TYPES
            | self.MEETING_TYPES
            | self.REPLY_TYPES
            | self.FOLLOW_UP_TYPES
            | self.RISK_TYPES
        )
        return TodayBriefing(
            generated_at=current,
            greeting=self._greeting(local_now.hour, language),
            narrative=self._narrative(counts, suggestions, language, reminders, overdue_count),
            counts=counts,
            important_emails=important,
            deadlines=of_types(self.DEADLINE_TYPES),
            meetings=of_types(self.MEETING_TYPES),
            suggested_replies=of_types(self.REPLY_TYPES),
            smart_actions=[item for item in suggestions if item.suggestion_type not in reserved],
            pending_follow_ups=of_types(self.FOLLOW_UP_TYPES),
            risk_alerts=of_types(self.RISK_TYPES),
        )
