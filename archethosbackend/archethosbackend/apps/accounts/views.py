"""
Authentication endpoints.

    POST /api/v1/auth/login/            email + password -> sets both cookies
    POST /api/v1/auth/refresh/          rotates the pair from the refresh cookie
    POST /api/v1/auth/logout/           blacklists + clears
    GET  /api/v1/auth/me/               current user, groups, effective permissions
    POST /api/v1/auth/password/change/
    GET  /api/v1/auth/csrf/             seeds the csrftoken cookie

No registration endpoint exists by design: CMS accounts are created by an
administrator through /api/v1/admin/users/ (Phase 4), never self-service.
"""

from django.conf import settings
from django.middleware.csrf import get_token, rotate_token
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .cookies import clear_auth_cookies, set_auth_cookies
from .serializers import (
    CurrentUserSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    ProfileUpdateSerializer,
)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    envelope_message = "Logged in successfully"

    @extend_schema(
        tags=["auth"],
        summary="Log in",
        request=LoginSerializer,
        responses={200: CurrentUserSerializer},
        description=(
            "Sets HttpOnly access_token and refresh_token cookies. Token values "
            "are never returned in the body."
        ),
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)

        # New session identity: discard any CSRF token tied to the previous one.
        rotate_token(request)
        get_token(request)

        response = Response(
            CurrentUserSerializer(user).data,
            status=status.HTTP_200_OK,
        )
        return set_auth_cookies(response, refresh.access_token, refresh)


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    envelope_message = "Session refreshed"

    @extend_schema(
        tags=["auth"],
        summary="Refresh the session",
        request=None,
        responses={200: None},
        description=(
            "Reads the refresh_token cookie, rotates it, blacklists the old one "
            "and rewrites both cookies. Any failure returns 401 with both "
            "cookies cleared."
        ),
    )
    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH_NAME)
        if not raw_refresh:
            return self._reject("No refresh token was provided.")

        try:
            refresh = RefreshToken(raw_refresh)
            access = refresh.access_token

            # ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION: the presented
            # token is retired and a fresh one issued. There is deliberately no
            # grace window for concurrent refreshes (DEVELOPMENT_PLAN.md §2.7).
            if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS"):
                if settings.SIMPLE_JWT.get("BLACKLIST_AFTER_ROTATION"):
                    try:
                        refresh.blacklist()
                    except AttributeError:
                        pass
                refresh.set_jti()
                refresh.set_exp()
                refresh.set_iat()
                access = refresh.access_token
        except TokenError as exc:
            return self._reject(str(exc))

        response = Response({"refreshed": True}, status=status.HTTP_200_OK)
        return set_auth_cookies(response, access, refresh)

    @staticmethod
    def _reject(detail):
        response = Response(
            {
                "success": False,
                "message": "Session expired. Please log in again.",
                "errors": {"detail": detail},
                "code": "invalid_refresh_token",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )
        return clear_auth_cookies(response)


class LogoutView(APIView):
    # Deliberately AllowAny: an expired access token must not prevent logging
    # out. The refresh cookie is what actually gets invalidated.
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["auth"],
        summary="Log out",
        request=None,
        responses={204: None},
        description="Blacklists the refresh token where possible and clears both cookies.",
    )
    def post(self, request):
        raw_refresh = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH_NAME)
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except (TokenError, AttributeError):
                # Already expired, already blacklisted or malformed: logging out
                # is still a success from the client's point of view.
                pass

        response = Response(status=status.HTTP_204_NO_CONTENT)
        return clear_auth_cookies(response)


class MeView(APIView):
    permission_classes = [IsAuthenticated]
    envelope_message = "Current user retrieved successfully"

    @extend_schema(
        tags=["auth"],
        summary="Current user",
        responses={200: CurrentUserSerializer},
        description=(
            "Returns the authenticated user with their groups and full effective "
            "permission set (direct plus group-derived), for the frontend to "
            "decide which menus and actions to show."
        ),
    )
    def get(self, request):
        serializer = CurrentUserSerializer(
            request.user,
            context={"request": request},
        )
        return Response(serializer.data)

    @extend_schema(
        tags=["auth"],
        summary="Update your own profile",
        request=ProfileUpdateSerializer,
        responses={200: CurrentUserSerializer},
        description=(
            "Name and email only. `username` is a login identifier and is not "
            "editable; role and status fields are not accepted here at all."
        ),
    )
    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Return the same shape as GET, so the client can drop it straight into
        # the session cache instead of refetching.
        return Response(
            CurrentUserSerializer(request.user, context={"request": request}).data
        )


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    envelope_message = "Password changed successfully"

    @extend_schema(
        tags=["auth"],
        summary="Change own password",
        request=PasswordChangeSerializer,
        responses={200: None},
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # The password changed, so every existing session should end. Clearing
        # cookies forces a fresh login with the new credentials.
        response = Response({"changed": True}, status=status.HTTP_200_OK)
        return clear_auth_cookies(response)


class CSRFView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    envelope_message = "CSRF cookie set"

    @extend_schema(
        tags=["auth"],
        summary="Seed the CSRF cookie",
        responses={200: None},
        description=(
            "Sets the readable csrftoken cookie. The frontend calls this once on "
            "boot, then echoes the value in the X-CSRFToken header on unsafe "
            "requests."
        ),
    )
    def get(self, request):
        return Response({"csrftoken": get_token(request)})
