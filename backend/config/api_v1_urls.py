from django.urls import include, path

app_name = "v1"

urlpatterns = [
    path("auth/", include("apps.accounts.api.v1.urls")),
    path("oauth/", include("apps.email_accounts.api.v1.urls")),
    path("dashboard/", include("apps.dashboard.api.v1.urls")),
    path("health/", include("apps.common.api.urls")),
    path("assistant/", include("apps.proactive_assistant.api.v1.urls")),
    path("ai/", include("apps.intelligence.api.v1.urls")),
    path("voice/", include("apps.voice.api.v1.urls")),
    path("notifications/", include("apps.notifications.api.v1.urls")),
    path("reminders/", include("apps.reminders.api.v1.urls")),
    path("settings/", include("apps.preferences.api.v1.urls")),
    path("emails/", include("apps.emails.api.v1.urls")),
]
