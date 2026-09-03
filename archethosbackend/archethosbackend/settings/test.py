"""Test settings: faster hashing, isolated media root, no throttling noise."""

import tempfile

from .base import *  # noqa: F401,F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Upload tests write real files. Without this they accumulate in the project's
# media/ directory, which the test database teardown does not clean up.
MEDIA_ROOT = tempfile.mkdtemp(prefix="archethos-test-media-")

# Off by default so unrelated tests are not throttled by their own setUp. The
# rate limit tests turn it back on with override_settings, which is also what
# proves it can be turned on.
RATELIMIT_ENABLE = False

# django_ratelimit refuses a per-process cache, and it is right to in production
# — three gunicorn workers keeping three counters makes every limit a lie. Here
# there is one process, so LocMemCache is genuinely shared with everything that
# can read it. Silenced rather than papered over with a real cache, because a dev
# machine should not need `createcachetable` before it can serve a request.
SILENCED_SYSTEM_CHECKS = [
    "django_ratelimit.E003",
    "django_ratelimit.W001",
]
