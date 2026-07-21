from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_settings_are_created_and_updated_for_authenticated_user() -> None:
    user = User.objects.create_user(email="settings-owner@example.com")
    client = APIClient()
    client.force_authenticate(user)

    response = client.get(reverse("v1:preferences:detail"))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["importance_threshold"] == 75

    response = client.patch(
        reverse("v1:preferences:detail"),
        {"importance_threshold": 88, "push_notifications_enabled": False},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["importance_threshold"] == 88
    assert response.data["push_notifications_enabled"] is False
