from __future__ import annotations

from rest_framework import serializers

from apps.preferences.models import UserPreference


class UserPreferenceSerializer(serializers.ModelSerializer[UserPreference]):
    class Meta:
        model = UserPreference
        fields = (
            "uuid",
            "importance_threshold",
            "push_notifications_enabled",
            "notification_mode",
            "reminder_notifications_enabled",
            "reminder_lead_time_minutes",
            "notify_categories",
            "quiet_hours_enabled",
            "quiet_hours_start",
            "quiet_hours_end",
            "timezone",
            "locale",
            "voice_language",
            "tts_voice",
            "digest_frequency",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("uuid", "created_at", "updated_at")

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        enabled = attrs.get(
            "quiet_hours_enabled",
            getattr(self.instance, "quiet_hours_enabled", False),
        )
        start = attrs.get(
            "quiet_hours_start",
            getattr(self.instance, "quiet_hours_start", None),
        )
        end = attrs.get(
            "quiet_hours_end",
            getattr(self.instance, "quiet_hours_end", None),
        )
        if enabled and (start is None or end is None):
            raise serializers.ValidationError(
                "Quiet-hour start and end are required when quiet hours are enabled."
            )
        return attrs
