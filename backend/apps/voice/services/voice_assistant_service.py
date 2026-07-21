from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import BinaryIO

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from openai import OpenAIError

from apps.accounts.models import User
from apps.preferences.models import UserPreference
from apps.proactive_assistant.services import BriefingService
from apps.voice.integrations import OpenAIVoiceGateway
from apps.voice.models import VoiceConversation

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class VoiceTurnResult:
    conversation: VoiceConversation
    transcript: str
    response_text: str
    response_audio_path: str | None
    suggestions: list[str]


class VoiceAssistantService:
    """Runs one secure voice turn with proactive inbox context and history."""

    GREETINGS = {
        "good morning",
        "good afternoon",
        "good evening",
        "hello",
        "hi",
        "subax wanaagsan",
        "galab wanaagsan",
        "habeen wanaagsan",
    }

    def __init__(
        self,
        gateway: OpenAIVoiceGateway | None = None,
        briefing_service: BriefingService | None = None,
    ) -> None:
        self.gateway = gateway or OpenAIVoiceGateway()
        self.briefing_service = briefing_service or BriefingService()

    def process_turn(
        self,
        *,
        user: User,
        audio_file: BinaryIO,
        filename: str,
        content_type: str,
        language: str,
        conversation_uuid: str | None = None,
    ) -> VoiceTurnResult:
        conversation = self._conversation(user, conversation_uuid, language)
        transcript = self.gateway.transcribe(
            file=audio_file,
            filename=filename,
            content_type=content_type,
            language=language,
        )
        briefing = self.briefing_service.get_today(user)
        if self._is_greeting(transcript):
            question = (
                "Ma jeclaan lahayd inaan wax walba kuu soo koobo?"
                if language.lower().startswith("so")
                else "Would you like me to summarize everything?"
            )
            response_text = f"{briefing.greeting} {briefing.narrative} {question}"
        else:
            response_text = self.gateway.respond(
                instructions=(
                    "You are MailPilot, a calm executive email assistant. Be concise and "
                    "conversational. Use the inbox briefing and conversation history. Explain "
                    "why you recommend an action. Never claim an external action was completed "
                    "unless the supplied context says it was completed."
                ),
                input_text=self._response_input(transcript, briefing.narrative, conversation),
                safety_identifier=hashlib.sha256(str(user.uuid).encode()).hexdigest(),
            )
        preferences, _ = UserPreference.objects.get_or_create(user=user)
        audio_path: str | None = None
        try:
            audio_bytes = self.gateway.synthesize(text=response_text, voice=preferences.tts_voice)
            audio_path = default_storage.save(
                f"voice/responses/{conversation.uuid}/{timezone.now().timestamp()}.mp3",
                ContentFile(audio_bytes),
            )
        except OpenAIError:
            # OpenRouter TTS availability varies by model/account. Preserve the
            # text turn so the client can fall back to native device speech.
            logger.warning("Voice synthesis unavailable; returning text response", exc_info=True)
        conversation.messages = [
            *conversation.messages,
            {"role": "user", "content": transcript, "created_at": timezone.now().isoformat()},
            {
                "role": "assistant",
                "content": response_text,
                "created_at": timezone.now().isoformat(),
            },
        ][-20:]
        conversation.last_interaction_at = timezone.now()
        conversation.context = {
            "last_briefing_generated_at": briefing.generated_at.isoformat(),
            "last_attention_count": briefing.counts.attention,
        }
        conversation.save(
            update_fields=("messages", "last_interaction_at", "context", "updated_at")
        )
        return VoiceTurnResult(
            conversation=conversation,
            transcript=transcript,
            response_text=response_text,
            response_audio_path=audio_path,
            suggestions=self._suggestions(briefing.counts.attention),
        )

    @staticmethod
    def _conversation(user: User, uuid: str | None, language: str) -> VoiceConversation:
        if uuid:
            try:
                return VoiceConversation.objects.get(user=user, uuid=uuid)
            except VoiceConversation.DoesNotExist:
                pass
        return VoiceConversation.objects.create(
            user=user,
            title="Inbox assistant",
            language=language,
            last_interaction_at=timezone.now(),
        )

    @classmethod
    def _is_greeting(cls, transcript: str) -> bool:
        normalized = transcript.lower().strip(" .!?,'\"")
        return normalized in cls.GREETINGS

    @staticmethod
    def _response_input(
        transcript: str,
        briefing: str,
        conversation: VoiceConversation,
    ) -> str:
        history = "\n".join(
            f"{message.get('role', 'unknown')}: {message.get('content', '')}"
            for message in conversation.messages[-10:]
        )
        return (
            f"Inbox briefing:\n{briefing}\n\nRecent conversation:\n{history}"
            f"\n\nUser:\n{transcript}"
        )

    @staticmethod
    def _suggestions(attention_count: int) -> list[str]:
        suggestions = ["Summarize my latest email", "What deadlines are coming up?"]
        if attention_count:
            suggestions.insert(0, "Summarize what needs my attention")
        return suggestions
