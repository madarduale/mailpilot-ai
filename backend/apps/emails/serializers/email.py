from __future__ import annotations

from rest_framework import serializers

from apps.emails.models import Email
from apps.intelligence.models import AICategory, AISummary


class EmailCategorySerializer(serializers.ModelSerializer[AICategory]):
    class Meta:
        model = AICategory
        fields = ("name", "color")


class EmailAnalysisSerializer(serializers.ModelSerializer[AISummary]):
    category = EmailCategorySerializer(read_only=True)

    class Meta:
        model = AISummary
        fields = (
            "summary",
            "importance_score",
            "category",
            "action_required",
            "deadline",
            "meeting_date",
            "phishing_score",
            "confidence",
            "reasoning",
        )


class EmailListSerializer(serializers.ModelSerializer[Email]):
    ai_analysis = EmailAnalysisSerializer(source="ai_summary", read_only=True, allow_null=True)

    class Meta:
        model = Email
        fields = (
            "uuid",
            "subject",
            "sender",
            "sender_name",
            "snippet",
            "received_at",
            "is_read",
            "is_starred",
            "labels",
            "ai_analysis",
        )


class EmailDetailSerializer(serializers.ModelSerializer[Email]):
    ai_analysis = EmailAnalysisSerializer(source="ai_summary", read_only=True, allow_null=True)
    attachments = serializers.SerializerMethodField()

    def get_attachments(self, email: Email) -> list[dict[str, object]]:
        request = self.context.get("request")
        attachments: list[dict[str, object]] = []
        for attachment in email.attachments:
            if not isinstance(attachment, dict):
                continue
            attachment_uuid = str(attachment.get("uuid", ""))
            item = dict(attachment)
            if attachment_uuid:
                path = f"/api/v1/emails/{email.uuid}/attachments/{attachment_uuid}/"
                item["download_url"] = request.build_absolute_uri(path) if request else path
            attachments.append(item)
        return attachments

    class Meta:
        model = Email
        fields = (
            "uuid",
            "subject",
            "sender",
            "sender_name",
            "recipients",
            "cc_recipients",
            "bcc_recipients",
            "reply_to",
            "body",
            "body_html",
            "snippet",
            "received_at",
            "thread_id",
            "attachments",
            "is_read",
            "is_starred",
            "labels",
            "ai_analysis",
        )
