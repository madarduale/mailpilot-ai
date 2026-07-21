from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import User
from apps.preferences.models import UserPreference
from apps.preferences.serializers import UserPreferenceSerializer
from apps.preferences.services import PreferenceService


class UserPreferenceView(RetrieveUpdateAPIView[UserPreference]):
    permission_classes = (IsAuthenticated,)
    http_method_names = ("get", "patch", "head", "options")
    serializer_class = UserPreferenceSerializer
    service_class = PreferenceService

    def get_object(self) -> UserPreference:
        if not isinstance(self.request.user, User):
            raise TypeError("Authenticated request did not contain a MailPilot user.")
        return self.service_class().get_or_create(self.request.user)

    @extend_schema(
        tags=("Settings",),
        operation_id="settings_retrieve",
        summary="Get user settings",
    )
    def get(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=("Settings",),
        operation_id="settings_update",
        summary="Update user settings",
        request=UserPreferenceSerializer,
        responses={200: UserPreferenceSerializer},
    )
    def patch(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        return super().patch(request, *args, **kwargs)
