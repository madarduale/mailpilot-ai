from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import override_settings
from openai import OpenAIError

from apps.voice.integrations import OpenAIVoiceGateway


@override_settings(
    AI_TEXT_PROVIDER="openrouter",
    AI_AUDIO_PROVIDER="openrouter",
    OPENROUTER_RESPONSES_MODEL="openai/gpt-5.6-terra",
    OPENROUTER_TRANSCRIPTION_MODEL="openai/whisper-1",
    OPENROUTER_TTS_MODEL="x-ai/grok-voice-tts-1.0",
    OPENROUTER_TTS_FALLBACK_MODELS=["hexgrad/kokoro-82m", "mistralai/voxtral-mini-tts-2603"],
    OPENROUTER_TTS_VOICE="Eve",
    AI_MAX_OUTPUT_TOKENS=512,
)
def test_openrouter_models_are_used_for_text_transcription_and_speech() -> None:
    text_client = MagicMock()
    text_client.responses.create.return_value = SimpleNamespace(output_text="Inbox clear")
    audio_client = MagicMock()
    audio_client.audio.transcriptions.create.return_value = SimpleNamespace(text="Hello")
    audio_client.audio.speech.create.return_value = SimpleNamespace(
        read=lambda: b"mp3-audio"
    )
    gateway = OpenAIVoiceGateway(text_client=text_client, audio_client=audio_client)

    transcript = gateway.transcribe(
        file=BytesIO(b"audio"),
        filename="voice.m4a",
        content_type="audio/mp4",
        language="en",
    )
    response = gateway.respond(
        instructions="Be concise.",
        input_text="What is important?",
        safety_identifier="user-hash",
    )
    audio = gateway.synthesize(text=response, voice="alloy")

    assert transcript == "Hello"
    assert response == "Inbox clear"
    assert audio == b"mp3-audio"
    assert (
        audio_client.audio.transcriptions.create.call_args.kwargs["model"]
        == "openai/whisper-1"
    )
    assert (
        text_client.responses.create.call_args.kwargs["model"]
        == "openai/gpt-5.6-terra"
    )
    assert text_client.responses.create.call_args.kwargs["max_output_tokens"] == 512
    assert (
        audio_client.audio.speech.create.call_args.kwargs["model"]
        == "x-ai/grok-voice-tts-1.0"
    )
    assert (
        audio_client.audio.speech.create.call_args.kwargs["voice"]
        == "Eve"
    )


@override_settings(
    AI_AUDIO_PROVIDER="openrouter",
    OPENROUTER_TTS_MODEL="x-ai/grok-voice-tts-1.0",
    OPENROUTER_TTS_FALLBACK_MODELS=["hexgrad/kokoro-82m"],
    OPENROUTER_TTS_VOICE="Eve",
)
def test_openrouter_tts_falls_back_to_next_model() -> None:
    audio_client = MagicMock()
    audio_client.audio.speech.create.side_effect = [
        OpenAIError("primary TTS failed"),
        SimpleNamespace(read=lambda: b"fallback-mp3"),
    ]
    gateway = OpenAIVoiceGateway(text_client=MagicMock(), audio_client=audio_client)

    audio = gateway.synthesize(text="Hello", voice="alloy")

    assert audio == b"fallback-mp3"
    assert [call.kwargs["model"] for call in audio_client.audio.speech.create.call_args_list] == [
        "x-ai/grok-voice-tts-1.0",
        "hexgrad/kokoro-82m",
    ]
