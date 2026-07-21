from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.email_accounts.models import EmailAccount
from apps.emails.models import Email
from apps.intelligence.services import (
    AIChatService,
    ChatConversationNotFoundError,
    ChatEmailNotFoundError,
)

pytestmark = pytest.mark.django_db


class FakeGateway:
    def __init__(self) -> None:
        self.input_text = ""
        self.instructions = ""

    def respond(self, *, instructions: str, input_text: str, safety_identifier: str) -> str:
        assert safety_identifier
        self.instructions = instructions
        self.input_text = input_text
        return "Your latest email asks you to submit the report tomorrow."


def create_email(user: User, suffix: str) -> Email:
    account = EmailAccount.objects.create(
        user=user,
        provider_account_id=f"provider-{suffix}",
        email_address=user.email,
        access_token_encrypted="encrypted",
    )
    return Email.objects.create(
        account=account,
        provider_message_id=f"message-{suffix}",
        thread_id=f"thread-{suffix}",
        subject="Quarterly report due tomorrow",
        sender="manager@example.com",
        recipients=[user.email],
        body="Please submit the report tomorrow.",
        snippet="Please submit the report tomorrow.",
        received_at=timezone.now() - timedelta(minutes=5),
    )


def test_chat_uses_scoped_inbox_context_and_persists_history() -> None:
    user = User.objects.create_user(email="chat-service@example.com")
    email = create_email(user, "owner")
    gateway = FakeGateway()
    service = AIChatService(gateway=gateway)

    result = service.process_turn(
        user=user,
        message="What does my latest email need?",
        history=[],
        email_uuid=str(email.uuid),
    )

    result.conversation.refresh_from_db()
    assert result.message.startswith("Your latest email")
    assert result.conversation.context["channel"] == "text"
    assert result.conversation.context["email_uuid"] == str(email.uuid)
    assert [item["role"] for item in result.conversation.messages] == ["user", "assistant"]
    assert "Quarterly report due tomorrow" in gateway.input_text
    assert "untrusted data" in gateway.instructions


def test_chat_rejects_another_users_email_and_conversation() -> None:
    owner = User.objects.create_user(email="chat-owner@example.com")
    intruder = User.objects.create_user(email="chat-intruder@example.com")
    email = create_email(owner, "private")
    service = AIChatService(gateway=FakeGateway())
    conversation = service.process_turn(
        user=owner,
        message="Hello",
        history=[],
    ).conversation

    with pytest.raises(ChatEmailNotFoundError):
        service.process_turn(
            user=intruder,
            message="Show it",
            history=[],
            email_uuid=str(email.uuid),
        )
    with pytest.raises(ChatConversationNotFoundError):
        service.process_turn(
            user=intruder,
            message="Continue",
            history=[],
            conversation_uuid=str(conversation.uuid),
        )
