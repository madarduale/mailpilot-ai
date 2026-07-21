from rest_framework import serializers

from apps.email_accounts.models import EmailAccount


class GmailAuthorizationRequestSerializer(serializers.Serializer):
    redirect_uri = serializers.CharField(max_length=2048)


class GmailAuthorizationResponseSerializer(serializers.Serializer):
    authorization_url = serializers.URLField()


class GmailCallbackQuerySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=4096, required=False)
    state = serializers.CharField(max_length=8192)
    error = serializers.CharField(max_length=255, required=False)

    def validate(self, attrs: dict[str, str]) -> dict[str, str]:
        if not attrs.get("code") and not attrs.get("error"):
            raise serializers.ValidationError("Google returned neither a code nor an error.")
        return attrs


class EmailAccountSerializer(serializers.ModelSerializer[EmailAccount]):
    class Meta:
        model = EmailAccount
        fields = (
            "uuid",
            "provider",
            "email_address",
            "display_name",
            "sync_status",
            "last_synced_at",
            "last_sync_error",
            "is_primary",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
