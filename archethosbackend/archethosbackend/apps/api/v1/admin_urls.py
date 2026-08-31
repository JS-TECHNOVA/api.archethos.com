"""
Routes for /api/v1/admin/.

Every route is written out explicitly — no routers anywhere in this project
(DEVELOPMENT_PLAN.md §2.8).
"""

from django.urls import path

from archethosbackend.apps.accounts.admin_views import (
    GroupDetailAPIView,
    GroupListCreateAPIView,
    PermissionListAPIView,
    UserActivateAPIView,
    UserDeactivateAPIView,
    UserDetailAPIView,
    UserListCreateAPIView,
    UserSetPasswordAPIView,
)

urlpatterns = [
    # Users
    path("users/", UserListCreateAPIView.as_view(), name="user-list"),
    path("users/<int:pk>/", UserDetailAPIView.as_view(), name="user-detail"),
    path(
        "users/<int:pk>/deactivate/",
        UserDeactivateAPIView.as_view(),
        name="user-deactivate",
    ),
    path("users/<int:pk>/activate/", UserActivateAPIView.as_view(), name="user-activate"),
    path(
        "users/<int:pk>/set-password/",
        UserSetPasswordAPIView.as_view(),
        name="user-set-password",
    ),
    # Groups
    path("groups/", GroupListCreateAPIView.as_view(), name="group-list"),
    path("groups/<int:pk>/", GroupDetailAPIView.as_view(), name="group-detail"),
    # Permissions (read-only catalogue)
    path("permissions/", PermissionListAPIView.as_view(), name="permission-list"),
]
