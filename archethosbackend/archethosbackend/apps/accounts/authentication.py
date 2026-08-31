"""
Cookie-based JWT authentication.

Reads the access token from an HttpOnly cookie instead of the Authorization
header, so the Next.js frontend never handles token values.

Because the browser attaches the cookie automatically, this authentication is
CSRF-relevant in a way that header-based JWT is not: a cross-site form POST
would otherwise be authenticated. CSRF is therefore enforced on unsafe methods
exactly as DRF's SessionAuthentication does. It is never disabled.

A Bearer header is still accepted as a fallback for non-browser clients (CI,
scripts, server-to-server); those carry no ambient cookie, so no CSRF check
applies to them.
"""

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


class _CSRFCheck(CsrfViewMiddleware):
    def _reject(self, request, reason):
        return reason


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        raw_token = request.COOKIES.get(settings.AUTH_COOKIE_ACCESS_NAME)
        from_cookie = raw_token is not None

        if not from_cookie:
            header = self.get_header(request)
            if header is None:
                return None
            raw_token = self.get_raw_token(header)
            if raw_token is None:
                return None

        # get_validated_token only accepts AUTH_TOKEN_CLASSES (AccessToken), whose
        # verify() asserts token_type == "access". A refresh token presented here
        # is therefore rejected rather than granting API access.
        validated_token = self.get_validated_token(raw_token)

        if from_cookie:
            self._enforce_csrf(request)

        return self.get_user(validated_token), validated_token

    @staticmethod
    def _enforce_csrf(request):
        if request.method in SAFE_METHODS:
            return

        check = _CSRFCheck(lambda req: None)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise exceptions.PermissionDenied(f"CSRF failed: {reason}")
