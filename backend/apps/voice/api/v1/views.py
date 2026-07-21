from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema
from openai import OpenAIError
from rest_framework.exceptions import APIException, AuthenticationFailed
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.voice.serializers import VoiceTurnRequestSerializer, VoiceTurnResponseSerializer
from apps.voice.services import VoiceAssistantService


class VoiceProviderUnavailable(APIException):
    status_code = 503
    default_detail = "Voice processing is temporarily unavailable."
    default_code = "voice_provider_unavailable"


class VoiceConversationTurnView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)
    service_class = VoiceAssistantService

    @extend_schema(
        tags=("Voice Assistant",),
        operation_id="voice_conversation_turn",
        summary="Process one voice conversation turn",
        description=(
            "Transcribes a bounded audio upload, answers with proactive inbox context and "
            "conversation history, persists the turn, and returns synthesized speech."
        ),
        request=VoiceTurnRequestSerializer,
        responses={
            200: VoiceTurnResponseSerializer,
            400: OpenApiResponse(description="Invalid audio upload."),
            503: OpenApiResponse(description="Voice provider unavailable."),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = VoiceTurnRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not isinstance(user, User):
            raise AuthenticationFailed
        audio = serializer.validated_data["audio"]
        try:
            result = self.service_class().process_turn(
                user=user,
                audio_file=audio.file,
                filename=audio.name,
                content_type=audio.content_type,
                language=serializer.validated_data["language"],
                conversation_uuid=(
                    str(serializer.validated_data["conversation_uuid"])
                    if serializer.validated_data.get("conversation_uuid")
                    else None
                ),
            )
        except OpenAIError as exc:
            raise VoiceProviderUnavailable from exc

        audio_url = (
            request.build_absolute_uri(f"/media/{result.response_audio_path}")
            if result.response_audio_path
            else None
        )
        payload = {
            "conversation_uuid": result.conversation.uuid,
            "transcript": result.transcript,
            "response_text": result.response_text,
            "response_audio_url": audio_url,
            "suggestions": result.suggestions,
        }
        return Response(VoiceTurnResponseSerializer(payload).data)
