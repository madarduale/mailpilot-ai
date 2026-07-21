from __future__ import annotations

import json
from urllib.request import Request, urlopen

from django.conf import settings


class ExpoPushGateway:
    """Small Expo Push Service HTTP client with bounded request timeouts."""

    endpoint = "https://exp.host/--/api/v2/push/send"

    def send(self, messages: list[dict[str, object]]) -> list[dict[str, object]]:
        if not messages:
            return []
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if settings.EXPO_ACCESS_TOKEN:
            headers["Authorization"] = f"Bearer {settings.EXPO_ACCESS_TOKEN}"
        request = Request(
            self.endpoint,
            data=json.dumps(messages).encode(),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=10) as response:  # noqa: S310
            payload = json.loads(response.read().decode())
        data = payload.get("data", [])
        return data if isinstance(data, list) else [data]
