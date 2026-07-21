from __future__ import annotations

from typing import Any

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import filters, generics, status
from rest_framework.exceptions import AuthenticationFailed, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.reminders.models import Reminder
from apps.reminders.repositories import ReminderRepository
from apps.reminders.serializers import ReminderSerializer, ReminderWriteSerializer
from apps.reminders.services import (
    ReminderEmailNotFoundError,
    ReminderNotFoundError,
    ReminderService,
)


def user_from(request: Request) -> User:
    if not isinstance(request.user, User):
        raise AuthenticationFailed
    return request.user


class ReminderListCreateView(generics.ListAPIView[Reminder]):
    permission_classes = (IsAuthenticated,)
    serializer_class = ReminderSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("status",)
    search_fields = ("title", "description")
    ordering_fields = ("due_at", "created_at")
    ordering = ("due_at",)
    queryset = Reminder.objects.none()
    service_class = ReminderService

    def get_queryset(self):  # type: ignore[no-untyped-def]
        if getattr(self, "swagger_fake_view", False):
            return Reminder.objects.none()
        return ReminderRepository.for_user(user_from(self.request))

    @extend_schema(tags=("Reminders",), responses={200: ReminderSerializer(many=True)})
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=("Reminders",), request=ReminderWriteSerializer, responses={201: ReminderSerializer}
    )
    def post(self, request: Request) -> Response:
        serializer = ReminderWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            reminder = self.service_class().create(user_from(request), serializer.validated_data)
        except ReminderEmailNotFoundError as exc:
            raise NotFound("Email not found.") from exc
        return Response(ReminderSerializer(reminder).data, status=status.HTTP_201_CREATED)


class ReminderDetailView(APIView):
    permission_classes = (IsAuthenticated,)
    service_class = ReminderService

    def _get(self, request: Request, reminder_uuid: str) -> Reminder:
        reminder = ReminderRepository.get(user_from(request), reminder_uuid)
        if reminder is None:
            raise NotFound("Reminder not found.")
        return reminder

    @extend_schema(tags=("Reminders",), responses={200: ReminderSerializer, 404: OpenApiResponse()})
    def get(self, request: Request, reminder_uuid: str) -> Response:
        return Response(ReminderSerializer(self._get(request, reminder_uuid)).data)

    @extend_schema(
        tags=("Reminders",),
        request=ReminderWriteSerializer,
        responses={200: ReminderSerializer},
    )
    def patch(self, request: Request, reminder_uuid: str) -> Response:
        serializer = ReminderWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            reminder = self.service_class().update(
                user_from(request), reminder_uuid, serializer.validated_data
            )
        except ReminderEmailNotFoundError as exc:
            raise NotFound("Email not found.") from exc
        except ReminderNotFoundError as exc:
            raise NotFound("Reminder not found.") from exc
        return Response(ReminderSerializer(reminder).data)

    @extend_schema(tags=("Reminders",), responses={204: None})
    def delete(self, request: Request, reminder_uuid: str) -> Response:
        try:
            self.service_class().delete(user_from(request), reminder_uuid)
        except ReminderNotFoundError as exc:
            raise NotFound("Reminder not found.") from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReminderCompleteView(APIView):
    """Completes one user-owned reminder without accepting arbitrary fields."""

    permission_classes = (IsAuthenticated,)
    service_class = ReminderService

    @extend_schema(tags=("Reminders",), responses={200: ReminderSerializer, 404: OpenApiResponse()})
    def post(self, request: Request, reminder_uuid: str) -> Response:
        try:
            reminder = self.service_class().complete(user_from(request), reminder_uuid)
        except ReminderNotFoundError as exc:
            raise NotFound("Reminder not found.") from exc
        return Response(ReminderSerializer(reminder).data)
