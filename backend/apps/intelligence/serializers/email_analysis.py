from rest_framework import serializers

from apps.intelligence.models import AISummary


class AISummarySerializer(serializers.ModelSerializer[AISummary]):
    category = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)

    class Meta:
        model = AISummary
        fields = (
            "uuid",
            "summary",
            "importance_score",
            "category",
            "category_slug",
            "action_required",
            "deadline",
            "meeting_date",
            "phishing_score",
            "confidence",
            "reasoning",
            "model_name",
            "prompt_version",
            "processed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
