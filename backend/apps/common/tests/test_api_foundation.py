from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

from apps.common.pagination import StandardPageNumberPagination
from apps.common.permissions import IsObjectOwner

pytestmark = pytest.mark.django_db


def test_liveness_propagates_safe_request_id() -> None:
    client = APIClient()

    response = client.get(
        reverse("v1:system:live"),
        HTTP_X_REQUEST_ID="mobile-request-123",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok", "checks": {"application": "ok"}}
    assert response["X-Request-ID"] == "mobile-request-123"


def test_invalid_request_id_is_replaced_with_uuid() -> None:
    response = APIClient().get(
        reverse("v1:system:live"),
        HTTP_X_REQUEST_ID="unsafe\nheader",
    )

    assert response.status_code == status.HTTP_200_OK
    uuid.UUID(response["X-Request-ID"])


def test_readiness_checks_database_and_cache() -> None:
    response = APIClient().get(reverse("v1:system:ready"))

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "ok",
        "checks": {"database": "ok", "cache": "ok"},
    }


def test_api_errors_use_standard_envelope_and_request_id() -> None:
    response = APIClient().post(
        reverse("v1:accounts:login"),
        {"email": "nobody@example.com", "password": "incorrect"},
        format="json",
        HTTP_X_REQUEST_ID="auth-error-1",
    )

    body = response.json()
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert body["error"]["code"] == "authentication_failed"
    assert body["error"]["message"] == "Invalid email or password."
    assert body["request_id"] == "auth-error-1"
    assert response["X-Request-ID"] == "auth-error-1"


def test_standard_pagination_contract_and_page_size_limit() -> None:
    factory = APIRequestFactory()
    request = Request(factory.get("/items/", {"page": 2, "page_size": 3}))
    paginator = StandardPageNumberPagination()

    page = paginator.paginate_queryset(list(range(10)), request)
    response = paginator.get_paginated_response(page)

    assert response.data == {
        "count": 10,
        "next": "http://testserver/items/?page=3&page_size=3",
        "previous": "http://testserver/items/?page_size=3",
        "page": 2,
        "page_size": 3,
        "results": [3, 4, 5],
    }


def test_object_owner_permission_matches_authenticated_user() -> None:
    owner_id = uuid.uuid4()
    request = SimpleNamespace(
        user=SimpleNamespace(is_authenticated=True, pk=owner_id),
    )
    owned_object = SimpleNamespace(user_id=owner_id)
    other_object = SimpleNamespace(user_id=uuid.uuid4())
    permission = IsObjectOwner()

    assert permission.has_object_permission(request, SimpleNamespace(), owned_object)
    assert not permission.has_object_permission(request, SimpleNamespace(), other_object)


def test_openapi_and_documentation_endpoints_are_public() -> None:
    client = APIClient()

    schema_response = client.get(reverse("openapi-schema"))
    swagger_response = client.get(reverse("swagger-ui"))
    redoc_response = client.get(reverse("redoc"))

    assert schema_response.status_code == status.HTTP_200_OK
    assert swagger_response.status_code == status.HTTP_200_OK
    assert redoc_response.status_code == status.HTTP_200_OK
