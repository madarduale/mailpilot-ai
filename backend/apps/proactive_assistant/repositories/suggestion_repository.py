from __future__ import annotations

from datetime import datetime

from django.db.models import Q, QuerySet

from apps.accounts.models import User
from apps.proactive_assistant.enums import FeedbackType, SuggestionStatus
from apps.proactive_assistant.models import AssistantSuggestion, SuggestionFeedback


class SuggestionRepository:
    """User-scoped persistence and anti-fatigue queries for suggestions."""

    @staticmethod
    def find_duplicate(user: User, deduplication_key: str) -> AssistantSuggestion | None:
        return AssistantSuggestion.objects.filter(
            user=user,
            deduplication_key=deduplication_key,
        ).first()

    @staticmethod
    def dismissal_count(user: User, semantic_key: str) -> int:
        return SuggestionFeedback.objects.filter(
            user=user,
            feedback_type=FeedbackType.DISMISSED,
            suggestion__semantic_key=semantic_key,
        ).count()

    @staticmethod
    def feedback_count(user: User, suggestion_type: str, feedback_type: str) -> int:
        return SuggestionFeedback.objects.filter(
            user=user,
            feedback_type=feedback_type,
            suggestion__suggestion_type=suggestion_type,
        ).count()

    @staticmethod
    def recent_interruptions(user: User, since: datetime) -> int:
        return AssistantSuggestion.objects.filter(
            user=user,
            created_at__gte=since,
            status__in=(
                SuggestionStatus.PENDING,
                SuggestionStatus.SHOWN,
                SuggestionStatus.ACCEPTED,
                SuggestionStatus.COMPLETED,
            ),
        ).exclude(delivery_method="in_app").count()

    @staticmethod
    def pending_for_user(user: User, now: datetime) -> QuerySet[AssistantSuggestion]:
        return AssistantSuggestion.objects.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now),
            user=user,
            status=SuggestionStatus.PENDING,
        )
