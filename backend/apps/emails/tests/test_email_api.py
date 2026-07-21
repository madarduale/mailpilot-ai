from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.email_accounts.models import EmailAccount
from apps.emails.models import Email

pytestmark = pytest.mark.django_db


def make_email(user: User, suffix: str) -> Email:
    account = EmailAccount.objects.create(
        user=user,
        provider_account_id=f"provider-{suffix}",
        email_address=f"{suffix}@gmail.com",
        access_token_encrypted="encrypted",
        refresh_token_encrypted="encrypted",
    )
    return Email.objects.create(
        account=account,
        provider_message_id=f"message-{suffix}",
        thread_id=f"thread-{suffix}",
        subject=f"Subject {suffix}",
        sender="sender@example.com",
        recipients=[account.email_address],
        snippet="A synchronized Gmail message",
        received_at=timezone.now() - timedelta(minutes=1),
        is_read=False,
    )


def test_email_endpoints_are_user_scoped_and_can_mark_read() -> None:
    owner = User.objects.create_user(email="email-owner@example.com")
    other = User.objects.create_user(email="email-other@example.com")
    email = make_email(owner, "owner")
    make_email(other, "other")
    client = APIClient()
    client.force_authenticate(owner)

    response = client.get(reverse("v1:emails:list"))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["uuid"] == str(email.uuid)

    response = client.get(reverse("v1:emails:detail", kwargs={"email_uuid": email.uuid}))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["ai_analysis"] is None

    response = client.post(reverse("v1:emails:read", kwargs={"email_uuid": email.uuid}))
    assert response.status_code == status.HTTP_204_NO_CONTENT
    email.refresh_from_db()
    assert email.is_read is True
