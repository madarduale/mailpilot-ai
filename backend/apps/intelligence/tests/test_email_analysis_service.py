from __future__ import annotations

import json

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.email_accounts.models import EmailAccount
from apps.emails.models import Email
from apps.intelligence.services import AIEmailAnalysisService

pytestmark = pytest.mark.django_db


class AnalysisGateway:
    def respond(self, **_: object) -> str:
        return json.dumps(
            {
                "summary": "A report is due tomorrow.",
                "importance_score": 91,
                "category": "Work",
                "action_required": True,
                "deadline": "2026-07-21T17:00:00Z",
                "meeting_date": None,
                "phishing_score": 3,
                "confidence": 0.96,
                "reasoning": "The sender states an explicit deadline.",
            }
        )


def test_analysis_is_validated_and_persisted() -> None:
    user = User.objects.create_user(email="analysis@example.com")
    account = EmailAccount.objects.create(
        user=user,
        provider_account_id="analysis-provider",
        email_address=user.email,
        access_token_encrypted="encrypted",
    )
    email = Email.objects.create(
        account=account,
        provider_message_id="analysis-message",
        thread_id="analysis-thread",
        subject="Report deadline",
        sender="manager@example.com",
        recipients=[user.email],
        body="Please send the report tomorrow.",
        received_at=timezone.now(),
    )

    analysis = AIEmailAnalysisService(gateway=AnalysisGateway()).analyze(email)

    assert analysis.importance_score == 91
    assert analysis.action_required is True
    assert analysis.deadline is not None
    assert analysis.category.slug == "system-work"
