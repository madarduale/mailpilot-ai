from __future__ import annotations

import re
import uuid
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from apps.common.utils import reset_request_id, set_request_id

REQUEST_ID_HEADER = "HTTP_X_REQUEST_ID"
RESPONSE_ID_HEADER = "X-Request-ID"
SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


class RequestIDMiddleware(MiddlewareMixin):
    """Propagate a safe client request ID or generate a new UUID correlation ID."""

    def process_request(self, request: HttpRequest) -> None:
        supplied_id = request.META.get(REQUEST_ID_HEADER, "")
        request_id = supplied_id if SAFE_REQUEST_ID.fullmatch(supplied_id) else str(uuid.uuid4())
        request.request_id = request_id  # type: ignore[attr-defined]
        request._request_id_token = set_request_id(request_id)  # type: ignore[attr-defined]

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        request_id = getattr(request, "request_id", str(uuid.uuid4()))
        response[RESPONSE_ID_HEADER] = request_id
        token: Any = getattr(request, "_request_id_token", None)
        if token is not None:
            reset_request_id(token)
        return response
