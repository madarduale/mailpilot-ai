from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.voice.serializers import VoiceTurnRequestSerializer

pytestmark = pytest.mark.django_db


def test_voice_turn_requires_authentication() -> None:
    response = APIClient().post(reverse("v1:voice:conversation-turn"), {})
    assert response.status_code == 401


def test_voice_serializer_rejects_unsupported_upload() -> None:
    serializer = VoiceTurnRequestSerializer(
        data={
            "audio": SimpleUploadedFile(
                "payload.txt",
                b"not audio",
                content_type="text/plain",
            ),
            "language": "en",
        }
    )

    assert serializer.is_valid() is False
    assert "Unsupported audio format" in str(serializer.errors["audio"])


def test_voice_turn_rejects_invalid_audio_before_provider_call() -> None:
    user = User.objects.create_user(email="voice-api@example.com")
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        reverse("v1:voice:conversation-turn"),
        {
            "audio": SimpleUploadedFile(
                "payload.txt",
                b"not audio",
                content_type="text/plain",
            )
        },
        format="multipart",
    )

    assert response.status_code == 400
