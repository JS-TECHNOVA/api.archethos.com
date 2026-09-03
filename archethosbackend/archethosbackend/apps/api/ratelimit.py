"""
Rate limiting: who the caller is, and what to say when they have had enough.

Two problems this module exists to solve.

**Identifying the caller.** `django_ratelimit`'s default reads `REMOTE_ADDR`, which
gunicorn leaves empty when nginx talks to it over a unix socket — and the library
raises `ImproperlyConfigured` rather than degrading, so every rate-limited endpoint
answers 500 in production while passing every test on `runserver`. That is exactly
what happened here. `client_ip` is wired in as `RATELIMIT_IP_META_KEY` and resolves
the address from the proxy headers instead.

**Which header to trust.** Anything a client can set, a client can forge, so the
header is named in configuration rather than guessed:

* `RATELIMIT_TRUSTED_IP_HEADER=HTTP_CF_CONNECTING_IP` behind Cloudflare. Cloudflare
  overwrites this on every request, so it cannot be spoofed *through* Cloudflare —
  but it can be spoofed by anyone who reaches the origin directly. Restrict the
  origin's port 80/443 to Cloudflare's published ranges before relying on it.
* Left unset, the last entry of `X-Forwarded-For` is used: nginx appends its own
  `$remote_addr` there, so the last entry is the one hop we actually trust.

The Cloudflare case matters here. With the proxy on, that last `X-Forwarded-For`
entry is a Cloudflare edge IP, not the visitor — so every visitor arriving through
one edge would share a bucket. Setting the header is not optional in that topology.
"""

import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

#: Used when no address can be determined at all. Everyone shares this bucket,
#: which is the wrong answer — but it is a bounded wrong answer, where raising
#: would take the endpoint down entirely.
UNKNOWN_CLIENT = "0.0.0.0"


def client_ip(request):
    """The caller's address, from the most trustworthy source configured.

    Never raises. A rate limiter that 500s is worse than one that is briefly
    imprecise, and the alternative here is an endpoint that cannot be called.
    """
    header = getattr(settings, "RATELIMIT_TRUSTED_IP_HEADER", None)
    if header:
        value = request.META.get(header)
        if value:
            return value.split(",")[0].strip()

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        # nginx appends its own view of the peer, so the *last* entry is the one
        # hop we control. Earlier entries are client-supplied and forgeable.
        return forwarded.split(",")[-1].strip()

    remote = request.META.get("REMOTE_ADDR")
    if remote:
        return remote

    logger.error(
        "No client address available for rate limiting. Behind a unix socket "
        "REMOTE_ADDR is empty; set RATELIMIT_TRUSTED_IP_HEADER or ensure nginx "
        "sends X-Forwarded-For."
    )
    return UNKNOWN_CLIENT


def too_many(message):
    """The 429 body, in the same envelope as every other error."""
    return Response(
        {
            "success": False,
            "message": message,
            "errors": {},
            "code": "throttled",
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )


def limited(request, *, group, rate, key="ip", method="ALL", increment=True):
    """True when this request has exhausted `rate`.

    A thin wrapper over `is_ratelimited` so views never repeat the argument list,
    and so `RATELIMIT_ENABLE=False` is honoured in one place.

    `increment=False` asks the question without spending the allowance, which is
    how login separates "have they had too many *failures*" from "is this a
    request at all" — a working password should never cost anyone their budget.
    """
    if not getattr(settings, "RATELIMIT_ENABLE", True):
        return False

    from django_ratelimit.core import is_ratelimited

    return is_ratelimited(
        request,
        group=group,
        key=key,
        rate=rate,
        method=method,
        increment=increment,
    )


def login_identifier(group, request):
    """Bucket key for the per-account login limit.

    Case-folded and trimmed so `Foo@x.com` and `foo@x.com` cannot each get a
    full allowance against the same account. Missing or blank identifiers fall
    into one bucket, which is correct: a flood of credential-less POSTs is
    exactly what should be throttled together.
    """
    data = getattr(request, "data", None) or {}
    identifier = data.get("email") or data.get("username") or ""
    return str(identifier).strip().lower() or "<blank>"
