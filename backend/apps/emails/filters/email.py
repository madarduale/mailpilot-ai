from __future__ import annotations

import django_filters

from apps.emails.models import Email


class EmailFilter(django_filters.FilterSet):
    account_uuid = django_filters.UUIDFilter(field_name="account__uuid")
    received_after = django_filters.IsoDateTimeFilter(field_name="received_at", lookup_expr="gte")
    received_before = django_filters.IsoDateTimeFilter(field_name="received_at", lookup_expr="lte")
    category = django_filters.CharFilter(field_name="ai_summary__category__slug")

    class Meta:
        model = Email
        fields = ("account_uuid", "is_read", "is_starred", "category")
