from __future__ import annotations

from datetime import datetime, timedelta
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
from apps.notifications.models import Notification, NotificationStatus
from apps.preferences.models import UserPreference
from apps.reminders.models import Reminder, ReminderStatus

pytestmark = pytest.mark.django_db


def create_email(account: EmailAccount, *, suffix: str, received_at: datetime) -> Email:
    return Email.objects.create(
        account=account,
        provider_message_id=f"provider-{suffix}",
        thread_id=f"thread-{suffix}",
        subject=f"Subject {suffix}",
        sender=f"{suffix}@example.com",
        sender_name=f"Sender {suffix}",
        recipients=[account.email_address],
        body="Email body",
        received_at=received_at,
    )


def analyze(
    email: Email,
    category: AICategory,
    *,
    importance: int,
    action_required: bool = False,
) -> AISummary:
    return AISummary.objects.create(
        email=email,
        category=category,
        summary=f"Summary for {email.subject}",
        importance_score=importance,
        action_required=action_required,
        phishing_score=3,
        confidence=Decimal("0.9500"),
        reasoning="The sender and requested action indicate priority.",
        model_name="test-model",
        prompt_version="v1",
        processed_at=timezone.now(),
    )


def create_account(user: User, suffix: str) -> EmailAccount:
    return EmailAccount.objects.create(
        user=user,
        provider_account_id=f"provider-account-{suffix}",
        email_address=f"{suffix}@example.com",
        access_token_encrypted="encrypted-token",
    )


def test_dashboard_requires_authentication() -> None:
    response = APIClient().get(reverse("v1:dashboard:detail"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_dashboard_returns_thresholded_user_scoped_data() -> None:
    user = User.objects.create_user(email="pilot@example.com", password="password")
    other_user = User.objects.create_user(email="other@example.com", password="password")
    account = create_account(user, "pilot")
    other_account = create_account(other_user, "other")
    UserPreference.objects.create(user=user, importance_threshold=80, timezone="UTC")
    category = AICategory.objects.create(name="Interview", slug="interview", color="#6750A4")
    now = timezone.now()

    important = create_email(account, suffix="important", received_at=now)
    analyze(important, category, importance=92, action_required=True)
    at_threshold = create_email(account, suffix="threshold", received_at=now)
    analyze(at_threshold, category, importance=80)
    yesterday = create_email(account, suffix="yesterday", received_at=now - timedelta(days=1))
    analyze(yesterday, category, importance=99, action_required=True)
    foreign = create_email(other_account, suffix="foreign", received_at=now)
    analyze(foreign, category, importance=100, action_required=True)

    Reminder.objects.create(
        user=user,
        email=important,
        title="Reply to recruiter",
        due_at=now + timedelta(hours=2),
        status=ReminderStatus.PENDING,
    )
    Reminder.objects.create(
        user=other_user,
        title="Other reminder",
        due_at=now + timedelta(hours=1),
    )
    Notification.objects.create(
        user=user,
        email=important,
        title="Interview invitation",
        body="A recruiter sent an invitation.",
        notification_type="interview",
        status=NotificationStatus.DELIVERED,
        importance_score=92,
    )
    Notification.objects.create(
        user=user,
        title="Already read",
        body="Read body",
        notification_type="general",
        status=NotificationStatus.READ,
        read_at=now,
    )

    client = APIClient()
    client.force_authenticate(user)
    response = client.get(reverse("v1:dashboard:detail"))

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["stats"] == {"important": 1, "action_required": 1, "unread": 2}
    assert body["unread_notifications"] == 1
    assert body["unread_emails"] == 3
    assert len(body["important_emails"]) == 1
    assert body["important_emails"][0]["uuid"] == str(important.uuid)
    assert body["important_emails"][0]["ai_summary"]["importance_score"] == 92
    assert body["important_emails"][0]["ai_summary"]["category"] == {
        "name": "Interview",
        "color": "#6750A4",
    }
    assert [item["title"] for item in body["reminders"]] == ["Reply to recruiter"]
    assert "1 important email" in body["briefing"]


def test_dashboard_uses_safe_defaults_without_preferences_or_messages() -> None:
    user = User.objects.create_user(email="empty@example.com", password="password")
    client = APIClient()
    client.force_authenticate(user)

    response = client.get(reverse("v1:dashboard:detail"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "briefing": (
            "Your priority inbox is clear today. MailPilot will keep watching for what matters."
        ),
        "stats": {"important": 0, "action_required": 0, "unread": 0},
        "important_emails": [],
        "reminders": [],
        "unread_notifications": 0,
        "unread_emails": 0,
    }
