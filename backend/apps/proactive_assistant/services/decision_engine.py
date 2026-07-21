from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.utils import timezone

from apps.emails.models import Email
from apps.intelligence.models import AISummary
from apps.preferences.models import UserPreference
from apps.proactive_assistant.enums import (
    DeliveryMethod,
    FeedbackType,
    SuggestedAction,
    SuggestionType,
)
from apps.proactive_assistant.repositories import SuggestionRepository


@dataclass(frozen=True, slots=True)
class DecisionContext:
    """External context available to the deterministic decision layer."""

    now: datetime
    conversation_history: tuple[str, ...] = ()
    calendar_events: tuple[dict[str, object], ...] = ()
    interaction_mode: Literal["background", "foreground", "voice"] = "background"


@dataclass(frozen=True, slots=True)
class ProactiveDecision:
    should_suggest: bool
    suggestion_type: str = ""
    recommended_action: str = SuggestedAction.NONE
    delivery_method: str = DeliveryMethod.NONE
    interruption_priority: int = 0
    title: str = ""
    message: str = ""
    reason: str = ""
    semantic_key: str = ""
    deduplication_key: str = ""


class ProactiveDecisionEngine:
    """Explainable first-pass ranking before optional generative personalization."""

    MAX_INTERRUPTIONS_PER_DAY = 4
    DISMISSAL_SUPPRESSION_COUNT = 2

    def __init__(self, repository: SuggestionRepository | None = None) -> None:
        self.repository = repository or SuggestionRepository()

    @staticmethod
    def _timezone(name: str) -> ZoneInfo:
        try:
            return ZoneInfo(name)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")

    @classmethod
    def _in_quiet_hours(cls, preferences: UserPreference, now: datetime) -> bool:
        if not preferences.quiet_hours_enabled:
            return False
        if preferences.quiet_hours_start is None or preferences.quiet_hours_end is None:
            return False

        local_now = now.astimezone(cls._timezone(preferences.timezone)).time()
        start: time = preferences.quiet_hours_start
        end: time = preferences.quiet_hours_end
        if start <= end:
            return start <= local_now < end
        return local_now >= start or local_now < end

    @staticmethod
    def _classification(analysis: AISummary) -> tuple[str, str, str]:
        slug = analysis.category.slug.lower()
        if analysis.phishing_score >= 70:
            return (
                SuggestionType.PHISHING_WARNING,
                SuggestedAction.REVIEW_SECURITY,
                "This message has a high phishing risk score.",
            )
        if analysis.meeting_date and not any(
            token in slug
            for token in (
                "interview",
                "hospital",
                "medical",
                "appointment",
                "travel",
                "flight",
                "hotel",
            )
        ):
            return (
                SuggestionType.MEETING_REMINDER,
                SuggestedAction.ADD_TO_CALENDAR,
                "The email contains a meeting date.",
            )
        if "interview" in slug:
            return (
                SuggestionType.INTERVIEW_REMINDER,
                SuggestedAction.GENERATE_REPLY,
                "The email is an interview message that may need a timely response.",
            )
        if any(token in slug for token in ("hospital", "medical", "appointment")):
            return (
                SuggestionType.HOSPITAL_APPOINTMENT,
                SuggestedAction.ADD_TO_CALENDAR,
                "The email contains healthcare appointment information.",
            )
        if any(token in slug for token in ("travel", "flight", "hotel")):
            return (
                SuggestionType.TRAVEL_REMINDER,
                SuggestedAction.ADD_TO_CALENDAR,
                "The email contains time-sensitive travel information.",
            )
        if any(token in slug for token in ("package", "delivery", "shipment")):
            return (
                SuggestionType.PACKAGE_DELIVERY,
                SuggestedAction.CREATE_REMINDER,
                "The email contains a package delivery update.",
            )
        if "spam" in slug:
            return (
                SuggestionType.SPAM_WARNING,
                SuggestedAction.ARCHIVE,
                "The message resembles unwanted or unsolicited email.",
            )
        if any(token in slug for token in ("government", "visa")):
            suggestion_type = (
                SuggestionType.VISA_REMINDER
                if "visa" in slug
                else SuggestionType.GOVERNMENT_DEADLINE
            )
            return suggestion_type, SuggestedAction.CREATE_REMINDER, (
                "The email concerns an official deadline."
            )
        if "bill" in slug:
            return (
                SuggestionType.BILL_DUE,
                SuggestedAction.CREATE_REMINDER,
                "The email contains a bill that may be due soon.",
            )
        if any(token in slug for token in ("payment", "bank")):
            return (
                SuggestionType.PAYMENT_REMINDER,
                SuggestedAction.CREATE_REMINDER,
                "The email contains financial information that may be time-sensitive.",
            )
        if analysis.deadline:
            return (
                SuggestionType.DEADLINE_REMINDER,
                SuggestedAction.CREATE_REMINDER,
                "The email includes a deadline.",
            )
        if "follow" in slug:
            return (
                SuggestionType.FOLLOW_UP_REMINDER,
                SuggestedAction.CREATE_REMINDER,
                "This conversation may need a follow-up.",
            )
        if "task" in slug:
            return (
                SuggestionType.TASK_EXTRACTION,
                SuggestedAction.CREATE_REMINDER,
                "The message contains a task that can be tracked.",
            )
        return (
            SuggestionType.REPLY_SUGGESTION,
            SuggestedAction.GENERATE_REPLY,
            "The sender requested an action or response.",
        )

    @staticmethod
    def _semantic_key(email: Email, suggestion_type: str) -> str:
        return f"{suggestion_type}:{email.sender.lower()}:{email.thread_id}"

    @staticmethod
    def _deduplication_key(email: Email, suggestion_type: str) -> str:
        value = f"{email.uuid}:{suggestion_type}"
        return hashlib.sha256(value.encode()).hexdigest()

    def evaluate(
        self,
        email: Email,
        analysis: AISummary,
        preferences: UserPreference,
        context: DecisionContext | None = None,
    ) -> ProactiveDecision:
        now = context.now if context else timezone.now()
        interaction_mode = context.interaction_mode if context else "background"
        suggestion_type, action, reason = self._classification(analysis)
        semantic_key = self._semantic_key(email, suggestion_type)
        deduplication_key = self._deduplication_key(email, suggestion_type)
        user = email.account.user

        if self.repository.find_duplicate(user, deduplication_key) is not None:
            return ProactiveDecision(
                should_suggest=False,
                reason="Duplicate suggestion suppressed.",
            )
        if context and email.subject and any(
            email.subject.lower() in message.lower()
            for message in context.conversation_history[-10:]
        ):
            return ProactiveDecision(
                should_suggest=False,
                reason="This email was already discussed in the recent conversation.",
            )
        if self.repository.dismissal_count(user, semantic_key) >= self.DISMISSAL_SUPPRESSION_COUNT:
            return ProactiveDecision(
                should_suggest=False,
                reason="The user dismissed this kind of suggestion twice.",
            )

        score = analysis.importance_score
        if analysis.action_required:
            score = min(100, score + 10)
        if analysis.sender_priority >= 80:
            score = min(100, score + 10)
        accepted_similar = self.repository.feedback_count(
            user,
            suggestion_type,
            FeedbackType.ACCEPTED,
        )
        dismissed_similar = self.repository.feedback_count(
            user,
            suggestion_type,
            FeedbackType.DISMISSED,
        )
        score = min(100, score + min(10, accepted_similar * 2))
        if dismissed_similar > accepted_similar:
            score = max(0, score - min(10, dismissed_similar * 2))
        if analysis.phishing_score >= 70:
            score = max(score, 95)
        if analysis.deadline and analysis.deadline <= now + timedelta(hours=24):
            score = min(100, score + 15)
        if analysis.meeting_date and analysis.meeting_date <= now + timedelta(hours=24):
            score = min(100, score + 15)

        has_clear_value = (
            analysis.action_required
            or analysis.deadline is not None
            or analysis.meeting_date is not None
            or analysis.phishing_score >= 70
            or score > preferences.importance_threshold
        )
        if not has_clear_value:
            return ProactiveDecision(
                should_suggest=False,
                reason="The message does not meet the user's interruption threshold.",
            )

        delivery = DeliveryMethod.IN_APP
        is_critical_risk = analysis.phishing_score >= 85
        if interaction_mode == "voice":
            delivery = DeliveryMethod.VOICE
        elif interaction_mode == "foreground" and score > preferences.importance_threshold:
            delivery = DeliveryMethod.POPUP
        elif preferences.push_notifications_enabled and score > preferences.importance_threshold:
            delivery = DeliveryMethod.PUSH
        if self._in_quiet_hours(preferences, now) and not is_critical_risk:
            delivery = DeliveryMethod.IN_APP

        day_start = now - timedelta(hours=24)
        if (
            delivery != DeliveryMethod.IN_APP
            and self.repository.recent_interruptions(user, day_start)
            >= getattr(
                settings,
                "PROACTIVE_ASSISTANT_DAILY_LIMIT",
                self.MAX_INTERRUPTIONS_PER_DAY,
            )
            and not is_critical_risk
        ):
            delivery = DeliveryMethod.IN_APP

        subject = email.subject or "this message"
        message = f"{analysis.summary} Would you like me to {action.replace('_', ' ')}?"
        return ProactiveDecision(
            should_suggest=True,
            suggestion_type=suggestion_type,
            recommended_action=action,
            delivery_method=delivery,
            interruption_priority=score,
            title=subject,
            message=message,
            reason=reason,
            semantic_key=semantic_key,
            deduplication_key=deduplication_key,
        )
