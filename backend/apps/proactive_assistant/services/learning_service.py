from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.emails.models import Email
from apps.proactive_assistant.enums import BehaviorType, FeedbackType
from apps.proactive_assistant.models import (
    AssistantMemory,
    AssistantSuggestion,
    SuggestionFeedback,
    UserBehavior,
)


class AssistantLearningService:
    """Turns explicit feedback and observed actions into explainable memory."""

    SUPPRESSION_THRESHOLD = 2

    @transaction.atomic
    def record_feedback(
        self,
        *,
        suggestion: AssistantSuggestion,
        feedback_type: str,
        comment: str = "",
        metadata: dict[str, object] | None = None,
    ) -> SuggestionFeedback:
        feedback = SuggestionFeedback.objects.create(
            suggestion=suggestion,
            user=suggestion.user,
            feedback_type=feedback_type,
            comment=comment,
            metadata=metadata or {},
        )
        behavior_type = (
            BehaviorType.SUGGESTION_DISMISSED
            if feedback_type == FeedbackType.DISMISSED
            else BehaviorType.SUGGESTION_ACCEPTED
        )
        self.record_behavior(
            user=suggestion.user,
            behavior_type=behavior_type,
            email=suggestion.email,
            target=suggestion.semantic_key,
            context={"suggestion_type": suggestion.suggestion_type},
        )
        if feedback_type == FeedbackType.DISMISSED:
            self._learn_suppression(suggestion)
        return feedback

    def record_behavior(
        self,
        *,
        user: User,
        behavior_type: str,
        email: Email | None = None,
        target: str = "",
        context: dict[str, object] | None = None,
    ) -> UserBehavior:
        behavior = UserBehavior.objects.create(
            user=user,
            email=email,
            behavior_type=behavior_type,
            target=target,
            context=context or {},
        )
        self._learn_repeated_behavior(behavior)
        return behavior

    @staticmethod
    def _learn_repeated_behavior(behavior: UserBehavior) -> None:
        if not behavior.target:
            return
        evidence_count = UserBehavior.objects.filter(
            user=behavior.user,
            behavior_type=behavior.behavior_type,
            target=behavior.target,
        ).count()
        if evidence_count < 3:
            return
        confidence = min(Decimal("0.9500"), Decimal("0.5000") + Decimal(evidence_count) / 10)
        AssistantMemory.objects.update_or_create(
            user=behavior.user,
            namespace="behavior_preference",
            key=f"{behavior.behavior_type}:{behavior.target}",
            defaults={
                "value": {
                    "behavior_type": behavior.behavior_type,
                    "target": behavior.target,
                    "context": behavior.context,
                },
                "confidence": confidence,
                "evidence_count": evidence_count,
                "source": "observed_behavior",
                "is_active": True,
                "last_reinforced_at": timezone.now(),
            },
        )

    def _learn_suppression(self, suggestion: AssistantSuggestion) -> None:
        dismissals = SuggestionFeedback.objects.filter(
            user=suggestion.user,
            feedback_type=FeedbackType.DISMISSED,
            suggestion__semantic_key=suggestion.semantic_key,
        ).count()
        if dismissals < self.SUPPRESSION_THRESHOLD:
            return

        AssistantMemory.objects.update_or_create(
            user=suggestion.user,
            namespace="suggestion_suppression",
            key=suggestion.semantic_key,
            defaults={
                "value": {
                    "suppressed": True,
                    "reason": "dismissed_twice",
                    "dismissal_count": dismissals,
                },
                "confidence": Decimal("1.0000"),
                "evidence_count": dismissals,
                "source": "explicit_feedback",
                "is_active": True,
                "last_reinforced_at": timezone.now(),
            },
        )
