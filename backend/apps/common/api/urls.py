from django.urls import path

from .views import LivenessView, ReadinessView

app_name = "system"

urlpatterns = [
    path("live/", LivenessView.as_view(), name="live"),
    path("ready/", ReadinessView.as_view(), name="ready"),
]
