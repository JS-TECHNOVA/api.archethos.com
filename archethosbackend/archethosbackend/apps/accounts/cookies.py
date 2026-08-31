"""
Auth cookie helpers.

Tokens reach the browser only as HttpOnly cookies. The frontend never reads,
stores or attaches them — it just sends requests with `credentials: "include"`.

The refresh cookie is scoped to /api/v1/auth/ so it is not transmitted on
ordinary API calls, which keeps it off the wire for the vast majority of
requests (DEVELOPMENT_PLAN.md §7).
"""

from django.conf import settings


def set_auth_cookies(response, access_token, refresh_token=None):
    response.set_cookie(
        settings.AUTH_COOKIE_ACCESS_NAME,
        str(access_token),
        max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path=settings.AUTH_COOKIE_ACCESS_PATH,
    )

    if refresh_token is not None:
        response.set_cookie(
            settings.AUTH_COOKIE_REFRESH_NAME,
            str(refresh_token),
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            domain=settings.AUTH_COOKIE_DOMAIN,
            path=settings.AUTH_COOKIE_REFRESH_PATH,
        )

    return response


def clear_auth_cookies(response):
    """Delete both cookies.

    The path must match the one used when setting, or the browser keeps the
    cookie and the user appears stuck in a broken session.
    """
    response.delete_cookie(
        settings.AUTH_COOKIE_ACCESS_NAME,
        path=settings.AUTH_COOKIE_ACCESS_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        settings.AUTH_COOKIE_REFRESH_NAME,
        path=settings.AUTH_COOKIE_REFRESH_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )
    return response
