from __future__ import annotations

import pytest

from apps.accounts.models import User
from apps.notifications.models import Notification, NotificationStatus, PushDevice
from apps.notifications.services import NotificationDeliveryService

pytestmark = pytest.mark.django_db


class FakeExpoGateway:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []

    def send(self, messages: list[dict[str, object]]) -> list[dict[str, object]]:
        self.messages = messages
        return [{"status": "ok", "id": "ticket-123"} for _ in messages]


def test_delivery_sends_to_active_devices_and_persists_ticket() -> None:
    user = User.objects.create_user(email="push@example.com")
    PushDevice.objects.create(
        user=user,
        token="ExponentPushToken[active-token]",
        platform="android",
    )
    PushDevice.objects.create(
        user=user,
        token="ExponentPushToken[inactive-token]",
        platform="ios",
        is_active=False,
    )
    notification = Notification.objects.create(
        user=user,
        notification_type="proactive_assistant",
        title="Interview tomorrow",
        body="Would you like me to draft a reply?",
        data={"suggestion_uuid": "abc"},
    )
    gateway = FakeExpoGateway()

    NotificationDeliveryService(gateway=gateway).deliver(notification)  # type: ignore[arg-type]

    notification.refresh_from_db()
    assert notification.status == NotificationStatus.SENT
    assert notification.provider_message_id == "ticket-123"
    assert len(gateway.messages) == 1
    assert gateway.messages[0]["to"] == "ExponentPushToken[active-token]"
