from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_reminder_crud_is_authenticated_and_user_scoped() -> None:
    assert APIClient().get(reverse("v1:reminders:list-create")).status_code == 401
    owner = User.objects.create_user(email="reminder-owner@example.com")
    other = User.objects.create_user(email="reminder-other@example.com")
    client = APIClient()
    client.force_authenticate(owner)
    created = client.post(
        reverse("v1:reminders:list-create"),
        {
            "title": "Submit report",
            "description": "Send it to the manager",
            "due_at": (timezone.now() + timedelta(days=1)).isoformat(),
        },
        format="json",
    )
    assert created.status_code == 201
    reminder_uuid = created.json()["uuid"]
    assert client.get(reverse("v1:reminders:list-create")).json()["count"] == 1

    client.force_authenticate(other)
    detail_url = reverse("v1:reminders:detail", kwargs={"reminder_uuid": reminder_uuid})
    assert client.get(detail_url).status_code == 404


def test_reminder_can_be_updated_completed_and_deleted() -> None:
    user = User.objects.create_user(email="reminder-lifecycle@example.com")
    client = APIClient(); client.force_authenticate(user)
    created = client.post(reverse("v1:reminders:list-create"), {"title": "Call bank", "due_at": (timezone.now() + timedelta(hours=2)).isoformat()}, format="json")
    reminder_uuid = created.json()["uuid"]
    detail = reverse("v1:reminders:detail", kwargs={"reminder_uuid": reminder_uuid})
    assert client.patch(detail, {"title": "Call bank today", "priority": 90}, format="json").json()["priority"] == 90
    complete = client.post(reverse("v1:reminders:complete", kwargs={"reminder_uuid": reminder_uuid}))
    assert complete.status_code == 200 and complete.json()["status"] == "completed"
    assert client.delete(detail).status_code == 204
