"""Local development settings."""

from .base import *  # noqa: F401,F403
from .base import REST_FRAMEWORK, INSTALLED_APPS

DEBUG = True

INSTALLED_APPS = INSTALLED_APPS + ["django_extensions"]

# The browsable API is convenient locally but must never ship to production,
# where it would render the envelope through a template instead of as JSON.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": [
        *REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"],
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# django_ratelimit refuses a per-process cache, and it is right to in production
# — three gunicorn workers keeping three counters makes every limit a lie. Here
# there is one process, so LocMemCache is genuinely shared with everything that
# can read it. Silenced rather than papered over with a real cache, because a dev
# machine should not need `createcachetable` before it can serve a request.
SILENCED_SYSTEM_CHECKS = [
    "django_ratelimit.E003",
    "django_ratelimit.W001",
]
