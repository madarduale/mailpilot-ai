from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import filters, generics, status
from rest_framework.exceptions import AuthenticationFailed, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.emails.models import Email
from apps.proactive_assistant.models import AssistantSuggestion, SuggestionHistory
from apps.proactive_assistant.serializers import (
    AssistantSuggestionSerializer,
    ProactiveRecommendationRequestSerializer,
    ProactiveRecommendationResponseSerializer,
    SuggestionActionResponseSerializer,
    SuggestionFeedbackRequestSerializer,
    SuggestionHistorySerializer,
    TodayBriefingSerializer,
)
from apps.proactive_assistant.services import (
    BriefingService,
    ProactiveAssistantService,
    SuggestionLifecycleService,
)
from apps.proactive_assistant.services.exceptions import (
    SuggestionNotActionableError,
    SuggestionNotFoundError,
)


def authenticated_user(request: Request) -> User:
    user = request.user
    if not isinstance(user, User):
        raise AuthenticationFailed
    return user


class TodayBriefingView(APIView):
    permission_classes = (IsAuthenticated,)
    service_class = BriefingService

    @extend_schema(
        tags=("Proactive Assistant",),
        operation_id="assistant_today_briefing",
        summary="Get today's executive inbox briefing",
        description=(
            "Returns a timezone-aware narrative and prioritized sections for important "
            "emails, deadlines, meetings, replies, smart actions, follow-ups, and risks."
        ),
        responses={200: TodayBriefingSerializer},
    )
    def get(self, request: Request) -> Response:
        result = self.service_class().get_today(authenticated_user(request))
        return Response(TodayBriefingSerializer(result).data)


class SuggestionListView(generics.ListAPIView[AssistantSuggestion]):
    permission_classes = (IsAuthenticated,)
    serializer_class = AssistantSuggestionSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("title", "message", "reason")
    ordering_fields = ("created_at", "interruption_priority", "expires_at")
    ordering = ("-interruption_priority", "-created_at")
    queryset = AssistantSuggestion.objects.none()

    def get_queryset(self) -> QuerySet[AssistantSuggestion]:
        if getattr(self, "swagger_fake_view", False):
            return AssistantSuggestion.objects.none()
        queryset = AssistantSuggestion.objects.filter(
            user=authenticated_user(self.request)
        ).select_related("email")
        for field in ("status", "suggestion_type", "delivery_method"):
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset

    @extend_schema(
        tags=("Proactive Assistant",),
        operation_id="assistant_suggestions_list",
        summary="List assistant suggestions",
        description="Returns only suggestions owned by the authenticated user.",
        parameters=[
            OpenApiParameter("status", str, description="Filter by lifecycle status."),
            OpenApiParameter("suggestion_type", str, description="Filter by suggestion type."),
            OpenApiParameter("delivery_method", str, description="Filter by delivery method."),
        ],
        responses={200: AssistantSuggestionSerializer(many=True)},
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class SuggestionDismissView(APIView):
    permission_classes = (IsAuthenticated,)
    service_class = SuggestionLifecycleService

    @extend_schema(
        tags=("Proactive Assistant",),
        operation_id="assistant_suggestion_dismiss",
        summary="Dismiss a suggestion",
        description=(
            "Dismisses a user-owned suggestion, records feedback, and learns suppression "
            "after the same semantic recommendation is dismissed twice."
        ),
        request=SuggestionFeedbackRequestSerializer,
        responses={
            200: AssistantSuggestionSerializer,
            404: OpenApiResponse(description="Suggestion not found."),
            409: OpenApiResponse(description="Suggestion is no longer actionable."),
        },
    )
    def post(self, request: Request, suggestion_uuid: str) -> Response:
        serializer = SuggestionFeedbackRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            suggestion = self.service_class().dismiss(
                user=authenticated_user(request),
                suggestion_uuid=suggestion_uuid,
                reason=serializer.validated_data.get("reason", ""),
            )
        except SuggestionNotFoundError as exc:
            raise NotFound("Suggestion not found.") from exc
        except SuggestionNotActionableError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(AssistantSuggestionSerializer(suggestion).data)


class SuggestionAcceptView(APIView):
    permission_classes = (IsAuthenticated,)
    service_class = SuggestionLifecycleService

    @extend_schema(
        tags=("Proactive Assistant",),
        operation_id="assistant_suggestion_accept",
        summary="Accept and execute a suggestion",
        description=(
            "Accepts a user-owned recommendation and safely performs its contextual action, "
            "such as creating a reminder, drafting a reply, archiving, or preparing an event."
        ),
        request=None,
        responses={
            200: SuggestionActionResponseSerializer,
            404: OpenApiResponse(description="Suggestion not found."),
            409: OpenApiResponse(description="Suggestion is no longer actionable."),
        },
    )
    def post(self, request: Request, suggestion_uuid: str) -> Response:
        try:
            result = self.service_class().accept(
                user=authenticated_user(request),
                suggestion_uuid=suggestion_uuid,
            )
        except SuggestionNotFoundError as exc:
            raise NotFound("Suggestion not found.") from exc
        except SuggestionNotActionableError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        payload = {"suggestion": result.suggestion, "action_result": result.action_result}
        return Response(SuggestionActionResponseSerializer(payload).data)


class SuggestionHistoryListView(generics.ListAPIView[SuggestionHistory]):
    permission_classes = (IsAuthenticated,)
    serializer_class = SuggestionHistorySerializer
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ("occurred_at",)
    ordering = ("-occurred_at",)
    queryset = SuggestionHistory.objects.none()

    def get_queryset(self) -> QuerySet[SuggestionHistory]:
        if getattr(self, "swagger_fake_view", False):
            return SuggestionHistory.objects.none()
        queryset = SuggestionHistory.objects.filter(
            user=authenticated_user(self.request)
        ).select_related("suggestion")
        for field in ("event", "channel"):
            value = self.request.query_params.get(field)
            if value:
                queryset = queryset.filter(**{field: value})
        return queryset

    @extend_schema(
        tags=("Proactive Assistant",),
        operation_id="assistant_history_list",
        summary="List assistant history",
        description="Returns the authenticated user's paginated suggestion audit trail.",
        responses={200: SuggestionHistorySerializer(many=True)},
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class GenerateRecommendationView(APIView):
    permission_classes = (IsAuthenticated,)
    service_class = ProactiveAssistantService

    @extend_schema(
        tags=("Proactive Assistant",),
        operation_id="assistant_recommendation_generate",
        summary="Generate a recommendation for an analyzed email",
        description=(
            "Evaluates one AI-analyzed email owned by the authenticated user. Duplicate, "
            "quiet-hour, dismissal, and interruption-limit rules are always enforced."
        ),
        request=ProactiveRecommendationRequestSerializer,
        responses={
            200: ProactiveRecommendationResponseSerializer,
            404: OpenApiResponse(description="Analyzed email not found."),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = ProactiveRecommendationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            email = Email.objects.select_related(
                "account__user",
                "ai_summary__category",
            ).get(
                uuid=serializer.validated_data["email_uuid"],
                account__user=authenticated_user(request),
                ai_summary__isnull=False,
            )
        except Email.DoesNotExist as exc:
            raise NotFound("Analyzed email not found.") from exc

        decision, suggestion = self.service_class().evaluate_email(email)
        payload = {
            "should_suggest": decision.should_suggest,
            "reason": decision.reason,
            "suggestion": suggestion,
        }
        return Response(ProactiveRecommendationResponseSerializer(payload).data)
