from __future__ import annotations

import base64
from unittest.mock import MagicMock

import pytest

from apps.accounts.models import User
from apps.email_accounts.models import EmailAccount, EmailSyncStatus
from apps.email_accounts.services.gmail_sync_service import GmailSyncService
from apps.emails.models import Email
from apps.notifications.models import Notification
from apps.preferences.models import UserPreference

pytestmark = pytest.mark.django_db


def encoded(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def test_initial_sync_normalizes_gmail_without_notifying_historical_mail() -> None:
    user = User.objects.create_user(email="sync-owner@example.com")
    UserPreference.objects.create(user=user, importance_threshold=75)
    account = EmailAccount.objects.create(
        user=user,
        provider_account_id="google-sync-owner",
        email_address="sync-owner@gmail.com",
        access_token_encrypted="encrypted",
        refresh_token_encrypted="encrypted",
    )
    messages = MagicMock()
    messages.list.return_value.execute.return_value = {"messages": [{"id": "gmail-1"}]}
    messages.get.return_value.execute.return_value = {
        "id": "gmail-1",
        "threadId": "thread-1",
        "internalDate": "1784538000000",
        "labelIds": ["INBOX", "UNREAD", "IMPORTANT"],
        "snippet": "Please review this important update.",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "Manager <manager@example.com>"},
                {"name": "To", "value": "sync-owner@gmail.com"},
                {"name": "Subject", "value": "Important update"},
            ],
            "body": {"data": encoded("Action is required today.")},
        },
    }
    client = MagicMock()
    client.users.return_value.messages.return_value = messages
    factory = MagicMock()
    factory.build.return_value = client

    result = GmailSyncService(client_factory=factory).sync(account, notify_new=True)

    assert result.created == 1
    email = Email.objects.get(account=account, provider_message_id="gmail-1")
    assert email.subject == "Important update"
    assert email.body == "Action is required today."
    assert email.is_read is False
    assert not Notification.objects.filter(email=email).exists()
    account.refresh_from_db()
    assert account.sync_status == EmailSyncStatus.ACTIVE


def test_subsequent_sync_queues_ai_analysis_for_notification_decision(
    monkeypatch: pytest.MonkeyPatch,
    django_capture_on_commit_callbacks,
) -> None:
    user = User.objects.create_user(email="notify-owner@example.com")
    UserPreference.objects.create(user=user, importance_threshold=75)
    account = EmailAccount.objects.create(
        user=user,
        provider_account_id="google-notify-owner",
        email_address="notify-owner@gmail.com",
        access_token_encrypted="encrypted",
        refresh_token_encrypted="encrypted",
        last_synced_at="2026-07-20T09:00:00Z",
    )
    messages = MagicMock()
    messages.list.return_value.execute.return_value = {"messages": [{"id": "gmail-new"}]}
    messages.get.return_value.execute.return_value = {
        "id": "gmail-new",
        "threadId": "thread-new",
        "internalDate": "1784538000000",
        "labelIds": ["INBOX", "UNREAD", "IMPORTANT"],
        "snippet": "A genuinely new important update.",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "Manager <manager@example.com>"},
                {"name": "To", "value": "notify-owner@gmail.com"},
                {"name": "Subject", "value": "New important update"},
            ],
            "body": {"data": encoded("Please review this today.")},
        },
    }
    client = MagicMock()
    client.users.return_value.messages.return_value = messages
    factory = MagicMock()
    factory.build.return_value = client

    from apps.intelligence.tasks import analyze_email

    queued = MagicMock()
    monkeypatch.setattr(analyze_email, "delay", queued)
    with django_capture_on_commit_callbacks(execute=True):
        GmailSyncService(client_factory=factory).sync(account, notify_new=True)

    email = Email.objects.get(provider_message_id="gmail-new")
    queued.assert_called_once_with(str(email.uuid), True)
    assert not Notification.objects.filter(email=email).exists()
