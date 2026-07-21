from __future__ import annotations

import logging
from dataclasses import dataclass

from django.core.cache import cache
from django.db import connection

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class HealthReport:
    status: str
    checks: dict[str, str]

    @property
    def ready(self) -> bool:
        return self.status == "ok"


class HealthService:
    """Infrastructure health checks used by deployment probes."""

    @staticmethod
    def liveness() -> HealthReport:
        return HealthReport(status="ok", checks={"application": "ok"})

    @staticmethod
    def readiness() -> HealthReport:
        checks: dict[str, str] = {}

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            checks["database"] = "ok"
        except Exception:
            logger.warning("Readiness database check failed", exc_info=True)
            checks["database"] = "unavailable"

        cache_key = "health:readiness"
        try:
            cache.set(cache_key, "ok", timeout=10)
            checks["cache"] = "ok" if cache.get(cache_key) == "ok" else "unavailable"
            cache.delete(cache_key)
        except Exception:
            logger.warning("Readiness cache check failed", exc_info=True)
            checks["cache"] = "unavailable"

        status_value = "ok" if all(value == "ok" for value in checks.values()) else "degraded"
        return HealthReport(status=status_value, checks=checks)
