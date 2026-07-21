from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.email_accounts.models import EmailAccount
from apps.emails.models import Email
from apps.intelligence.models import AICategory, AISummary
from apps.preferences.models import UserPreference
from apps.proactive_assistant.enums import SuggestedAction, SuggestionStatus
from apps.proactive_assistant.models import AssistantMemory, AssistantSuggestion
from apps.proactive_assistant.services import ProactiveAssistantService
from apps.reminders.models import Reminder

pytestmark = pytest.mark.django_db


def setup_analyzed_email(suffix: str = "api") -> tuple[User, Email]:
    user = User.objects.create_user(email=f"{suffix}@example.com")
    UserPreference.objects.create(user=user, importance_threshold=70, timezone="UTC")
    account = EmailAccount.objects.create(
        user=user,
        provider_account_id=f"provider-{suffix}",
        email_address=user.email,
        access_token_encrypted="encrypted",
    )
    email = Email.objects.create(
        account=account,
        provider_message_id=f"message-{suffix}",
        thread_id=f"thread-{suffix}",
        subject="Government form due tomorrow",
        sender="office@example.gov",
        recipients=[user.email],
        body="Submit the form by tomorrow.",
        received_at=timezone.now(),
    )
    category = AICategory.objects.create(
        name=f"Government {suffix}",
        slug=f"government-{suffix}",
    )
    AISummary.objects.create(
        email=email,
        category=category,
        summary="An official form is due tomorrow.",
        importance_score=94,
        sender_priority=90,
        action_required=True,
        deadline=timezone.now() + timedelta(days=1),
        phishing_score=4,
        confidence=Decimal("0.9800"),
        reasoning="Official sender and explicit deadline.",
        model_name="test-model",
        prompt_version="v1",
        processed_at=timezone.now(),
    )
    return user, email


def authenticated_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_assistant_endpoints_require_authentication() -> None:
    client = APIClient()

    assert client.get(reverse("v1:assistant:today-briefing")).status_code == 401
    assert client.get(reverse("v1:assistant:suggestion-list")).status_code == 401
    assert client.get(reverse("v1:assistant:history-list")).status_code == 401


def test_generate_list_and_briefing_are_user_scoped() -> None:
    user, email = setup_analyzed_email("owner")
    other, other_email = setup_analyzed_email("other")
    ProactiveAssistantService().evaluate_email(other_email)
    client = authenticated_client(user)

    generated = client.post(
        reverse("v1:assistant:recommendation-generate"),
        {"email_uuid": str(email.uuid)},
        format="json",
    )
    suggestions = client.get(reverse("v1:assistant:suggestion-list"))
    briefing = client.get(reverse("v1:assistant:today-briefing"))

    assert generated.status_code == status.HTTP_200_OK
    assert generated.json()["should_suggest"] is True
    assert suggestions.status_code == status.HTTP_200_OK
    assert suggestions.json()["count"] == 1
    body = briefing.json()
    assert body["counts"] == {
        "received": 1,
        "attention": 1,
        "urgent": 1,
        "unanswered_urgent": 1,
    }
    assert len(body["important_emails"]) == 1
    assert len(body["deadlines"]) == 1
    assert other.email not in str(body)


def test_accept_executes_action_and_records_history() -> None:
    user, email = setup_analyzed_email("accept")
    _, suggestion = ProactiveAssistantService().evaluate_email(email)
    assert suggestion is not None
    client = authenticated_client(user)

    response = client.post(
        reverse(
            "v1:assistant:suggestion-accept",
            kwargs={"suggestion_uuid": suggestion.uuid},
        )
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["suggestion"]["status"] == SuggestionStatus.ACCEPTED
    assert response.json()["action_result"]["status"] == "reminder_created"
    assert Reminder.objects.filter(user=user, email=email).count() == 1
    assert suggestion.history.filter(event="accepted").exists()


def test_dismiss_twice_creates_suppression_memory() -> None:
    user, email = setup_analyzed_email("dismiss")
    _, first = ProactiveAssistantService().evaluate_email(email)
    assert first is not None
    client = authenticated_client(user)
    url = reverse(
        "v1:assistant:suggestion-dismiss",
        kwargs={"suggestion_uuid": first.uuid},
    )
    assert client.post(url, {"reason": "Not useful"}, format="json").status_code == 200

    second = AssistantSuggestion.objects.create(
        user=user,
        email=email,
        suggestion_type=first.suggestion_type,
        recommended_action=SuggestedAction.CREATE_REMINDER,
        interruption_priority=80,
        title="Same kind of reminder",
        message="Would you like a reminder?",
        reason="Same semantic recommendation.",
        semantic_key=first.semantic_key,
        deduplication_key="second-occurrence",
    )
    second_url = reverse(
        "v1:assistant:suggestion-dismiss",
        kwargs={"suggestion_uuid": second.uuid},
    )
    assert client.post(second_url, {}, format="json").status_code == 200

    memory = AssistantMemory.objects.get(
        user=user,
        namespace="suggestion_suppression",
        key=first.semantic_key,
    )
    assert memory.value["suppressed"] is True
    assert memory.evidence_count == 2


def test_user_cannot_act_on_another_users_suggestion() -> None:
    owner, email = setup_analyzed_email("secure-owner")
    intruder = User.objects.create_user(email="intruder@example.com")
    _, suggestion = ProactiveAssistantService().evaluate_email(email)
    assert suggestion is not None

    response = authenticated_client(intruder).post(
        reverse(
            "v1:assistant:suggestion-accept",
            kwargs={"suggestion_uuid": suggestion.uuid},
        )
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    suggestion.refresh_from_db()
    assert suggestion.status == SuggestionStatus.PENDING
