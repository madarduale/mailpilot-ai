from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.dashboard.serializers import DashboardResponseSerializer
from apps.dashboard.services import DashboardService


class DashboardView(APIView):
    permission_classes = (IsAuthenticated,)
    service_class = DashboardService

    @extend_schema(
        tags=("Dashboard",),
        operation_id="dashboard_retrieve",
        summary="Get the priority dashboard",
        description=(
            "Returns today's user-scoped priority email statistics, the highest-priority "
            "AI-analyzed messages, upcoming reminders, and unread notification count."
        ),
        responses={200: DashboardResponseSerializer},
    )
    def get(self, request: Request) -> Response:
        user = request.user
        if not isinstance(user, User):
            raise TypeError("Authenticated request did not contain a MailPilot user.")
        result = self.service_class().get_dashboard(user)
        return Response(DashboardResponseSerializer(result).data)
