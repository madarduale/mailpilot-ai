from django.urls import path

from .views import (
    GmailAccountDetailView,
    GmailAccountListView,
    GmailAuthorizationView,
    GmailCallbackView,
    GmailSyncView,
)

app_name = "email_accounts"

urlpatterns = [
    path("gmail/accounts/", GmailAccountListView.as_view(), name="gmail-account-list"),
    path(
        "gmail/accounts/<uuid:account_uuid>/",
        GmailAccountDetailView.as_view(),
        name="gmail-account-detail",
    ),
    path("gmail/authorize/", GmailAuthorizationView.as_view(), name="gmail-authorize"),
    path("gmail/callback/", GmailCallbackView.as_view(), name="gmail-callback"),
    path("gmail/<uuid:account_uuid>/sync/", GmailSyncView.as_view(), name="gmail-sync"),
]
