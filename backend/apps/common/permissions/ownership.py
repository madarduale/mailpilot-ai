from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsObjectOwner(BasePermission):
    """Allow access only when an object's `user_id` matches the requester."""

    message = "You do not have permission to access this resource."

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(obj, "user_id", None) == request.user.pk
        )
