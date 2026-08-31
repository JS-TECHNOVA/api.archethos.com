"""Test settings: faster hashing, isolated media root, no throttling noise."""

import tempfile

from .base import *  # noqa: F401,F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Upload tests write real files. Without this they accumulate in the project's
# media/ directory, which the test database teardown does not clean up.
MEDIA_ROOT = tempfile.mkdtemp(prefix="archethos-test-media-")
