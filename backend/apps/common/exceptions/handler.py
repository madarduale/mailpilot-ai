from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.common.utils import get_request_id

logger = logging.getLogger(__name__)


def _message_for(data: Any, status_code: int) -> str:
    if isinstance(data, dict) and "detail" in data:
        return str(data["detail"])
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Request failed"


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    """Return a consistent, non-leaking error envelope for every API failure."""

    response = drf_exception_handler(exc, context)
    request_id = get_request_id()

    if response is None:
        logger.error(
            "Unhandled API exception",
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return Response(
            {
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                    "details": None,
                },
                "request_id": request_id,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = exc.default_code if isinstance(exc, APIException) else "request_error"
    response.data = {
        "error": {
            "code": code,
            "message": _message_for(response.data, response.status_code),
            "details": response.data,
        },
        "request_id": request_id,
    }
    return response
