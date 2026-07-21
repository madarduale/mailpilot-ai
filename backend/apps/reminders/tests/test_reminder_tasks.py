from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications.models import Notification, NotificationStatus
from apps.reminders.models import Reminder
from apps.preferences.models import UserPreference
from apps.reminders.tasks import deliver_due_reminder, deliver_reminder_notification, dispatch_due_reminders

pytestmark = pytest.mark.django_db


def test_due_reminder_is_delivered_once() -> None:
    user = User.objects.create_user(email="reminder-task@example.com")
    reminder = Reminder.objects.create(user=user, title="Pay electricity bill", due_at=timezone.now() - timedelta(minutes=1))
    with patch("apps.reminders.tasks.NotificationDeliveryService.deliver") as deliver:
        deliver.side_effect = lambda notification: _sent(notification)
        assert deliver_due_reminder.run(str(reminder.uuid)) is True
        assert deliver_due_reminder.run(str(reminder.uuid)) is False
    reminder.refresh_from_db()
    assert reminder.notification_sent is True
    assert Notification.objects.filter(reminder=reminder).count() == 1


def test_lead_and_due_reminders_are_delivered_once_per_stage() -> None:
    user = User.objects.create_user(email="lead-reminder-task@example.com")
    UserPreference.objects.create(user=user, reminder_lead_time_minutes=30)
    reminder = Reminder.objects.create(
        user=user,
        title="Interview",
        due_at=timezone.now() + timedelta(minutes=20),
    )
    with patch("apps.reminders.tasks.NotificationDeliveryService.deliver") as deliver:
        deliver.side_effect = lambda notification: _sent(notification)
        assert deliver_reminder_notification.run(str(reminder.uuid), "lead") is True
        assert deliver_reminder_notification.run(str(reminder.uuid), "lead") is False
        assert deliver_reminder_notification.run(str(reminder.uuid), "due") is False

    reminder.due_at = timezone.now() - timedelta(minutes=1)
    reminder.save(update_fields=("due_at", "updated_at"))
    with patch("apps.reminders.tasks.NotificationDeliveryService.deliver") as deliver:
        deliver.side_effect = lambda notification: _sent(notification)
        assert deliver_reminder_notification.run(str(reminder.uuid), "due") is True
        assert deliver_reminder_notification.run(str(reminder.uuid), "due") is False

    reminder.refresh_from_db()
    assert reminder.lead_notification_sent is True
    assert reminder.notification_sent is True
    assert Notification.objects.filter(reminder=reminder).count() == 2


def _sent(notification: Notification) -> Notification:
    notification.status = NotificationStatus.SENT
    notification.save(update_fields=("status",))
    return notification


def test_dispatch_only_queues_due_undelivered_reminders() -> None:
    user = User.objects.create_user(email="dispatch@example.com")
    due = Reminder.objects.create(user=user, title="Due", due_at=timezone.now() - timedelta(minutes=1))
    Reminder.objects.create(user=user, title="Later", due_at=timezone.now() + timedelta(hours=1))
    with patch("apps.reminders.tasks.deliver_reminder_notification.delay") as delay:
        assert dispatch_due_reminders.run() == 2
        delay.assert_any_call(str(due.uuid), "lead")
        delay.assert_any_call(str(due.uuid), "due")
