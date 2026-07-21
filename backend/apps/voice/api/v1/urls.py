from django.urls import path

from .views import VoiceConversationTurnView

app_name = "voice"

urlpatterns = [
    path("conversations/turn/", VoiceConversationTurnView.as_view(), name="conversation-turn"),
]
