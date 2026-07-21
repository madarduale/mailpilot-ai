from __future__ import annotations

from io import BytesIO

import pytest
from openai import OpenAIError

from apps.accounts.models import User
from apps.voice.models import VoiceConversation
from apps.voice.services import VoiceAssistantService
from apps.reminders.models import Reminder
from django.utils import timezone

pytestmark = pytest.mark.django_db


class FakeVoiceGateway:
    def __init__(self, transcripts: list[str]) -> None:
        self.transcripts = transcripts
        self.response_calls = 0
        self.speech: list[str] = []

    def transcribe(self, **kwargs: object) -> str:
        return self.transcripts.pop(0)

    def respond(self, **kwargs: object) -> str:
        self.response_calls += 1
        assert "Inbox briefing" in str(kwargs["input_text"])
        return "Your priority inbox is clear."

    def synthesize(self, *, text: str, voice: str) -> bytes:
        self.speech.append(text)
        assert voice == "alloy"
        return b"fake-mp3"


class FailingTTSGateway(FakeVoiceGateway):
    def synthesize(self, *, text: str, voice: str) -> bytes:
        raise OpenAIError("TTS unavailable")


def test_greeting_returns_proactive_briefing_without_model_response() -> None:
    user = User.objects.create_user(email="voice-greeting@example.com")
    gateway = FakeVoiceGateway(["Good morning"])
    service = VoiceAssistantService(gateway=gateway)  # type: ignore[arg-type]

    result = service.process_turn(
        user=user,
        audio_file=BytesIO(b"audio"),
        filename="greeting.m4a",
        content_type="audio/mp4",
        language="en",
    )

    assert result.transcript == "Good morning"
    assert result.response_text.startswith(("Good morning.", "Good afternoon.", "Good evening."))
    assert "Would you like me to summarize everything?" in result.response_text
    assert gateway.response_calls == 0
    assert result.response_audio_path is not None
    assert VoiceConversation.objects.get(uuid=result.conversation.uuid).messages[-1][
        "role"
    ] == "assistant"


def test_greeting_summary_includes_due_reminders() -> None:
    user = User.objects.create_user(email="voice-reminder@example.com")
    Reminder.objects.create(user=user, title="Interview", due_at=timezone.now())
    gateway = FakeVoiceGateway(["Good morning"])
    result = VoiceAssistantService(gateway=gateway).process_turn(user=user, audio_file=BytesIO(b"audio"), filename="voice.m4a", content_type="audio/mp4", language="en")  # type: ignore[arg-type]
    assert "Interview" in result.response_text


def test_followup_uses_conversation_history_and_responses_gateway() -> None:
    user = User.objects.create_user(email="voice-followup@example.com")
    gateway = FakeVoiceGateway(["Good morning", "What needs my attention?"])
    service = VoiceAssistantService(gateway=gateway)  # type: ignore[arg-type]
    first = service.process_turn(
        user=user,
        audio_file=BytesIO(b"audio"),
        filename="first.m4a",
        content_type="audio/mp4",
        language="en",
    )

    second = service.process_turn(
        user=user,
        audio_file=BytesIO(b"audio"),
        filename="second.m4a",
        content_type="audio/mp4",
        language="en",
        conversation_uuid=str(first.conversation.uuid),
    )

    assert second.conversation.uuid == first.conversation.uuid
    assert second.response_text == "Your priority inbox is clear."
    assert gateway.response_calls == 1
    second.conversation.refresh_from_db()
    assert len(second.conversation.messages) == 4


def test_tts_failure_keeps_voice_turn_successful() -> None:
    user = User.objects.create_user(email="voice-tts-fallback@example.com")
    gateway = FailingTTSGateway(["Good morning"])

    result = VoiceAssistantService(gateway=gateway).process_turn(
        user=user,
        audio_file=BytesIO(b"audio"),
        filename="voice.m4a",
        content_type="audio/mp4",
        language="en",
    )  # type: ignore[arg-type]

    assert result.response_text
    assert result.response_audio_path is None
    assert VoiceConversation.objects.filter(uuid=result.conversation.uuid).exists()
