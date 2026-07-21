from __future__ import annotations

import logging
from typing import BinaryIO

import httpx
from django.conf import settings
from openai import OpenAI, OpenAIError

logger = logging.getLogger(__name__)


class OpenAIVoiceGateway:
    """Narrow provider boundary for transcription, Responses, and speech APIs."""

    def __init__(
        self,
        text_client: OpenAI | None = None,
        audio_client: OpenAI | None = None,
    ) -> None:
        timeout = httpx.Timeout(
            settings.AI_READ_TIMEOUT_SECONDS,
            connect=settings.AI_CONNECT_TIMEOUT_SECONDS,
            write=settings.AI_WRITE_TIMEOUT_SECONDS,
        )
        self.text_client = text_client or self._build_text_client(timeout)
        self.audio_client = audio_client or self._build_audio_client(timeout)

    @staticmethod
    def _build_text_client(timeout: httpx.Timeout) -> OpenAI:
        if settings.AI_TEXT_PROVIDER == "openrouter":
            headers = {"X-OpenRouter-Title": settings.OPENROUTER_APP_TITLE}
            if settings.OPENROUTER_HTTP_REFERER:
                headers["HTTP-Referer"] = settings.OPENROUTER_HTTP_REFERER
            return OpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url=settings.OPENROUTER_BASE_URL,
                default_headers=headers,
                timeout=timeout,
                max_retries=settings.AI_MAX_RETRIES,
            )
        if settings.AI_TEXT_PROVIDER == "openai":
            return OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                timeout=timeout,
                max_retries=settings.AI_MAX_RETRIES,
            )
        raise ValueError(f"Unsupported AI_TEXT_PROVIDER: {settings.AI_TEXT_PROVIDER}")

    @staticmethod
    def _build_audio_client(timeout: httpx.Timeout) -> OpenAI:
        if settings.AI_AUDIO_PROVIDER == "openrouter":
            headers = {"X-OpenRouter-Title": settings.OPENROUTER_APP_TITLE}
            if settings.OPENROUTER_HTTP_REFERER:
                headers["HTTP-Referer"] = settings.OPENROUTER_HTTP_REFERER
            return OpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url=settings.OPENROUTER_BASE_URL,
                default_headers=headers,
                timeout=timeout,
                max_retries=settings.AI_MAX_RETRIES,
            )
        if settings.AI_AUDIO_PROVIDER == "openai":
            return OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                timeout=timeout,
                max_retries=settings.AI_MAX_RETRIES,
            )
        raise ValueError(f"Unsupported AI_AUDIO_PROVIDER: {settings.AI_AUDIO_PROVIDER}")

    def transcribe(
        self,
        *,
        file: BinaryIO,
        filename: str,
        content_type: str,
        language: str,
    ) -> str:
        model = (
            settings.OPENROUTER_TRANSCRIPTION_MODEL
            if settings.AI_AUDIO_PROVIDER == "openrouter"
            else settings.OPENAI_TRANSCRIPTION_MODEL
        )
        result = self.audio_client.audio.transcriptions.create(
            model=model,
            file=(filename, file, content_type),
            language=language or None,
            prompt="MailPilot AI email assistant conversation.",
        )
        return result.text.strip()

    def respond(self, *, instructions: str, input_text: str, safety_identifier: str) -> str:
        model = (
            settings.OPENROUTER_RESPONSES_MODEL
            if settings.AI_TEXT_PROVIDER == "openrouter"
            else settings.OPENAI_RESPONSES_MODEL
        )
        request: dict[str, object] = {
            "model": model,
            "instructions": instructions,
            "input": input_text,
            "reasoning": {"effort": "low"},
            "max_output_tokens": settings.AI_MAX_OUTPUT_TOKENS,
        }
        if settings.AI_TEXT_PROVIDER == "openai":
            request["text"] = {"verbosity": "low"}
            request["safety_identifier"] = safety_identifier
        response = self.text_client.responses.create(
            **request,  # type: ignore[arg-type]
        )
        return response.output_text.strip()

    def synthesize(self, *, text: str, voice: str) -> bytes:
        models = [settings.OPENAI_TTS_MODEL]
        provider_voice = (
            settings.OPENROUTER_TTS_VOICE
            if settings.AI_AUDIO_PROVIDER == "openrouter"
            else voice
        )
        if settings.AI_AUDIO_PROVIDER == "openrouter":
            models = list(
                dict.fromkeys(
                    [
                        settings.OPENROUTER_TTS_MODEL,
                        *settings.OPENROUTER_TTS_FALLBACK_MODELS,
                    ]
                )
            )

        last_error: OpenAIError | None = None
        for model in models:
            try:
                response = self.audio_client.audio.speech.create(
                    model=model,
                    voice=provider_voice,
                    input=text,
                    response_format="mp3",
                )
                if hasattr(response, "read"):
                    return response.read()
                return bytes(response.content)
            except OpenAIError as exc:
                last_error = exc
                logger.warning(
                    "Voice synthesis model failed",
                    extra={"model": model, "voice": provider_voice},
                    exc_info=True,
                )

        if last_error is not None:
            raise last_error
        raise ValueError("No speech synthesis model configured.")
