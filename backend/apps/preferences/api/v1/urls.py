from django.urls import path

from .views import UserPreferenceView

app_name = "preferences"

urlpatterns = [path("", UserPreferenceView.as_view(), name="detail")]
