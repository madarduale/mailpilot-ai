from django.urls import path

from .views import ReminderCompleteView, ReminderDetailView, ReminderListCreateView

app_name = "reminders"

urlpatterns = [
    path("", ReminderListCreateView.as_view(), name="list-create"),
    path("<uuid:reminder_uuid>/", ReminderDetailView.as_view(), name="detail"),
    path("<uuid:reminder_uuid>/complete/", ReminderCompleteView.as_view(), name="complete"),
]
