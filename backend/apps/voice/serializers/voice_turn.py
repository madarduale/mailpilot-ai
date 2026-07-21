from __future__ import annotations

from typing import Any

from rest_framework import serializers


class VoiceTurnRequestSerializer(serializers.Serializer[dict[str, Any]]):
    audio = serializers.FileField(write_only=True)
    conversation_uuid = serializers.UUIDField(required=False, allow_null=True)
    language = serializers.CharField(default="en", max_length=16)

    def validate_audio(self, value: Any) -> Any:
        if value.size > 25 * 1024 * 1024:
            raise serializers.ValidationError("Audio must not exceed 25 MB.")
        allowed_types = {
            "audio/m4a",
            "audio/mp4",
            "audio/mpeg",
            "audio/wav",
            "audio/webm",
            "video/mp4",
        }
        if value.content_type not in allowed_types:
            raise serializers.ValidationError("Unsupported audio format.")
        return value


class VoiceTurnResponseSerializer(serializers.Serializer[Any]):
    conversation_uuid = serializers.UUIDField()
    transcript = serializers.CharField()
    response_text = serializers.CharField()
    response_audio_url = serializers.URLField(allow_null=True)
    suggestions = serializers.ListField(child=serializers.CharField())
