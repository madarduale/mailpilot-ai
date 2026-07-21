from __future__ import annotations

from django.urls import URLPattern, URLResolver

# Voice websocket routes are registered with the voice API module.
websocket_urlpatterns: list[URLPattern | URLResolver] = []
