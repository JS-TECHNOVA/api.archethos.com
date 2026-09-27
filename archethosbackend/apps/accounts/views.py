from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Group, Permission
from django.conf import settings
from django.middleware.csrf import get_token
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema

from .models import AuditLog
from .serializers import AuditLogSerializer, CSRFResponseSerializer, GroupSerializer, LoginRequestSerializer, LoginResponseSerializer, MeResponseSerializer, PermissionSerializer, RefreshResponseSerializer, StaffUserSerializer


class StaffUserPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_staff:
            return False
        return request.method in ("GET", "HEAD", "OPTIONS") or request.user.is_superuser


def set_auth_cookies(response, refresh):
    cookie_options = {
        "httponly": True,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
        "secure": settings.AUTH_COOKIE_SECURE,
        "domain": settings.AUTH_COOKIE_DOMAIN,
    }
    response.set_cookie(settings.AUTH_COOKIE_ACCESS_NAME, str(refresh.access_token), path="/api/", **cookie_options)
    response.set_cookie(settings.AUTH_COOKIE_REFRESH_NAME, str(refresh), path="/api/v1/auth/", **cookie_options)
    return response


@extend_schema(tags=["Authentication"])
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(request=LoginRequestSerializer, responses={200: LoginResponseSerializer})
    def post(self, request):
        user = authenticate(
            request,
            username=request.data.get("username") or request.data.get("email"),
            password=request.data.get("password"),
        )
        if not user:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        return set_auth_cookies(Response({"id": user.id, "username": user.username}), RefreshToken.for_user(user))


@extend_schema(tags=["Authentication"])
class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={200: RefreshResponseSerializer})
    def post(self, request):
        raw_token = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH_NAME)
        if not raw_token:
            return Response({"detail": "No refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            refresh = RefreshToken(raw_token)
        except Exception:
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
        return set_auth_cookies(Response({"refreshed": True}), refresh)


@extend_schema(tags=["Authentication"])
class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(settings.AUTH_COOKIE_ACCESS_NAME, path="/api/", domain=settings.AUTH_COOKIE_DOMAIN)
        response.delete_cookie(settings.AUTH_COOKIE_REFRESH_NAME, path="/api/v1/auth/", domain=settings.AUTH_COOKIE_DOMAIN)
        return response


@extend_schema(tags=["Authentication"])
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=MeResponseSerializer)
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


@extend_schema(tags=["Authentication"])
class CSRFView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses=CSRFResponseSerializer)
    def get(self, request):
        return Response({"csrftoken": get_token(request)})


@extend_schema(tags=["Users"])
class StaffUserListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [StaffUserPermission]
    queryset = get_user_model().objects.filter(is_staff=True).prefetch_related("groups")
    serializer_class = StaffUserSerializer


@extend_schema(tags=["Users"])
class StaffUserDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [StaffUserPermission]
    queryset = get_user_model().objects.filter(is_staff=True).prefetch_related("groups")
    serializer_class = StaffUserSerializer


@extend_schema(tags=["Groups"])
class GroupListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdminUser]
    queryset = Group.objects.prefetch_related("permissions")
    serializer_class = GroupSerializer


@extend_schema(tags=["Groups"])
class GroupDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminUser]
    queryset = Group.objects.prefetch_related("permissions")
    serializer_class = GroupSerializer


@extend_schema(tags=["Permissions"])
class PermissionListAPIView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    queryset = Permission.objects.select_related("content_type").order_by("content_type__app_label", "codename")
    serializer_class = PermissionSerializer


@extend_schema(tags=["Audit log"])
class AuditLogListAPIView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    queryset = AuditLog.objects.select_related("actor")
    serializer_class = AuditLogSerializer
