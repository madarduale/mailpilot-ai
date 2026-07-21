from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.serializers import (
    NotificationSerializer,
    PushDeviceRegistrationSerializer,
)
from apps.notifications.services import NotificationService


def current_user(request: Request) -> User:
    if not isinstance(request.user, User):
        raise AuthenticationFailed
    return request.user


class NotificationListView(generics.ListAPIView[Notification]):
    permission_classes = (IsAuthenticated,)
    serializer_class = NotificationSerializer
    ordering = ("-created_at",)
    filter_backends: tuple[type, ...] = ()
    queryset = Notification.objects.none()

    def get_queryset(self) -> QuerySet[Notification]:
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return Notification.objects.filter(user=current_user(self.request)).select_related(
            "email", "reminder"
        )

    @extend_schema(
        tags=("Notifications",),
        operation_id="notifications_list",
        summary="List notifications",
        description="Returns the authenticated user's paginated notification history.",
        responses={200: NotificationSerializer(many=True)},
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class NotificationReadView(APIView):
    permission_classes = (IsAuthenticated,)
    service_class = NotificationService

    @extend_schema(
        tags=("Notifications",),
        operation_id="notification_mark_read",
        summary="Mark a notification as read",
        request=None,
        responses={204: None, 404: OpenApiResponse(description="Notification not found.")},
    )
    def post(self, request: Request, notification_uuid: str) -> Response:
        notification = self.service_class().mark_read(
            current_user(request), notification_uuid
        )
        if notification is None:
            raise NotFound("Notification not found.")
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationReadAllView(APIView):
    permission_classes = (IsAuthenticated,)
    service_class = NotificationService

    @extend_schema(
        tags=("Notifications",),
        operation_id="notifications_mark_all_read",
        summary="Mark all notifications as read",
        request=None,
        responses={204: None},
    )
    def post(self, request: Request) -> Response:
        self.service_class().mark_all_read(current_user(request))
        return Response(status=status.HTTP_204_NO_CONTENT)


class PushDeviceRegistrationView(APIView):
    permission_classes = (IsAuthenticated,)
    service_class = NotificationService

    @extend_schema(
        tags=("Notifications",),
        operation_id="notification_device_register",
        summary="Register an Expo push device",
        description="Registers or safely transfers a rotated Expo push token.",
        request=PushDeviceRegistrationSerializer,
        responses={201: PushDeviceRegistrationSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = PushDeviceRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = self.service_class().register_device(
            user=current_user(request),
            **serializer.validated_data,
        )
        return Response(
            PushDeviceRegistrationSerializer(device).data,
            status=status.HTTP_201_CREATED,
        )
