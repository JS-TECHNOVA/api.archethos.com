"""
CMS user, group and permission management.

Class-based views only — no ViewSets, no routers, no @action
(DEVELOPMENT_PLAN.md §2.8). Operations that would have been router actions are
their own small view classes: UserDeactivateAPIView, UserActivateAPIView,
UserSetPasswordAPIView.

Users are never deleted, only deactivated: an account may own blog posts and
audit history, and deactivation is reversible where a delete is not.
"""

from collections import defaultdict

import django_filters
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models import Count, Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from archethosbackend.apps.api.generics import (
    AdminListCreateAPIView,
    AdminRetrieveUpdateAPIView,
)
from archethosbackend.apps.api.permissions import HasModelPermission

from .admin_serializers import (
    GroupDetailSerializer,
    GroupListSerializer,
    GroupWriteSerializer,
    PermissionSerializer,
    SetPasswordSerializer,
    UserDetailSerializer,
    UserListSerializer,
    UserWriteSerializer,
    _is_last_active_superuser,
)

User = get_user_model()


# ─── Filters ─────────────────────────────────────────────────────────────────


class UserFilterSet(django_filters.FilterSet):
    group = django_filters.NumberFilter(field_name="groups__id")

    class Meta:
        model = User
        fields = ["is_active", "is_staff", "is_superuser", "group"]


# ─── Users ───────────────────────────────────────────────────────────────────


class UserListCreateAPIView(AdminListCreateAPIView):
    ordering = ["-date_joined", "-id"]
    queryset = User.objects.all().prefetch_related("groups").order_by("-date_joined")
    list_serializer_class = UserListSerializer
    write_serializer_class = UserWriteSerializer
    filterset_class = UserFilterSet
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["email", "date_joined", "last_login", "is_active"]

    @extend_schema(tags=["admin:users"], summary="List CMS users")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=["admin:users"],
        summary="Create a CMS user",
        description=(
            "Administrator-only account creation; there is no self-registration. "
            "`username` is derived from the email address."
        ),
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class UserDetailAPIView(AdminRetrieveUpdateAPIView):
    """Retrieve and update. Deliberately no DELETE — see module docstring."""

    queryset = User.objects.all().prefetch_related(
        "groups",
        Prefetch(
            "user_permissions",
            queryset=Permission.objects.select_related("content_type"),
        ),
    )
    detail_serializer_class = UserDetailSerializer
    write_serializer_class = UserWriteSerializer

    @extend_schema(tags=["admin:users"], summary="Retrieve a CMS user")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:users"], summary="Update a CMS user")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class _UserActivationAPIView(APIView):
    permission_classes = [IsAuthenticated, HasModelPermission]
    required_permissions = ["auth.change_user"]
    target_active = True

    def post(self, request, pk):
        user = generics.get_object_or_404(User, pk=pk)

        if not self.target_active:
            if user.pk == request.user.pk:
                return self._error("You cannot deactivate your own account.")
            if user.is_superuser and _is_last_active_superuser(user):
                return self._error("The last active superuser cannot be deactivated.")

        if user.is_active != self.target_active:
            user.is_active = self.target_active
            user.save(update_fields=["is_active"])

        return Response(UserDetailSerializer(user).data)

    @staticmethod
    def _error(message):
        return Response(
            {
                "success": False,
                "message": message,
                "errors": {"is_active": [message]},
                "code": "not_allowed",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class UserDeactivateAPIView(_UserActivationAPIView):
    target_active = False
    envelope_message = "User deactivated"

    @extend_schema(
        tags=["admin:users"],
        summary="Deactivate a user",
        request=None,
        responses={200: UserDetailSerializer},
    )
    def post(self, request, pk):
        return super().post(request, pk)


class UserActivateAPIView(_UserActivationAPIView):
    target_active = True
    envelope_message = "User activated"

    @extend_schema(
        tags=["admin:users"],
        summary="Reactivate a user",
        request=None,
        responses={200: UserDetailSerializer},
    )
    def post(self, request, pk):
        return super().post(request, pk)


class UserSetPasswordAPIView(APIView):
    """An administrator resetting someone else's password.

    Distinct from /auth/password/change/, which is a user changing their own and
    therefore requires the current password.
    """

    permission_classes = [IsAuthenticated, HasModelPermission]
    required_permissions = ["auth.change_user"]
    envelope_message = "Password set"

    @extend_schema(
        tags=["admin:users"],
        summary="Set a user's password",
        request=SetPasswordSerializer,
        responses={200: None},
    )
    def post(self, request, pk):
        user = generics.get_object_or_404(User, pk=pk)
        serializer = SetPasswordSerializer(
            data=request.data, context={"request": request, "target_user": user}
        )
        serializer.is_valid(raise_exception=True)

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"updated": True})


# ─── Groups ──────────────────────────────────────────────────────────────────


class GroupListCreateAPIView(AdminListCreateAPIView):
    ordering = ["name", "id"]
    queryset = Group.objects.annotate(
        permissions_count=Count("permissions", distinct=True),
        users_count=Count("user", distinct=True),
    ).order_by("name")
    list_serializer_class = GroupListSerializer
    write_serializer_class = GroupWriteSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "permissions_count", "users_count"]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    @extend_schema(tags=["admin:groups"], summary="List groups")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:groups"], summary="Create a group")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class GroupDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Group.objects.prefetch_related(
        Prefetch(
            "permissions", queryset=Permission.objects.select_related("content_type")
        )
    )
    permission_classes = UserDetailAPIView.permission_classes

    def get_serializer_class(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return GroupDetailSerializer
        return GroupWriteSerializer

    @extend_schema(tags=["admin:groups"], summary="Retrieve a group")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:groups"], summary="Update a group")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(tags=["admin:groups"], summary="Delete a group")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# ─── Permissions ─────────────────────────────────────────────────────────────


class PermissionListAPIView(APIView):
    """Read-only catalogue of assignable permissions.

    Returned grouped by app and model, which is the shape the group-editing UI
    needs — a flat list of several hundred rows is unusable in a picker.

    Not paginated: the whole catalogue is the point, and it is a few hundred rows
    at most.
    """

    permission_classes = [IsAuthenticated, HasModelPermission]
    required_permissions = ["auth.view_permission"]
    envelope_message = "Permissions retrieved successfully"

    #: Permissions for Django's own plumbing are noise in a CMS picker.
    HIDDEN_APPS = {"contenttypes", "sessions", "admin", "token_blacklist"}

    @extend_schema(
        tags=["admin:permissions"],
        summary="List assignable permissions",
        responses={200: PermissionSerializer(many=True)},
        description="Grouped by app label and model.",
    )
    def get(self, request):
        queryset = (
            Permission.objects.select_related("content_type")
            .exclude(content_type__app_label__in=self.HIDDEN_APPS)
            .order_by("content_type__app_label", "content_type__model", "codename")
        )

        grouped = defaultdict(lambda: defaultdict(list))
        for permission in queryset:
            app = permission.content_type.app_label
            model = permission.content_type.model
            grouped[app][model].append(
                {
                    "id": permission.id,
                    "codename": permission.codename,
                    "codename_full": f"{app}.{permission.codename}",
                    "name": permission.name,
                }
            )

        return Response(
            {
                app: {model: perms for model, perms in models.items()}
                for app, models in grouped.items()
            }
        )
