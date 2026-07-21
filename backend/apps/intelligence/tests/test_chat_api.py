from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.intelligence.api.v1.views import AIChatView
from apps.intelligence.serializers import ChatRequestSerializer

pytestmark = pytest.mark.django_db


def test_chat_requires_authentication() -> None:
    response = APIClient().post(reverse("v1:ai:chat"), {"message": "Hello"}, format="json")
    assert response.status_code == 401


def test_chat_rejects_unbounded_history() -> None:
    serializer = ChatRequestSerializer(
        data={
            "message": "Summarize my inbox",
            "history": [{"role": "user", "content": "x"}] * 21,
        }
    )
    assert serializer.is_valid() is False
    assert "at most 20" in str(serializer.errors["history"])


def test_chat_response_matches_mobile_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    conversation_uuid = uuid4()

    class FakeChatService:
        def process_turn(self, **_: object) -> SimpleNamespace:
            return SimpleNamespace(
                conversation=SimpleNamespace(uuid=conversation_uuid),
                message="Two emails need your attention.",
                suggestions=["Show the most important one"],
            )

    monkeypatch.setattr(AIChatView, "service_class", FakeChatService)
    user = User.objects.create_user(email="chat-api@example.com")
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        reverse("v1:ai:chat"),
        {"message": "What needs my attention?", "history": []},
        format="json",
    )

    assert response.status_code == 200
    assert response.json() == {
        "conversation_uuid": str(conversation_uuid),
        "message": "Two emails need your attention.",
        "suggestions": ["Show the most important one"],
    }
