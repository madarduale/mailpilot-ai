from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from apps.emails.models import Email
from apps.preferences.models import UserPreference
from apps.proactive_assistant.enums import HistoryEvent
from apps.proactive_assistant.models import AssistantSuggestion, SuggestionHistory
from apps.proactive_assistant.services.decision_engine import (
    DecisionContext,
    ProactiveDecision,
    ProactiveDecisionEngine,
)


class ProactiveAssistantService:
    """Evaluates analyzed email events and persists actionable recommendations."""

    def __init__(self, engine: ProactiveDecisionEngine | None = None) -> None:
        self.engine = engine or ProactiveDecisionEngine()

    @transaction.atomic
    def evaluate_email(
        self,
        email: Email,
        context: DecisionContext | None = None,
    ) -> tuple[ProactiveDecision, AssistantSuggestion | None]:
        analysis = email.ai_summary
        preferences, _ = UserPreference.objects.get_or_create(user=email.account.user)
        decision = self.engine.evaluate(email, analysis, preferences, context)
        if not decision.should_suggest:
            return decision, None

        suggestion = AssistantSuggestion.objects.create(
            user=email.account.user,
            email=email,
            suggestion_type=decision.suggestion_type,
            recommended_action=decision.recommended_action,
            delivery_method=decision.delivery_method,
            interruption_priority=decision.interruption_priority,
            title=decision.title,
            message=decision.message,
            reason=decision.reason,
            semantic_key=decision.semantic_key,
            deduplication_key=decision.deduplication_key,
            scheduled_for=timezone.now(),
            expires_at=self._expiry(email),
        )
        SuggestionHistory.objects.create(
            suggestion=suggestion,
            user=suggestion.user,
            event=HistoryEvent.CREATED,
            channel=suggestion.delivery_method,
            details={"reason": decision.reason},
        )
        return decision, suggestion

    def evaluate_recent_emails(
        self,
        emails: Iterable[Email],
        context: DecisionContext | None = None,
    ) -> list[tuple[ProactiveDecision, AssistantSuggestion | None]]:
        """Evaluate a batch while applying the same per-user fatigue controls."""

        return [self.evaluate_email(email, context) for email in emails]

    @staticmethod
    def _expiry(email: Email) -> datetime:
        analysis = email.ai_summary
        if analysis.deadline:
            return analysis.deadline
        if analysis.meeting_date:
            return analysis.meeting_date
        return timezone.now() + timedelta(days=7)
