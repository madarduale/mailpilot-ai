from __future__ import annotations

from typing import Any

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

EMAIL = "pilot@example.com"
PASSWORD = "StrongPass!234"
NEW_PASSWORD = "EvenStronger!567"


def register(client: APIClient, **overrides: Any) -> dict[str, Any]:
    payload = {
        "email": EMAIL,
        "password": PASSWORD,
        "first_name": "Mail",
        "last_name": "Pilot",
    }
    payload.update(overrides)
    response = client.post(reverse("v1:accounts:register"), payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


def authenticated_client(access_token: str) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
    return client


def test_register_creates_user_and_returns_tokens() -> None:
    client = APIClient()

    body = register(client, email="PILOT@EXAMPLE.COM")

    user = User.objects.get()
    assert user.email == EMAIL
    assert user.check_password(PASSWORD)
    assert body["user"]["uuid"] == str(user.uuid)
    assert body["user"]["email"] == EMAIL
    assert body["tokens"]["access"]
    assert body["tokens"]["refresh"]
    assert body["tokens"]["token_type"] == "Bearer"


def test_register_rejects_duplicate_email_case_insensitively() -> None:
    client = APIClient()
    register(client)

    response = client.post(
        reverse("v1:accounts:register"),
        {"email": EMAIL.upper(), "password": PASSWORD},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.json()["error"]["details"]
    assert User.objects.count() == 1


def test_login_returns_tokens_without_revealing_credential_details() -> None:
    client = APIClient()
    register(client)

    valid_response = client.post(
        reverse("v1:accounts:login"),
        {"email": EMAIL, "password": PASSWORD},
        format="json",
    )
    invalid_response = client.post(
        reverse("v1:accounts:login"),
        {"email": EMAIL, "password": "wrong-password"},
        format="json",
    )

    assert valid_response.status_code == status.HTTP_200_OK
    assert valid_response.json()["tokens"]["access"]
    assert invalid_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert invalid_response.json()["error"]["message"] == "Invalid email or password."


def test_refresh_rotates_and_blacklists_previous_token() -> None:
    client = APIClient()
    old_refresh = register(client)["tokens"]["refresh"]

    first_response = client.post(
        reverse("v1:accounts:refresh"), {"refresh": old_refresh}, format="json"
    )
    replay_response = client.post(
        reverse("v1:accounts:refresh"), {"refresh": old_refresh}, format="json"
    )

    assert first_response.status_code == status.HTTP_200_OK
    assert first_response.json()["refresh"] != old_refresh
    assert replay_response.status_code == status.HTTP_401_UNAUTHORIZED


def test_current_user_requires_authentication_and_allows_profile_update() -> None:
    anonymous = APIClient()
    body = register(anonymous)
    client = authenticated_client(body["tokens"]["access"])

    anonymous_response = anonymous.get(reverse("v1:accounts:me"))
    get_response = client.get(reverse("v1:accounts:me"))
    patch_response = client.patch(
        reverse("v1:accounts:me"), {"first_name": "Updated"}, format="json"
    )

    assert anonymous_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert get_response.status_code == status.HTTP_200_OK
    assert patch_response.status_code == status.HTTP_200_OK
    assert patch_response.json()["first_name"] == "Updated"
    assert patch_response.json()["last_name"] == "Pilot"


def test_logout_only_revokes_current_users_refresh_token() -> None:
    anonymous = APIClient()
    body = register(anonymous)
    client = authenticated_client(body["tokens"]["access"])

    response = client.post(
        reverse("v1:accounts:logout"),
        {"refresh": body["tokens"]["refresh"]},
        format="json",
    )
    refresh_response = anonymous.post(
        reverse("v1:accounts:refresh"),
        {"refresh": body["tokens"]["refresh"]},
        format="json",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED


def test_password_change_revokes_refresh_tokens_and_updates_credentials() -> None:
    anonymous = APIClient()
    body = register(anonymous)
    client = authenticated_client(body["tokens"]["access"])

    response = client.post(
        reverse("v1:accounts:password-change"),
        {
            "current_password": PASSWORD,
            "new_password": NEW_PASSWORD,
            "new_password_confirm": NEW_PASSWORD,
        },
        format="json",
    )
    old_login = anonymous.post(
        reverse("v1:accounts:login"),
        {"email": EMAIL, "password": PASSWORD},
        format="json",
    )
    new_login = anonymous.post(
        reverse("v1:accounts:login"),
        {"email": EMAIL, "password": NEW_PASSWORD},
        format="json",
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert old_login.status_code == status.HTTP_401_UNAUTHORIZED
    assert new_login.status_code == status.HTTP_200_OK
    assert BlacklistedToken.objects.filter(token__user__email=EMAIL).exists()
