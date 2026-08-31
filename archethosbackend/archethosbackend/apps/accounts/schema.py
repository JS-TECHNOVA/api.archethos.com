"""Teaches drf-spectacular how CookieJWTAuthentication authenticates.

Without this the generated schema omits the security scheme entirely and the
docs page offers no way to describe how a client authenticates.
"""

from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CookieJWTScheme(OpenApiAuthenticationExtension):
    target_class = "archethosbackend.apps.accounts.authentication.CookieJWTAuthentication"
    name = "cookieAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": settings.AUTH_COOKIE_ACCESS_NAME,
            "description": (
                "HttpOnly cookie set by POST /api/v1/auth/login/. Browsers send it "
                "automatically when the request uses credentials: 'include'. Unsafe "
                "methods additionally require the X-CSRFToken header."
            ),
        }
