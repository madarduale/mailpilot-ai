from django.urls import path

from .views import (
    EmailAttachmentDownloadView,
    EmailDetailView,
    EmailDoneView,
    EmailListView,
    EmailReadView,
    EmailSummaryView,
)

app_name = "emails"

urlpatterns = [
    path("", EmailListView.as_view(), name="list"),
    path("<uuid:email_uuid>/", EmailDetailView.as_view(), name="detail"),
    path(
        "<uuid:email_uuid>/attachments/<str:attachment_uuid>/",
        EmailAttachmentDownloadView.as_view(),
        name="attachment-download",
    ),
    path("<uuid:email_uuid>/read/", EmailReadView.as_view(), name="read"),
    path("<uuid:email_uuid>/done/", EmailDoneView.as_view(), name="done"),
    path("<uuid:email_uuid>/summary/", EmailSummaryView.as_view(), name="summary"),
]
