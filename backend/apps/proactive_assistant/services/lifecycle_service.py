from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.proactive_assistant.enums import (
    BehaviorType,
    FeedbackType,
    HistoryEvent,
    SuggestedAction,
    SuggestionStatus,
)
from apps.proactive_assistant.models import AssistantSuggestion, SuggestionHistory
from apps.reminders.models import Reminder

from .exceptions import SuggestionNotActionableError, SuggestionNotFoundError
from .learning_service import AssistantLearningService


@dataclass(frozen=True, slots=True)
class SuggestionActionResult:
    suggestion: AssistantSuggestion
    action_result: dict[str, Any]


class SuggestionLifecycleService:
    """Owns acceptance, dismissal, audit history, and safe action execution."""

    def __init__(self, learning_service: AssistantLearningService | None = None) -> None:
        self.learning_service = learning_service or AssistantLearningService()

    @staticmethod
    def _locked_suggestion(user: User, suggestion_uuid: str) -> AssistantSuggestion:
        try:
            # `email` and `ai_summary` are optional relationships, so eager
            # loading them produces LEFT OUTER JOINs. PostgreSQL cannot apply
            # FOR UPDATE to the nullable side of those joins. Lock the
            # suggestion first; related objects are loaded lazily if an action
            # needs them.
            return AssistantSuggestion.objects.select_for_update().get(
                user=user,
                uuid=suggestion_uuid,
            )
        except AssistantSuggestion.DoesNotExist as exc:
            raise SuggestionNotFoundError from exc

    @staticmethod
    def _ensure_actionable(suggestion: AssistantSuggestion) -> None:
        if suggestion.status not in (SuggestionStatus.PENDING, SuggestionStatus.SHOWN):
            raise SuggestionNotActionableError(
                f"Suggestion is already {suggestion.get_status_display().lower()}."
            )
        if suggestion.expires_at and suggestion.expires_at <= timezone.now():
            suggestion.status = SuggestionStatus.EXPIRED
            suggestion.save(update_fields=("status", "updated_at"))
            raise SuggestionNotActionableError("Suggestion has expired.")

    @transaction.atomic
    def dismiss(
        self,
        *,
        user: User,
        suggestion_uuid: str,
        reason: str = "",
    ) -> AssistantSuggestion:
        suggestion = self._locked_suggestion(user, suggestion_uuid)
        self._ensure_actionable(suggestion)
        suggestion.status = SuggestionStatus.DISMISSED
        suggestion.acted_at = timezone.now()
        suggestion.save(update_fields=("status", "acted_at", "updated_at"))
        self.learning_service.record_feedback(
            suggestion=suggestion,
            feedback_type=FeedbackType.DISMISSED,
            comment=reason,
        )
        SuggestionHistory.objects.create(
            suggestion=suggestion,
            user=user,
            event=HistoryEvent.DISMISSED,
            channel=suggestion.delivery_method,
            details={"reason": reason},
        )
        return suggestion

    @transaction.atomic
    def accept(self, *, user: User, suggestion_uuid: str) -> SuggestionActionResult:
        suggestion = self._locked_suggestion(user, suggestion_uuid)
        self._ensure_actionable(suggestion)
        result = self._execute_action(suggestion)
        suggestion.status = SuggestionStatus.ACCEPTED
        suggestion.acted_at = timezone.now()
        suggestion.action_payload = {**suggestion.action_payload, **result}
        suggestion.save(
            update_fields=("status", "acted_at", "action_payload", "updated_at")
        )
        self.learning_service.record_feedback(
            suggestion=suggestion,
            feedback_type=FeedbackType.ACCEPTED,
        )
        if suggestion.email is not None:
            behavior_type = None
            if suggestion.recommended_action == SuggestedAction.ARCHIVE:
                behavior_type = BehaviorType.EMAIL_ARCHIVED
            elif suggestion.recommended_action in (
                SuggestedAction.REPLY,
                SuggestedAction.GENERATE_REPLY,
            ):
                behavior_type = BehaviorType.EMAIL_REPLIED
            if behavior_type is not None:
                self.learning_service.record_behavior(
                    user=user,
                    behavior_type=behavior_type,
                    email=suggestion.email,
                    target=suggestion.email.sender.lower(),
                    context={"suggestion_type": suggestion.suggestion_type},
                )
        SuggestionHistory.objects.create(
            suggestion=suggestion,
            user=user,
            event=HistoryEvent.ACCEPTED,
            channel=suggestion.delivery_method,
            details=result,
        )
        return SuggestionActionResult(suggestion=suggestion, action_result=result)

    @staticmethod
    def _execute_action(suggestion: AssistantSuggestion) -> dict[str, Any]:
        email = suggestion.email
        action = suggestion.recommended_action
        if action == SuggestedAction.CREATE_REMINDER:
            due_at = timezone.now() + timedelta(days=1)
            if email is not None:
                due_at = email.ai_summary.deadline or email.ai_summary.meeting_date or due_at
            reminder = Reminder.objects.create(
                user=suggestion.user,
                email=email,
                title=suggestion.title,
                description=suggestion.reason,
                due_at=due_at,
                source="proactive_assistant",
            )
            return {"status": "reminder_created", "reminder_uuid": str(reminder.uuid)}
        if action == SuggestedAction.ARCHIVE and email is not None:
            email.labels = list(dict.fromkeys([*email.labels, "ARCHIVED_BY_MAILPILOT"]))
            email.save(update_fields=("labels", "updated_at"))
            return {"status": "email_archived", "email_uuid": str(email.uuid)}
        if action == SuggestedAction.MARK_IMPORTANT and email is not None:
            email.is_starred = True
            email.save(update_fields=("is_starred", "updated_at"))
            return {"status": "email_marked_important", "email_uuid": str(email.uuid)}
        if action in (SuggestedAction.REPLY, SuggestedAction.GENERATE_REPLY):
            sender_name = email.sender_name if email and email.sender_name else "there"
            draft = (
                f"Hi {sender_name},\n\nThank you for your message. "
                "I’ll review this and respond shortly.\n\nBest,"
            )
            return {"status": "reply_drafted", "draft": draft}
        if action == SuggestedAction.ADD_TO_CALENDAR and email is not None:
            return {
                "status": "calendar_event_ready",
                "title": email.subject,
                "starts_at": (
                    email.ai_summary.meeting_date.isoformat()
                    if email.ai_summary.meeting_date
                    else None
                ),
            }
        return {"status": "action_ready", "action": action}
