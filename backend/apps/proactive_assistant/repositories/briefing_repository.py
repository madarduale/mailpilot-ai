from __future__ import annotations

from datetime import datetime

from django.db.models import Q, QuerySet

from apps.accounts.models import User
from apps.emails.models import Email
from apps.proactive_assistant.enums import SuggestionStatus
from apps.proactive_assistant.models import AssistantSuggestion


class BriefingRepository:
    """Optimized user-scoped reads for the executive briefing."""

    @staticmethod
    def recent_emails(user: User, *, since: datetime) -> QuerySet[Email]:
        return Email.objects.filter(
            account__user=user,
            received_at__gte=since,
        ).select_related("ai_summary__category")

    @staticmethod
    def important_emails(
        user: User,
        *,
        since: datetime,
        threshold: int,
        limit: int = 5,
    ) -> list[Email]:
        return list(
            BriefingRepository.recent_emails(user, since=since)
            .filter(ai_summary__importance_score__gt=threshold)
            .order_by("-ai_summary__importance_score", "-received_at")[:limit]
        )

    @staticmethod
    def pending_suggestions(user: User, *, now: datetime) -> list[AssistantSuggestion]:
        return list(
            AssistantSuggestion.objects.filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=now),
                user=user,
                status__in=(SuggestionStatus.PENDING, SuggestionStatus.SHOWN),
            )
            .select_related("email")
            .order_by("-interruption_priority", "-created_at")
        )
