from django.contrib.auth import authenticate
from django.conf import settings
from django.middleware.csrf import get_token
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken


def set_auth_cookies(response, refresh):
    cookie_options = {
        "httponly": True,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
        "secure": settings.AUTH_COOKIE_SECURE,
        "domain": settings.AUTH_COOKIE_DOMAIN,
    }
    response.set_cookie(settings.AUTH_COOKIE_ACCESS_NAME, str(refresh.access_token), path="/api/", **cookie_options)
    response.set_cookie(settings.AUTH_COOKIE_REFRESH_NAME, str(refresh), path="/api/auth/", **cookie_options)
    return response


class LoginView(APIView):
    schema = None
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        user = authenticate(
            request,
            username=request.data.get("username") or request.data.get("email"),
            password=request.data.get("password"),
        )
        if not user:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        return set_auth_cookies(Response({"id": user.id, "username": user.username}), RefreshToken.for_user(user))


class RefreshView(APIView):
    schema = None
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw_token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH_NAME)
        if not raw_token:
            return Response({"detail": "No refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            refresh = RefreshToken(raw_token)
        except Exception:
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
        return set_auth_cookies(Response({"refreshed": True}), refresh)


class LogoutView(APIView):
    schema = None
    permission_classes = [AllowAny]

    def post(self, request):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(settings.AUTH_COOKIE_ACCESS_NAME, path="/api/", domain=settings.AUTH_COOKIE_DOMAIN)
        response.delete_cookie(settings.AUTH_COOKIE_REFRESH_NAME, path="/api/auth/", domain=settings.AUTH_COOKIE_DOMAIN)
        return response


class MeView(APIView):
    schema = None
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "groups": list(user.groups.order_by("name").values("id", "name")),
            "permissions": sorted(user.get_all_permissions()),
        })


class CSRFView(APIView):
    schema = None
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrftoken": get_token(request)})
