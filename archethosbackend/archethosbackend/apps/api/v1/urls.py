"""
API v1 route tree.

Versioning is expressed entirely through this URL prefix; DRF's versioning
classes add nothing on top of it and are deliberately unused.

    /api/v1/auth/     authentication (Phase 3)
    /api/v1/admin/    protected CMS management (Phases 4-9)
    /api/v1/public/   unauthenticated read-only content (Phases 7, 10, 11)
"""

from django.urls import include, path

app_name = "v1"

urlpatterns = [
    path("auth/", include(("archethosbackend.apps.api.v1.auth_urls", "auth"))),
    path("admin/", include(("archethosbackend.apps.api.v1.admin_urls", "admin"))),
    path("public/", include(("archethosbackend.apps.api.v1.public_urls", "public"))),
]
