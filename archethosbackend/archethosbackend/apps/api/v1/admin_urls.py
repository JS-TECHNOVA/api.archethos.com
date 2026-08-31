"""
Routes for /api/v1/admin/.

Every route is written out explicitly — no routers anywhere in this project
(DEVELOPMENT_PLAN.md §2.8).
"""

from django.urls import path

from archethosbackend.apps.media_library.views import (
    MediaDetailAPIView,
    MediaDuplicateCheckAPIView,
    MediaListAPIView,
    MediaUploadAPIView,
    MediaUsageAPIView,
    MediaYouTubeAPIView,
)

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
    # Media library.  Upload and YouTube are separate endpoints rather than modes
    # of one create view: they take different payloads (multipart vs JSON) and
    # share nothing but the table they write to.
    path("media/", MediaListAPIView.as_view(), name="media-list"),
    path("media/upload/", MediaUploadAPIView.as_view(), name="media-upload"),
    path("media/youtube/", MediaYouTubeAPIView.as_view(), name="media-youtube"),
    path(
        "media/check-duplicate/",
        MediaDuplicateCheckAPIView.as_view(),
        name="media-check-duplicate",
    ),
    path("media/<int:pk>/", MediaDetailAPIView.as_view(), name="media-detail"),
    path("media/<int:pk>/usage/", MediaUsageAPIView.as_view(), name="media-usage"),
]
