from django.urls import path

from .views import AuditLogListAPIView, CSRFView, GroupDetailAPIView, GroupListCreateAPIView, LoginView, LogoutView, MeView, PermissionListAPIView, RefreshView, StaffUserDetailAPIView, StaffUserListCreateAPIView

urlpatterns = [
    path("login/", LoginView.as_view()),
    path("refresh/", RefreshView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("me/", MeView.as_view()),
    path("csrf/", CSRFView.as_view()),
    path("users/", StaffUserListCreateAPIView.as_view()),
    path("users/<int:pk>/", StaffUserDetailAPIView.as_view()),
    path("groups/", GroupListCreateAPIView.as_view()),
    path("groups/<int:pk>/", GroupDetailAPIView.as_view()),
    path("permissions/", PermissionListAPIView.as_view()),
    path("audit-log/", AuditLogListAPIView.as_view()),
]
