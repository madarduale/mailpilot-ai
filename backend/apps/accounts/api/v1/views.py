from __future__ import annotations

from typing import Any

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.serializers import (
    AuthenticationResponseSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordChangeSerializer,
    RefreshSerializer,
    RegisterSerializer,
    TokenPairSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
)
from apps.accounts.services import AuthenticationService
from apps.accounts.services.exceptions import (
    EmailAlreadyRegistered,
    IncorrectCurrentPassword,
    InvalidCredentials,
    InvalidRefreshToken,
)


class RegisterView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth_register"
    service_class = AuthenticationService

    @extend_schema(
        tags=("Authentication",),
        operation_id="auth_register",
        summary="Register an account",
        description="Creates a user and returns a JWT access/refresh token pair.",
        request=RegisterSerializer,
        responses={201: AuthenticationResponseSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = self.service_class().register(**serializer.validated_data)
        except EmailAlreadyRegistered as exc:
            raise ValidationError({"email": "An account with this email already exists."}) from exc

        response = AuthenticationResponseSerializer(
            {"user": result.user, "tokens": result.tokens}
        )
        return Response(response.data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth_login"
    service_class = AuthenticationService

    @extend_schema(
        tags=("Authentication",),
        operation_id="auth_login",
        summary="Log in",
        description="Validates credentials and returns a JWT access/refresh token pair.",
        request=LoginSerializer,
        responses={
            200: AuthenticationResponseSerializer,
            401: OpenApiResponse(description="Invalid credentials."),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = self.service_class().login(
                request=request._request,
                **serializer.validated_data,
            )
        except InvalidCredentials as exc:
            raise AuthenticationFailed("Invalid email or password.") from exc

        response = AuthenticationResponseSerializer(
            {"user": result.user, "tokens": result.tokens}
        )
        return Response(response.data)


class RefreshTokenView(APIView):
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth_refresh"
    service_class = AuthenticationService

    @extend_schema(
        tags=("Authentication",),
        operation_id="auth_token_refresh",
        summary="Refresh JWT tokens",
        description="Rotates a valid refresh token and blacklists the previous token.",
        request=RefreshSerializer,
        responses={
            200: TokenPairSerializer,
            401: OpenApiResponse(description="Invalid or expired refresh token."),
        },
    )
    def post(self, request: Request) -> Response:
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            tokens = self.service_class().refresh(serializer.validated_data["refresh"])
        except InvalidRefreshToken as exc:
            raise AuthenticationFailed("Invalid or expired refresh token.") from exc
        return Response(TokenPairSerializer(tokens).data)


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)
    service_class = AuthenticationService

    @extend_schema(
        tags=("Authentication",),
        operation_id="auth_logout",
        summary="Log out",
        description="Blacklists the supplied refresh token for the authenticated user.",
        request=LogoutSerializer,
        responses={204: None, 400: OpenApiResponse(description="Invalid refresh token.")},
    )
    def post(self, request: Request) -> Response:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not isinstance(user, User):
            raise AuthenticationFailed
        try:
            self.service_class().logout(
                serializer.validated_data["refresh"],
                user=user,
            )
        except InvalidRefreshToken as exc:
            raise ValidationError({"refresh": "Invalid refresh token."}) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    permission_classes = (IsAuthenticated,)
    service_class = AuthenticationService

    @extend_schema(
        tags=("Authentication",),
        operation_id="auth_current_user",
        summary="Get the current user",
        responses={200: UserProfileSerializer},
    )
    def get(self, request: Request) -> Response:
        user = request.user
        if not isinstance(user, User):
            raise AuthenticationFailed
        return Response(UserProfileSerializer(user).data)

    @extend_schema(
        tags=("Authentication",),
        operation_id="auth_update_current_user",
        summary="Update the current user",
        request=UserProfileUpdateSerializer,
        responses={200: UserProfileSerializer},
    )
    def patch(self, request: Request) -> Response:
        serializer = UserProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        authenticated_user = request.user
        if not isinstance(authenticated_user, User):
            raise AuthenticationFailed
        user = self.service_class().update_profile(
            authenticated_user,
            **serializer.validated_data,
        )
        return Response(UserProfileSerializer(user).data)


class PasswordChangeView(APIView):
    permission_classes = (IsAuthenticated,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth_password_change"
    service_class = AuthenticationService

    @extend_schema(
        tags=("Authentication",),
        operation_id="auth_change_password",
        summary="Change the current password",
        description="Changes the password and revokes every outstanding refresh token.",
        request=PasswordChangeSerializer,
        responses={204: None, 400: OpenApiResponse(description="Password validation failed.")},
    )
    def post(self, request: Request) -> Response:
        user = request.user
        if not isinstance(user, User):
            raise AuthenticationFailed

        serializer = PasswordChangeSerializer(data=request.data, context={"user": user})
        serializer.is_valid(raise_exception=True)
        data: dict[str, Any] = serializer.validated_data
        try:
            self.service_class().change_password(
                user=user,
                current_password=data["current_password"],
                new_password=data["new_password"],
            )
        except IncorrectCurrentPassword as exc:
            raise ValidationError(
                {"current_password": "The current password is incorrect."}
            ) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)
