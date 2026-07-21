from __future__ import annotations

from collections import OrderedDict
from typing import Any

from django.conf import settings
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPageNumberPagination(PageNumberPagination):
    """Stable page-number contract shared by all collection endpoints."""

    page_size = settings.API_PAGE_SIZE
    page_size_query_param = "page_size"
    max_page_size = settings.API_MAX_PAGE_SIZE

    def get_paginated_response(self, data: list[Any]) -> Response:
        assert self.page is not None
        assert self.request is not None
        return Response(
            OrderedDict(
                (
                    ("count", self.page.paginator.count),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("page", self.page.number),
                    ("page_size", self.get_page_size(self.request)),
                    ("results", data),
                )
            )
        )

    def get_paginated_response_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        response_schema = super().get_paginated_response_schema(schema)
        properties = response_schema["properties"]
        properties["page"] = {"type": "integer", "example": 1}
        properties["page_size"] = {"type": "integer", "example": self.page_size}
        return response_schema
