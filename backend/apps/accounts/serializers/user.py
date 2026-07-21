from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import User


class UserProfileSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = (
            "uuid",
            "email",
            "first_name",
            "last_name",
            "date_joined",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class UserProfileUpdateSerializer(serializers.Serializer[dict[str, str]]):
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate(self, attrs: dict[str, str]) -> dict[str, str]:
        if not attrs:
            raise serializers.ValidationError("At least one profile field is required.")
        return attrs

