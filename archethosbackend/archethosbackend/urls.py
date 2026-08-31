"""Root URL configuration."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from archethosbackend.apps.api.views import api_not_found, api_server_error, health

urlpatterns = [
    # Django Admin is for development and superuser rescue only; the REST API is
    # the CMS (DEVELOPMENT_PLAN.md §12 roadmap).
    path("django-admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/v1/", include("archethosbackend.apps.api.v1.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/schema/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/v1/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

if settings.DEBUG:
    # In production the media root is served by the web server / CDN, not Django.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Unmatched /api/ URLs and unhandled 500s answer with the JSON envelope rather
# than Django's HTML error pages.
handler404 = api_not_found
handler500 = api_server_error
