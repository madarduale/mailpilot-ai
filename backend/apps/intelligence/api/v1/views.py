from __future__ import annotations

import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from openai import OpenAIError
from rest_framework.exceptions import APIException, AuthenticationFailed, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.intelligence.serializers import ChatRequestSerializer, ChatResponseSerializer
from apps.intelligence.services import (
    AIChatService,
    ChatConversationNotFoundError,
    ChatEmailNotFoundError,
    EmptyAIResponseError,
)

logger = logging.getLogger(__name__)


class AIProviderUnavailable(APIException):
    status_code = 503
    default_detail = "The AI assistant is temporarily unavailable."
    default_code = "ai_provider_unavailable"


class AIChatView(APIView):
    permission_classes = (IsAuthenticated,)
    service_class = AIChatService

    @extend_schema(
        tags=("AI Assistant",),
        operation_id="ai_chat_turn",
        summary="Send a text message to the inbox assistant",
        description=(
            "Answers using only the authenticated user's recent inbox, optional email context, "
            "today's briefing, and persisted conversation history."
        ),
        request=ChatRequestSerializer,
        responses={
            200: ChatResponseSerializer,
            400: OpenApiResponse(description="Invalid chat request."),
            404: OpenApiResponse(description="Conversation or email not found."),
            503: OpenApiResponse(description="AI provider unavailable."),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not isinstance(user, User):
            raise AuthenticationFailed
        values = serializer.validated_data
        try:
            result = self.service_class().process_turn(
                user=user,
                message=values["message"],
                history=values["history"],
                conversation_uuid=(
                    str(values["conversation_uuid"])
                    if values.get("conversation_uuid")
                    else None
                ),
                email_uuid=str(values["email_uuid"]) if values.get("email_uuid") else None,
            )
        except (ChatConversationNotFoundError, ChatEmailNotFoundError) as exc:
            raise NotFound("The requested chat context was not found.") from exc
        except (OpenAIError, EmptyAIResponseError, ValueError) as exc:
            logger.warning("AI chat provider request failed", exc_info=True)
            raise AIProviderUnavailable from exc

        payload = {
            "conversation_uuid": result.conversation.uuid,
            "message": result.message,
            "suggestions": result.suggestions,
        }
        return Response(ChatResponseSerializer(payload).data)
