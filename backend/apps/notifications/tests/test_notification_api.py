from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.notifications.models import Notification, NotificationStatus, PushDevice

pytestmark = pytest.mark.django_db


def client_for(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_notification_list_and_read_actions_are_user_scoped() -> None:
    user = User.objects.create_user(email="notification-owner@example.com")
    other = User.objects.create_user(email="notification-other@example.com")
    notification = Notification.objects.create(
        user=user,
        notification_type="proactive_assistant",
        title="Deadline tomorrow",
        body="A government form is due tomorrow.",
    )
    Notification.objects.create(
        user=other,
        notification_type="private",
        title="Other user",
        body="Must not leak.",
    )
    client = client_for(user)

    listed = client.get(reverse("v1:notifications:list"))
    marked = client.post(
        reverse("v1:notifications:read", kwargs={"notification_uuid": notification.uuid})
    )

    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert marked.status_code == 204
    notification.refresh_from_db()
    assert notification.status == NotificationStatus.READ
    assert notification.read_at is not None


def test_register_device_upserts_rotated_token_owner() -> None:
    first = User.objects.create_user(email="device-first@example.com")
    second = User.objects.create_user(email="device-second@example.com")
    token = "ExponentPushToken[valid-device-token]"

    first_response = client_for(first).post(
        reverse("v1:notifications:device-register"),
        {"token": token, "platform": "android", "provider": "expo"},
        format="json",
    )
    second_response = client_for(second).post(
        reverse("v1:notifications:device-register"),
        {"token": token, "platform": "ios", "provider": "expo"},
        format="json",
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    device = PushDevice.objects.get(token=token)
    assert device.user == second
    assert device.platform == "ios"
    assert PushDevice.objects.count() == 1
