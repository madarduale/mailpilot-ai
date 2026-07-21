from django.urls import path

from .views import AIChatView

app_name = "ai"

urlpatterns = [
    path("chat/", AIChatView.as_view(), name="chat"),
]
