"""
Base Django settings for the Archethos headless CMS.

Environment-specific overrides live in development.py / production.py / test.py.
Every deployment-varying value is read from the repo-root .env via django-environ.

See DEVELOPMENT_PLAN.md for the architecture this configuration serves.
"""

from pathlib import Path

import environ

# ─── Paths ───────────────────────────────────────────────────────────────────
# base.py -> settings/ -> archethosbackend/ -> archethosbackend/ (holds manage.py)
BASE_DIR = Path(__file__).resolve().parents[2]
# The repository root, which holds .env, docker-compose.yml and requirements/.
REPO_ROOT = BASE_DIR.parent

env = environ.Env()
environ.Env.read_env(REPO_ROOT / ".env")

# ─── Core ────────────────────────────────────────────────────────────────────
SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# ─── Applications ────────────────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
]

LOCAL_APPS = [
    "archethosbackend.apps.core",
    "archethosbackend.apps.accounts",
    "archethosbackend.apps.audit",
    "archethosbackend.apps.media_library",
    "archethosbackend.apps.content",
    "archethosbackend.apps.sections",
    "archethosbackend.apps.pages",
    "archethosbackend.apps.enquiries",
    "archethosbackend.apps.api",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # CorsMiddleware must precede CommonMiddleware so it can answer preflights.
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "archethosbackend.urls"
WSGI_APPLICATION = "archethosbackend.wsgi.application"
ASGI_APPLICATION = "archethosbackend.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ─── Database ────────────────────────────────────────────────────────────────
# PostgreSQL runs in Docker (see docker-compose.yml); DB_* is shared by both.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="5432"),
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=60),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django's built-in auth.User is used as-is. One login field accepts either an
# email address or a username; EmailOrUsernameBackend inspects the identifier
# and queries the matching column. A case-insensitive unique index on
# auth_user.email (accounts/migrations/0001) keeps email login unambiguous.
#
# ModelBackend is deliberately NOT listed. It subclasses cleanly into
# EmailOrUsernameBackend (which is where the permission machinery comes
# from), and leaving it in the chain would defeat the whole point: when this
# backend correctly refuses an email-shaped identifier, Django would fall
# through to ModelBackend, match the *username* column, and let a user whose
# username equals someone else's email address in. A test pins that.
AUTHENTICATION_BACKENDS = [
    "archethosbackend.apps.accounts.backends.EmailOrUsernameBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── i18n ────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

# ─── Static & media ──────────────────────────────────────────────────────────
STATIC_URL = "static/"
STATIC_ROOT = REPO_ROOT / "staticfiles"

MEDIA_URL = env("MEDIA_URL", default="/media/")
MEDIA_ROOT = REPO_ROOT / "media"

# Uploads are validated against these in the media library (Phase 6).
MAX_UPLOAD_SIZE_MB = env.int("MAX_UPLOAD_SIZE_MB", default=20)

# ─── Django REST Framework ───────────────────────────────────────────────────
# API versioning is expressed purely through the URL prefix (/api/v1/); DRF's
# versioning machinery buys nothing on top of that and is deliberately unused.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "archethosbackend.apps.accounts.authentication.CookieJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        # Deny by default; public endpoints opt out explicitly with AllowAny.
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "archethosbackend.apps.api.renderers.EnvelopeJSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "archethosbackend.apps.api.pagination.EnvelopePageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "EXCEPTION_HANDLER": "archethosbackend.apps.api.exceptions.envelope_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "UNAUTHENTICATED_USER": "django.contrib.auth.models.AnonymousUser",
}

# ─── JWT ─────────────────────────────────────────────────────────────────────
from datetime import timedelta  # noqa: E402  (kept beside the settings it feeds)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("ACCESS_TOKEN_LIFETIME_MINUTES", default=15)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env.int("REFRESH_TOKEN_LIFETIME_DAYS", default=7)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_TYPE_CLAIM": "token_type",
}

# ─── Auth cookies ────────────────────────────────────────────────────────────
# Tokens are delivered to the browser only as HttpOnly cookies; the frontend
# never reads or stores them. See DEVELOPMENT_PLAN.md §7.
AUTH_COOKIE_ACCESS_NAME = "access_token"
AUTH_COOKIE_REFRESH_NAME = "refresh_token"
AUTH_COOKIE_SECURE = env.bool("AUTH_COOKIE_SECURE", default=False)
AUTH_COOKIE_SAMESITE = env("AUTH_COOKIE_SAMESITE", default="Lax")
AUTH_COOKIE_DOMAIN = env("AUTH_COOKIE_DOMAIN", default=None) or None
AUTH_COOKIE_ACCESS_PATH = "/api/"
# Scoped so the refresh token is never transmitted on ordinary API calls.
AUTH_COOKIE_REFRESH_PATH = "/api/v1/auth/"

# ─── CORS / CSRF ─────────────────────────────────────────────────────────────
# Cookie auth requires credentialed CORS, which forbids a wildcard origin.
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = (
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
)

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
# The frontend must read this cookie to echo it back in the X-CSRFToken header.
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = AUTH_COOKIE_SAMESITE
CSRF_COOKIE_SECURE = AUTH_COOKIE_SECURE

SESSION_COOKIE_SECURE = AUTH_COOKIE_SECURE
SESSION_COOKIE_SAMESITE = AUTH_COOKIE_SAMESITE

# ─── OpenAPI schema ──────────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "Archethos CMS API",
    "DESCRIPTION": (
        "Headless CMS for the Archethos architecture studio website. "
        "Routes are grouped as /api/v1/auth/, /api/v1/admin/ and /api/v1/public/."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/v1",
    "SORT_OPERATIONS": False,
}

# ─── Logging ─────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {
        "django.db.backends": {"level": "INFO", "handlers": ["console"], "propagate": False},
    },
}
