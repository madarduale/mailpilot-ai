from django.urls import path

from .views import (
    NotificationListView,
    NotificationReadAllView,
    NotificationReadView,
    PushDeviceRegistrationView,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("read-all/", NotificationReadAllView.as_view(), name="read-all"),
    path("devices/", PushDeviceRegistrationView.as_view(), name="device-register"),
    path("<uuid:notification_uuid>/read/", NotificationReadView.as_view(), name="read"),
]
