from django.contrib import admin

from apps.proactive_assistant.models import (
    AssistantMemory,
    AssistantSuggestion,
    SuggestionFeedback,
    SuggestionHistory,
    UserBehavior,
)


@admin.register(AssistantSuggestion)
class AssistantSuggestionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "suggestion_type",
        "status",
        "delivery_method",
        "interruption_priority",
        "created_at",
    )
    list_filter = ("suggestion_type", "status", "delivery_method")
    search_fields = ("title", "message", "reason", "user__email")
    readonly_fields = ("uuid", "created_at", "updated_at")
    raw_id_fields = ("user", "email")


@admin.register(SuggestionHistory)
class SuggestionHistoryAdmin(admin.ModelAdmin):
    list_display = ("suggestion", "user", "event", "channel", "occurred_at")
    list_filter = ("event", "channel")
    readonly_fields = ("uuid", "created_at", "updated_at", "occurred_at")
    raw_id_fields = ("suggestion", "user")


@admin.register(AssistantMemory)
class AssistantMemoryAdmin(admin.ModelAdmin):
    list_display = ("user", "namespace", "key", "confidence", "is_active")
    list_filter = ("namespace", "is_active", "source")
    search_fields = ("user__email", "namespace", "key")
    readonly_fields = ("uuid", "created_at", "updated_at")
    raw_id_fields = ("user",)


@admin.register(UserBehavior)
class UserBehaviorAdmin(admin.ModelAdmin):
    list_display = ("user", "behavior_type", "target", "occurred_at")
    list_filter = ("behavior_type",)
    search_fields = ("user__email", "target")
    readonly_fields = ("uuid", "created_at", "updated_at", "occurred_at")
    raw_id_fields = ("user", "email")


@admin.register(SuggestionFeedback)
class SuggestionFeedbackAdmin(admin.ModelAdmin):
    list_display = ("suggestion", "user", "feedback_type", "occurred_at")
    list_filter = ("feedback_type",)
    search_fields = ("user__email", "comment")
    readonly_fields = ("uuid", "created_at", "updated_at", "occurred_at")
    raw_id_fields = ("suggestion", "user")
