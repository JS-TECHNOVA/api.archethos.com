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
