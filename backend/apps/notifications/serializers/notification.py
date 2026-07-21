from __future__ import annotations

from rest_framework import serializers

from apps.notifications.models import DevicePlatform, Notification, PushDevice


class NotificationSerializer(serializers.ModelSerializer[Notification]):
    email_uuid = serializers.UUIDField(source="email.uuid", read_only=True, allow_null=True)
    reminder_uuid = serializers.UUIDField(source="reminder.uuid", read_only=True, allow_null=True)

    class Meta:
        model = Notification
        fields = (
            "uuid",
            "notification_type",
            "title",
            "body",
            "status",
            "importance_score",
            "email_uuid",
            "reminder_uuid",
            "created_at",
            "read_at",
        )


class PushDeviceRegistrationSerializer(serializers.ModelSerializer[PushDevice]):
    token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(choices=DevicePlatform.choices)
    provider = serializers.ChoiceField(choices=("expo",), default="expo")

    class Meta:
        model = PushDevice
        fields = ("token", "platform", "provider")

    def validate_token(self, value: str) -> str:
        if not (
            value.startswith("ExponentPushToken[") or value.startswith("ExpoPushToken[")
        ) or not value.endswith("]"):
            raise serializers.ValidationError("Invalid Expo push token.")
        return value
