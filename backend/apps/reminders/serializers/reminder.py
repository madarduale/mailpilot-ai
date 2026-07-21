from __future__ import annotations

from rest_framework import serializers

from apps.reminders.models import Reminder


class ReminderSerializer(serializers.ModelSerializer[Reminder]):
    email_uuid = serializers.UUIDField(source="email.uuid", read_only=True, allow_null=True)
    created_from_email = serializers.SerializerMethodField()

    @staticmethod
    def get_created_from_email(reminder: Reminder) -> bool:
        return reminder.email_id is not None

    class Meta:
        model = Reminder
        fields = (
            "uuid",
            "email_uuid",
            "title",
            "description",
            "due_at",
            "priority",
            "status",
            "completed_at",
            "lead_notification_sent",
            "lead_notification_sent_at",
            "notification_sent",
            "notification_sent_at",
            "created_from_email",
            "snoozed_until",
            "source",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "uuid",
            "completed_at",
            "lead_notification_sent",
            "lead_notification_sent_at",
            "notification_sent",
            "notification_sent_at",
            "source",
            "created_at",
            "updated_at",
        )


class ReminderWriteSerializer(serializers.Serializer[dict[str, object]]):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    due_at = serializers.DateTimeField(required=False)
    priority = serializers.IntegerField(required=False, min_value=0, max_value=100)
    email_uuid = serializers.UUIDField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=("pending", "completed", "snoozed", "cancelled"), required=False
    )
    snoozed_until = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        if not self.partial:
            missing = [field for field in ("title", "due_at") if field not in attrs]
            if missing:
                errors = {field: "This field is required." for field in missing}
                raise serializers.ValidationError(errors)
        return attrs
