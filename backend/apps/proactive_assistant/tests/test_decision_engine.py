from __future__ import annotations

from datetime import time, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.email_accounts.models import EmailAccount
from apps.emails.models import Email
from apps.intelligence.models import AICategory, AISummary
from apps.preferences.models import UserPreference
from apps.proactive_assistant.enums import (
    DeliveryMethod,
    FeedbackType,
    SuggestionType,
)
from apps.proactive_assistant.models import (
    AssistantSuggestion,
    SuggestionFeedback,
    SuggestionHistory,
)
from apps.proactive_assistant.services import DecisionContext, ProactiveAssistantService
from apps.proactive_assistant.services.decision_engine import ProactiveDecisionEngine

pytestmark = pytest.mark.django_db


def analyzed_email(
    *,
    importance: int = 90,
    action_required: bool = True,
    phishing_score: int = 2,
    sender_priority: int = 50,
) -> tuple[User, Email, AISummary, UserPreference]:
    user = User.objects.create_user(email=f"pilot-{User.objects.count()}@example.com")
    account = EmailAccount.objects.create(
        user=user,
        provider_account_id=f"account-{user.uuid}",
        email_address=user.email,
        access_token_encrypted="encrypted",
    )
    email = Email.objects.create(
        account=account,
        provider_message_id=f"message-{user.uuid}",
        thread_id=f"thread-{user.uuid}",
        subject="Response requested",
        sender="manager@example.com",
        recipients=[user.email],
        body="Please respond today.",
        received_at=timezone.now(),
    )
    category = AICategory.objects.create(
        name=f"Work {user.uuid}",
        slug=f"work-{user.uuid}",
    )
    analysis = AISummary.objects.create(
        email=email,
        category=category,
        summary="Your manager requested a response today.",
        importance_score=importance,
        sender_priority=sender_priority,
        action_required=action_required,
        phishing_score=phishing_score,
        confidence=Decimal("0.9500"),
        reasoning="A direct request from a known sender.",
        model_name="test-model",
        prompt_version="v1",
        processed_at=timezone.now(),
    )
    preferences = UserPreference.objects.create(
        user=user,
        importance_threshold=75,
        timezone="UTC",
    )
    return user, email, analysis, preferences


def test_engine_recommends_explainable_reply_and_uses_sender_priority() -> None:
    _, email, analysis, preferences = analyzed_email(
        importance=70,
        sender_priority=95,
    )

    decision = ProactiveDecisionEngine().evaluate(email, analysis, preferences)

    assert decision.should_suggest is True
    assert decision.suggestion_type == SuggestionType.REPLY_SUGGESTION
    assert decision.interruption_priority == 90
    assert decision.delivery_method == DeliveryMethod.PUSH
    assert decision.reason
    assert "Would you like me" in decision.message


def test_quiet_hours_downgrade_noncritical_interruptions_to_in_app() -> None:
    _, email, analysis, preferences = analyzed_email()
    preferences.quiet_hours_enabled = True
    preferences.quiet_hours_start = time(21, 0)
    preferences.quiet_hours_end = time(7, 0)
    preferences.save()
    now = timezone.now().replace(hour=23, minute=0, second=0, microsecond=0)

    decision = ProactiveDecisionEngine().evaluate(
        email,
        analysis,
        preferences,
        DecisionContext(now=now),
    )

    assert decision.should_suggest is True
    assert decision.delivery_method == DeliveryMethod.IN_APP


def test_two_dismissals_suppress_same_semantic_suggestion() -> None:
    user, email, analysis, preferences = analyzed_email()
    semantic_key = f"reply_suggestion:{email.sender}:{email.thread_id}"
    for index in range(2):
        suggestion = AssistantSuggestion.objects.create(
            user=user,
            email=email,
            suggestion_type=SuggestionType.REPLY_SUGGESTION,
            interruption_priority=80,
            title="Reply",
            message="Would you like to reply?",
            reason="Action requested.",
            deduplication_key=f"old-{index}",
            semantic_key=semantic_key,
        )
        SuggestionFeedback.objects.create(
            suggestion=suggestion,
            user=user,
            feedback_type=FeedbackType.DISMISSED,
        )

    decision = ProactiveDecisionEngine().evaluate(email, analysis, preferences)

    assert decision.should_suggest is False
    assert "twice" in decision.reason


def test_service_persists_one_suggestion_and_audit_event() -> None:
    _, email, _, _ = analyzed_email()
    service = ProactiveAssistantService()

    first_decision, suggestion = service.evaluate_email(email)
    second_decision, duplicate = service.evaluate_email(email)

    assert first_decision.should_suggest is True
    assert suggestion is not None
    assert SuggestionHistory.objects.filter(suggestion=suggestion).count() == 1
    assert second_decision.should_suggest is False
    assert duplicate is None
    assert AssistantSuggestion.objects.filter(email=email).count() == 1


def test_critical_phishing_warning_bypasses_quiet_hour_downgrade() -> None:
    _, email, analysis, preferences = analyzed_email(phishing_score=95)
    preferences.quiet_hours_enabled = True
    preferences.quiet_hours_start = time(0, 0)
    preferences.quiet_hours_end = time(23, 59)
    preferences.save()

    decision = ProactiveDecisionEngine().evaluate(
        email,
        analysis,
        preferences,
        DecisionContext(now=timezone.now() + timedelta(minutes=1)),
    )

    assert decision.suggestion_type == SuggestionType.PHISHING_WARNING
    assert decision.delivery_method == DeliveryMethod.PUSH
    assert decision.interruption_priority == 100
