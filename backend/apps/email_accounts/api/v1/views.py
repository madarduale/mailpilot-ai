from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException, AuthenticationFailed, NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.email_accounts.models import EmailAccount
from apps.email_accounts.serializers import (
    EmailAccountSerializer,
    GmailAuthorizationRequestSerializer,
    GmailAuthorizationResponseSerializer,
    GmailCallbackQuerySerializer,
)
from apps.email_accounts.services import (
    GmailAccountNotFoundError,
    GmailAccountService,
    GmailOAuthService,
)
from apps.email_accounts.services.exceptions import (
    EmailAccountServiceError,
    InvalidOAuthState,
)
from apps.email_accounts.tasks import sync_gmail_account


class OAuthServiceUnavailable(APIException):
    status_code = 503
    default_detail = "Gmail authorization is temporarily unavailable."
    default_code = "oauth_service_unavailable"


class GmailAccountListView(APIView):
    permission_classes = (IsAuthenticated,)
    service_class = GmailAccountService

    @extend_schema(
        tags=("Gmail OAuth",),
        operation_id="gmail_accounts_list",
        summary="List connected Gmail accounts",
        responses={200: EmailAccountSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        if not isinstance(request.user, User):
            raise AuthenticationFailed
        accounts = self.service_class().list_for_user(request.user)
        return Response(EmailAccountSerializer(accounts, many=True).data)


class GmailAccountDetailView(APIView):
    permission_classes = (IsAuthenticated,)
    service_class = GmailAccountService

    @extend_schema(
        tags=("Gmail OAuth",),
        operation_id="gmail_account_disconnect",
        summary="Disconnect a Gmail account",
        responses={204: None, 404: OpenApiResponse(description="Account not found")},
    )
    def delete(self, request: Request, account_uuid: str) -> Response:
        if not isinstance(request.user, User):
            raise AuthenticationFailed
        try:
            self.service_class().disconnect(request.user, account_uuid)
        except GmailAccountNotFoundError as exc:
            raise NotFound("Gmail account not found.") from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


def _callback_redirect(uri: str, **params: str) -> str:
    parsed = urlsplit(uri)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update(params)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))


class GmailAuthorizationView(APIView):
    permission_classes = (IsAuthenticated,)
    service_class = GmailOAuthService

    @extend_schema(
        tags=("Gmail OAuth",),
        operation_id="gmail_oauth_authorize",
        summary="Start Gmail authorization",
        description=(
            "Returns a Google consent URL bound to the authenticated user and an approved "
            "mobile deep-link callback. OAuth credentials never pass through the mobile app."
        ),
        parameters=[
            OpenApiParameter(
                name="redirect_uri",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
            )
        ],
        responses={200: GmailAuthorizationResponseSerializer, 503: OpenApiResponse()},
    )
    def get(self, request: Request) -> Response:
        serializer = GmailAuthorizationRequestSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        if not isinstance(request.user, User):
            raise AuthenticationFailed
        try:
            authorization_url = self.service_class().authorization_url(
                user=request.user,
                client_redirect_uri=serializer.validated_data["redirect_uri"],
            )
        except EmailAccountServiceError as exc:
            raise OAuthServiceUnavailable from exc
        return Response(
            GmailAuthorizationResponseSerializer(
                {"authorization_url": authorization_url}
            ).data
        )


class GmailCallbackView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes: tuple[type, ...] = ()
    service_class = GmailOAuthService

    @extend_schema(
        tags=("Gmail OAuth",),
        operation_id="gmail_oauth_callback",
        summary="Complete Gmail authorization",
        description=(
            "Google redirects here. The endpoint verifies and consumes OAuth state, exchanges "
            "the code server-side, stores encrypted credentials, then returns to the mobile app."
        ),
        parameters=[
            OpenApiParameter("code", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("state", str, OpenApiParameter.QUERY, required=True),
            OpenApiParameter("error", str, OpenApiParameter.QUERY, required=False),
        ],
        responses={302: OpenApiResponse(description="Redirect to the trusted mobile callback.")},
    )
    def get(self, request: Request) -> Response:
        serializer = GmailCallbackQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        service = self.service_class()
        if values.get("error"):
            try:
                state = service.state_service.consume(values["state"])
            except InvalidOAuthState as exc:
                raise ValidationError({"state": str(exc)}) from exc
            response = Response(status=302)
            response["Location"] = _callback_redirect(
                state.client_redirect_uri,
                status="error",
                error="Google authorization was cancelled.",
            )
            return response

        try:
            connection = service.complete(code=values["code"], signed_state=values["state"])
        except InvalidOAuthState as exc:
            raise ValidationError({"state": str(exc)}) from exc
        except EmailAccountServiceError as exc:
            raise OAuthServiceUnavailable from exc
        response = Response(status=302)
        sync_gmail_account.delay(str(connection.account.uuid), False)
        response["Location"] = _callback_redirect(
            connection.client_redirect_uri,
            status="success",
            account_uuid=str(connection.account.uuid),
            email=connection.account.email_address,
        )
        return response


class GmailSyncView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=("Gmail OAuth",),
        operation_id="gmail_sync_start",
        summary="Queue Gmail synchronization",
        request=None,
        responses={202: OpenApiResponse(description="Synchronization queued")},
    )
    def post(self, request: Request, account_uuid: str) -> Response:
        account = EmailAccount.objects.filter(
            uuid=account_uuid,
            user=request.user,
        ).first()
        if account is None:
            raise ValidationError({"account_uuid": "Gmail account not found."})
        sync_gmail_account.delay(str(account.uuid), True)
        return Response({"status": "queued"}, status=status.HTTP_202_ACCEPTED)
