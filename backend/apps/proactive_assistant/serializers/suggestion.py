from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.dashboard.serializers.dashboard import DashboardEmailSerializer
from apps.proactive_assistant.models import AssistantSuggestion, SuggestionHistory


class AssistantSuggestionSerializer(serializers.ModelSerializer[AssistantSuggestion]):
    email_uuid = serializers.UUIDField(source="email.uuid", read_only=True, allow_null=True)
    ai_summary = serializers.CharField(source="email.ai_summary.summary", read_only=True, default="")
    importance_score = serializers.IntegerField(source="email.ai_summary.importance_score", read_only=True, allow_null=True, default=None)
    deadline = serializers.DateTimeField(source="email.ai_summary.deadline", read_only=True, allow_null=True, default=None)

    class Meta:
        model = AssistantSuggestion
        fields = (
            "uuid",
            "email_uuid",
            "ai_summary",
            "importance_score",
            "deadline",
            "suggestion_type",
            "recommended_action",
            "status",
            "delivery_method",
            "interruption_priority",
            "title",
            "message",
            "reason",
            "action_payload",
            "scheduled_for",
            "expires_at",
            "acted_at",
            "created_at",
            "updated_at",
        )


class SuggestionHistorySerializer(serializers.ModelSerializer[SuggestionHistory]):
    suggestion_uuid = serializers.UUIDField(source="suggestion.uuid", read_only=True)
    suggestion_title = serializers.CharField(source="suggestion.title", read_only=True)

    class Meta:
        model = SuggestionHistory
        fields = (
            "uuid",
            "suggestion_uuid",
            "suggestion_title",
            "event",
            "channel",
            "details",
            "occurred_at",
        )


class SuggestionFeedbackRequestSerializer(serializers.Serializer[dict[str, str]]):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


class ProactiveRecommendationRequestSerializer(serializers.Serializer[dict[str, Any]]):
    email_uuid = serializers.UUIDField()


class SuggestionActionResponseSerializer(serializers.Serializer[Any]):
    suggestion = AssistantSuggestionSerializer()
    action_result = serializers.DictField(child=serializers.JSONField())


class ProactiveRecommendationResponseSerializer(serializers.Serializer[Any]):
    should_suggest = serializers.BooleanField()
    reason = serializers.CharField()
    suggestion = AssistantSuggestionSerializer(allow_null=True)


class BriefingCountsSerializer(serializers.Serializer[Any]):
    received = serializers.IntegerField(min_value=0)
    attention = serializers.IntegerField(min_value=0)
    urgent = serializers.IntegerField(min_value=0)
    unanswered_urgent = serializers.IntegerField(min_value=0)


class TodayBriefingSerializer(serializers.Serializer[Any]):
    generated_at = serializers.DateTimeField()
    greeting = serializers.CharField()
    narrative = serializers.CharField()
    counts = BriefingCountsSerializer()
    important_emails = DashboardEmailSerializer(many=True)
    deadlines = AssistantSuggestionSerializer(many=True)
    meetings = AssistantSuggestionSerializer(many=True)
    suggested_replies = AssistantSuggestionSerializer(many=True)
    smart_actions = AssistantSuggestionSerializer(many=True)
    pending_follow_ups = AssistantSuggestionSerializer(many=True)
    risk_alerts = AssistantSuggestionSerializer(many=True)
