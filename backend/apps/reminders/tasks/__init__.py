from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Literal

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.notifications.models import Notification, NotificationChannel, NotificationStatus
from apps.notifications.services import NotificationDeliveryService
from apps.preferences.models import UserPreference
from apps.reminders.models import Reminder, ReminderStatus

logger = logging.getLogger(__name__)

ReminderNotificationKind = Literal["lead", "due"]


def _message(reminder: Reminder, kind: ReminderNotificationKind) -> tuple[str, str]:
    title = reminder.title.lower()
    if "interview" in title:
        heading = "Interview Reminder"
    elif any(word in title for word in ("bill", "payment", "invoice")):
        heading = "Payment Due"
    elif "meeting" in title:
        heading = "Meeting Starts Soon"
    else:
        heading = "Reminder Due"

    if kind == "lead":
        return heading, reminder.description or f"{reminder.title} is coming up."
    return heading, reminder.description or f"{reminder.title} is due now."


def _already_sent(reminder: Reminder, kind: ReminderNotificationKind) -> bool:
    if kind == "lead":
        return reminder.lead_notification_sent
    return reminder.notification_sent


def _mark_sent(reminder: Reminder, kind: ReminderNotificationKind) -> None:
    now = timezone.now()
    if kind == "lead":
        reminder.lead_notification_sent = True
        reminder.lead_notification_sent_at = now
        reminder.save(
            update_fields=("lead_notification_sent", "lead_notification_sent_at", "updated_at")
        )
        return

    reminder.notification_sent = True
    reminder.notification_sent_at = now
    reminder.save(update_fields=("notification_sent", "notification_sent_at", "updated_at"))


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def deliver_reminder_notification(
    self: Any,
    reminder_uuid: str,
    kind: ReminderNotificationKind,
) -> bool:
    """Deliver one reminder notification once, safely across concurrent workers."""
    failed = False
    with transaction.atomic():
        reminder = (
            Reminder.objects.select_for_update()
            .select_related("user")
            .filter(uuid=reminder_uuid)
            .first()
        )
        if reminder is None or reminder.status != ReminderStatus.PENDING:
            return False
        if kind not in ("lead", "due") or _already_sent(reminder, kind):
            return False

        now = timezone.now()
        preference, _ = UserPreference.objects.get_or_create(user=reminder.user)
        lead_at = reminder.due_at - timedelta(minutes=preference.reminder_lead_time_minutes)
        if kind == "lead" and now < lead_at:
            return False
        if kind == "due" and now < reminder.due_at:
            return False

        if not preference.reminder_notifications_enabled:
            _mark_sent(reminder, kind)
            logger.info(
                "Reminder notification skipped",
                extra={"reminder_uuid": str(reminder.uuid), "kind": kind, "reason": "disabled"},
            )
            return False

        title, body = _message(reminder, kind)
        notification_type = f"reminder_{kind}"
        notification = (
            Notification.objects.filter(
                reminder=reminder,
                notification_type=notification_type,
            )
            .exclude(status=NotificationStatus.SENT)
            .order_by("-created_at")
            .first()
        )
        if notification is None:
            notification = Notification.objects.create(
                user=reminder.user,
                reminder=reminder,
                channel=NotificationChannel.PUSH,
                notification_type=notification_type,
                title=title,
                body=body,
                data={"reminder_uuid": str(reminder.uuid), "kind": kind},
            )

        delivered = NotificationDeliveryService().deliver(notification)
        if delivered.status != NotificationStatus.SENT:
            failed = True
        else:
            _mark_sent(reminder, kind)
            logger.info(
                "Reminder notification delivered",
                extra={"reminder_uuid": str(reminder.uuid), "kind": kind},
            )

    if failed:
        raise ConnectionError("Reminder push was not accepted.")
    return True


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def deliver_due_reminder(self: Any, reminder_uuid: str) -> bool:
    """Backward-compatible due-time reminder task."""
    return deliver_reminder_notification.run(reminder_uuid, "due")


@shared_task
def dispatch_due_reminders() -> int:
    """Queue lead-time and due-time reminder notifications."""
    now = timezone.now()
    queued = 0
    reminders = (
        Reminder.objects.filter(
            status=ReminderStatus.PENDING,
            due_at__lte=now + timedelta(days=1),
        )
        .select_related("user")
        .order_by("due_at")[:500]
    )
    for reminder in reminders:
        preference, _ = UserPreference.objects.get_or_create(user=reminder.user)
        lead_at = reminder.due_at - timedelta(minutes=preference.reminder_lead_time_minutes)
        if not reminder.lead_notification_sent and now >= lead_at:
            deliver_reminder_notification.delay(str(reminder.uuid), "lead")
            queued += 1
        if not reminder.notification_sent and now >= reminder.due_at:
            deliver_reminder_notification.delay(str(reminder.uuid), "due")
            queued += 1
    return queued
