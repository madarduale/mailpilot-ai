from __future__ import annotations

from typing import Any

from rest_framework import serializers


class ChatHistoryMessageSerializer(serializers.Serializer[dict[str, str]]):
    role = serializers.ChoiceField(choices=("user", "assistant"))
    content = serializers.CharField(max_length=4_000, trim_whitespace=True)


class ChatRequestSerializer(serializers.Serializer[dict[str, Any]]):
    message = serializers.CharField(max_length=4_000, trim_whitespace=True)
    history = ChatHistoryMessageSerializer(many=True, required=False, default=list)
    conversation_uuid = serializers.UUIDField(required=False, allow_null=True)
    email_uuid = serializers.UUIDField(required=False, allow_null=True)

    def validate_history(self, value: list[dict[str, str]]) -> list[dict[str, str]]:
        if len(value) > 20:
            raise serializers.ValidationError("History must contain at most 20 messages.")
        return value


class ChatResponseSerializer(serializers.Serializer[Any]):
    conversation_uuid = serializers.UUIDField()
    message = serializers.CharField()
    suggestions = serializers.ListField(child=serializers.CharField())
