from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.emails.models import Email
from apps.intelligence.models import AICategory, AISummary
from apps.reminders.models import Reminder


class DashboardCategorySerializer(serializers.ModelSerializer[AICategory]):
    class Meta:
        model = AICategory
        fields = ("name", "color")


class DashboardSummarySerializer(serializers.ModelSerializer[AISummary]):
    category = DashboardCategorySerializer(read_only=True)

    class Meta:
        model = AISummary
        fields = (
            "summary",
            "importance_score",
            "category",
            "action_required",
            "deadline",
        )


class DashboardEmailSerializer(serializers.ModelSerializer[Email]):
    ai_summary = DashboardSummarySerializer(read_only=True)

    class Meta:
        model = Email
        fields = (
            "uuid",
            "subject",
            "sender",
            "sender_name",
            "received_at",
            "is_read",
            "is_done",
            "ai_summary",
        )


class DashboardReminderSerializer(serializers.ModelSerializer[Reminder]):
    class Meta:
        model = Reminder
        fields = ("uuid", "title", "description", "due_at", "priority", "status")


class DashboardStatsSerializer(serializers.Serializer[dict[str, int]]):
    important = serializers.IntegerField(min_value=0)
    action_required = serializers.IntegerField(min_value=0)
    unread = serializers.IntegerField(min_value=0)


class DashboardResponseSerializer(serializers.Serializer[Any]):
    briefing = serializers.CharField()
    stats = DashboardStatsSerializer()
    important_emails = DashboardEmailSerializer(many=True)
    reminders = DashboardReminderSerializer(many=True)
    unread_notifications = serializers.IntegerField(min_value=0)
    unread_emails = serializers.IntegerField(min_value=0)
