"""Routes for /api/v1/auth/."""

from django.urls import path

from archethosbackend.apps.accounts.views import (
    CSRFView,
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    RefreshView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("password/change/", PasswordChangeView.as_view(), name="password-change"),
    path("csrf/", CSRFView.as_view(), name="csrf"),
]
