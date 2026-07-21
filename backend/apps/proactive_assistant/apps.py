from django.apps import AppConfig


class ProactiveAssistantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.proactive_assistant"
    verbose_name = "Proactive AI Assistant"

    def ready(self) -> None:
        from apps.proactive_assistant import signals  # noqa: F401
