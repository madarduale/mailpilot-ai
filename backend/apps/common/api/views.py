from __future__ import annotations

from typing import Any

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.common.api.serializers import HealthResponseSerializer
from apps.common.services import HealthService


class LivenessView(APIView):
    authentication_classes: tuple[type[Any], ...] = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "health"
    service_class = HealthService

    @extend_schema(
        tags=("System",),
        operation_id="system_liveness",
        summary="Application liveness",
        description="Confirms that the API process is running without checking dependencies.",
        responses={200: HealthResponseSerializer},
        auth=(),
    )
    def get(self, request: Request) -> Response:
        report = self.service_class().liveness()
        return Response(HealthResponseSerializer(report).data)


class ReadinessView(APIView):
    authentication_classes: tuple[type[Any], ...] = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "health"
    service_class = HealthService

    @extend_schema(
        tags=("System",),
        operation_id="system_readiness",
        summary="Application readiness",
        description="Checks whether the database and cache are available to serve traffic.",
        responses={
            200: HealthResponseSerializer,
            503: OpenApiResponse(
                response=HealthResponseSerializer,
                description="One or more required dependencies are unavailable.",
            ),
        },
        auth=(),
    )
    def get(self, request: Request) -> Response:
        report = self.service_class().readiness()
        response_status = (
            status.HTTP_200_OK if report.ready else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(HealthResponseSerializer(report).data, status=response_status)
