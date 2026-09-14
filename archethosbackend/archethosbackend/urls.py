"""Root URL configuration for the reset project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny

from apps.core.views import api_not_found, api_server_error, health


class SwaggerView(SpectacularSwaggerView):
    schema = None
    authentication_classes = []
    permission_classes = [AllowAny]


class SchemaView(SpectacularAPIView):
    schema = None
    authentication_classes = []
    permission_classes = [AllowAny]


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/media/", include("apps.media_library.urls")),
    path("api/v1/public/", include("apps.public_api.urls")),
    path("api/v1/", include("apps.blogs.urls")),
    path("api/v1/", include("apps.projects.urls")),
    path("api/v1/", include("apps.services.urls")),
    path("api/v1/", include("apps.home.urls")),
    path("api/v1/", include("apps.about.urls")),
    path("api/v1/", include("apps.contact.urls")),
    path("api/v1/", include("apps.pages.urls")),
    path("api/v1/", include("apps.master.urls")),
    path("api/schema/", SchemaView.as_view(), name="schema"),
    path("api/docs/", SwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = api_not_found
handler500 = api_server_error
