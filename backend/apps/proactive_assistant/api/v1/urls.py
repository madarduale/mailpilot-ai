from django.urls import path

from .views import (
    GenerateRecommendationView,
    SuggestionAcceptView,
    SuggestionDismissView,
    SuggestionHistoryListView,
    SuggestionListView,
    TodayBriefingView,
)

app_name = "assistant"

urlpatterns = [
    path("briefing/today/", TodayBriefingView.as_view(), name="today-briefing"),
    path("suggestions/", SuggestionListView.as_view(), name="suggestion-list"),
    path(
        "suggestions/<uuid:suggestion_uuid>/dismiss/",
        SuggestionDismissView.as_view(),
        name="suggestion-dismiss",
    ),
    path(
        "suggestions/<uuid:suggestion_uuid>/accept/",
        SuggestionAcceptView.as_view(),
        name="suggestion-accept",
    ),
    path("history/", SuggestionHistoryListView.as_view(), name="history-list"),
    path(
        "recommendations/generate/",
        GenerateRecommendationView.as_view(),
        name="recommendation-generate",
    ),
]
