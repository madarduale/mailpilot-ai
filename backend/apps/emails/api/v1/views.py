from __future__ import annotations

import base64
from typing import Any

from django.db.models import QuerySet
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import filters, generics, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.emails.filters import EmailFilter
from apps.emails.models import Email
from apps.emails.serializers import EmailDetailSerializer, EmailListSerializer
from apps.email_accounts.integrations.gmail.client import GmailClientFactory
from apps.intelligence.serializers.email_analysis import AISummarySerializer


def user_emails(request: Request) -> QuerySet[Email]:
    return Email.objects.filter(account__user=request.user).select_related(
        "account", "ai_summary__category"
    )


class EmailListView(generics.ListAPIView[Email]):
    permission_classes = (IsAuthenticated,)
    serializer_class = EmailListSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_class = EmailFilter
    search_fields = ("subject", "sender", "sender_name", "body", "snippet")
    ordering_fields = ("received_at", "created_at", "sender", "subject")
    ordering = ("-received_at",)
    queryset = Email.objects.none()

    def get_queryset(self) -> QuerySet[Email]:
        if getattr(self, "swagger_fake_view", False):
            return Email.objects.none()
        return user_emails(self.request)

    @extend_schema(tags=("Emails",), operation_id="emails_list", summary="List emails")
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class EmailDetailView(generics.RetrieveAPIView[Email]):
    permission_classes = (IsAuthenticated,)
    serializer_class = EmailDetailSerializer
    lookup_field = "uuid"
    lookup_url_kwarg = "email_uuid"
    queryset = Email.objects.none()

    def get_queryset(self) -> QuerySet[Email]:
        if getattr(self, "swagger_fake_view", False):
            return Email.objects.none()
        return user_emails(self.request)

    @extend_schema(tags=("Emails",), operation_id="emails_retrieve", summary="Get an email")
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().get(request, *args, **kwargs)


class EmailReadView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=("Emails",),
        operation_id="emails_mark_read",
        summary="Mark an email as read",
        request=None,
        responses={204: None, 404: OpenApiResponse(description="Email not found")},
    )
    def post(self, request: Request, email_uuid: str) -> Response:
        email = generics.get_object_or_404(user_emails(request), uuid=email_uuid)
        if not email.is_read:
            email.is_read = True
            email.save(update_fields=("is_read", "updated_at"))
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmailAttachmentDownloadView(APIView):
    permission_classes = (IsAuthenticated,)
    gmail_client_factory = GmailClientFactory

    @extend_schema(
        tags=("Emails",),
        operation_id="emails_attachment_download",
        summary="Download an email attachment",
        responses={200: OpenApiResponse(description="Attachment bytes"), 404: OpenApiResponse()},
    )
    def get(self, request: Request, email_uuid: str, attachment_uuid: str) -> HttpResponse:
        email = generics.get_object_or_404(user_emails(request), uuid=email_uuid)
        attachment = next(
            (
                item
                for item in email.attachments
                if isinstance(item, dict) and str(item.get("uuid")) == str(attachment_uuid)
            ),
            None,
        )
        if attachment is None:
            raise NotFound("Attachment not found.")

        client = self.gmail_client_factory().build(email.account)
        payload = (
            client.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=email.provider_message_id, id=str(attachment_uuid))
            .execute()
        )
        content = base64.urlsafe_b64decode(str(payload.get("data", "")) + "===")
        filename = str(attachment.get("filename") or "attachment")
        content_type = str(attachment.get("content_type") or "application/octet-stream")
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class EmailSummaryView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=("AI Assistant",),
        operation_id="email_ai_summary_retrieve",
        summary="Get stored AI analysis for an email",
        responses={
            200: AISummarySerializer,
            404: OpenApiResponse(description="Analysis not found"),
        },
    )
    def get(self, request: Request, email_uuid: str) -> Response:
        email = generics.get_object_or_404(user_emails(request), uuid=email_uuid)
        analysis = getattr(email, "ai_summary", None)
        if analysis is None:
            raise NotFound("AI analysis is not available yet.")
        return Response(AISummarySerializer(analysis).data)
