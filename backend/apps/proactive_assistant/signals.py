from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.intelligence.models import AISummary
from apps.proactive_assistant.tasks import evaluate_analyzed_email


@receiver(post_save, sender=AISummary, dispatch_uid="proactive_evaluate_ai_summary")
def enqueue_proactive_evaluation(
    sender: type[AISummary],
    instance: AISummary,
    created: bool,
    **kwargs: object,
) -> None:
    """Publish an evaluation only after the analysis transaction commits."""

    if not created or not settings.PROACTIVE_ASSISTANT_AUTO_EVALUATE:
        return
    email_uuid = str(instance.email_id)
    transaction.on_commit(lambda: evaluate_analyzed_email.delay(email_uuid))
