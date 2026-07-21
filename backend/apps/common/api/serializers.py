from __future__ import annotations

from typing import Any

from rest_framework import serializers


class HealthResponseSerializer(serializers.Serializer[Any]):
    status = serializers.ChoiceField(choices=("ok", "degraded"), read_only=True)
    checks = serializers.DictField(child=serializers.CharField(), read_only=True)


class ErrorDetailSerializer(serializers.Serializer[dict[str, Any]]):
    code = serializers.CharField(read_only=True)
    message = serializers.CharField(read_only=True)
    details = serializers.JSONField(read_only=True, allow_null=True)


class ErrorResponseSerializer(serializers.Serializer[dict[str, Any]]):
    error = ErrorDetailSerializer(read_only=True)
    request_id = serializers.CharField(read_only=True)
