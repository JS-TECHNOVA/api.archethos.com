"""
Rate limiting.

The bug these exist to prevent is specific and was live: `django_ratelimit`'s
default reads `REMOTE_ADDR`, gunicorn leaves that empty behind a unix socket, and
the library raises rather than degrading — so the enquiry endpoint answered 500
in production while every test passed on `runserver`. `client_ip` is tested
against that exact environment, not against a request that has an address.
"""

from unittest.mock import Mock

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from archethosbackend.apps.api.ratelimit import (
    UNKNOWN_CLIENT,
    client_ip,
    login_identifier,
)

PASSWORD = "correct-horse-battery-staple"


def request_with(**meta):
    return Mock(META=meta, data={})


class ClientIPTests(TestCase):
    """Which header is believed, and what happens when none of them are there."""

    def test_the_trusted_header_wins_when_configured(self):
        with override_settings(RATELIMIT_TRUSTED_IP_HEADER="HTTP_CF_CONNECTING_IP"):
            ip = client_ip(
                request_with(
                    HTTP_CF_CONNECTING_IP="203.0.113.7",
                    HTTP_X_FORWARDED_FOR="198.51.100.1, 172.16.0.4",
                    REMOTE_ADDR="10.0.0.1",
                )
            )
        self.assertEqual(ip, "203.0.113.7")

    def test_forwarded_for_uses_the_last_entry(self):
        """nginx appends its own peer, so the last hop is the one we control.

        Earlier entries are whatever the client sent and are forgeable.
        """
        ip = client_ip(
            request_with(HTTP_X_FORWARDED_FOR="1.2.3.4, 198.51.100.1, 172.16.0.4")
        )
        self.assertEqual(ip, "172.16.0.4")

    def test_remote_addr_is_the_last_resort(self):
        self.assertEqual(client_ip(request_with(REMOTE_ADDR="10.0.0.1")), "10.0.0.1")

    def test_an_empty_remote_addr_does_not_raise(self):
        """The production failure, reproduced.

        gunicorn behind a unix socket sets REMOTE_ADDR to "". The stock resolver
        raises ImproperlyConfigured here, which is a 500 on every call.
        """
        with self.assertLogs("archethosbackend.apps.api.ratelimit", "ERROR"):
            self.assertEqual(client_ip(request_with(REMOTE_ADDR="")), UNKNOWN_CLIENT)

    def test_no_headers_at_all_does_not_raise(self):
        with self.assertLogs("archethosbackend.apps.api.ratelimit", "ERROR"):
            self.assertEqual(client_ip(request_with()), UNKNOWN_CLIENT)

    def test_a_trusted_header_that_is_absent_falls_through(self):
        with override_settings(RATELIMIT_TRUSTED_IP_HEADER="HTTP_CF_CONNECTING_IP"):
            self.assertEqual(
                client_ip(request_with(REMOTE_ADDR="10.0.0.1")), "10.0.0.1"
            )


class LoginIdentifierTests(TestCase):
    def test_case_and_whitespace_share_one_bucket(self):
        a = login_identifier("g", Mock(data={"email": "  Root@Archethos.test "}))
        b = login_identifier("g", Mock(data={"email": "root@archethos.test"}))
        self.assertEqual(a, b)

    def test_username_is_accepted_as_the_alias(self):
        self.assertEqual(
            login_identifier("g", Mock(data={"username": "elsker"})), "elsker"
        )

    def test_a_missing_identifier_gets_its_own_bucket(self):
        self.assertEqual(login_identifier("g", Mock(data={})), "<blank>")


@override_settings(
    RATELIMIT_ENABLE=True,
    RATELIMIT_LOGIN_IP="3/m",
    RATELIMIT_LOGIN_USER="2/m",
)
class LoginThrottleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="root@archethos.test",
            email="root@archethos.test",
            password=PASSWORD,
        )

    def setUp(self):
        # Counters live in the cache, which outlives a transaction rollback.
        cache.clear()

    def attempt(self, password, ip="203.0.113.1", email=None):
        return Client().post(
            reverse("v1:auth:login"),
            {"email": email or self.user.email, "password": password},
            content_type="application/json",
            REMOTE_ADDR=ip,
        )

    def test_repeated_failures_are_eventually_refused(self):
        seen = [self.attempt("wrong").status_code for _ in range(6)]

        self.assertIn(429, seen, seen)
        self.assertEqual(seen[0], 400, "the first attempt should be answered normally")

    def test_the_refusal_is_the_standard_envelope(self):
        for _ in range(6):
            response = self.attempt("wrong")
            if response.status_code == 429:
                break

        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["code"], "throttled")
        self.assertIn("Too many", body["message"])

    def test_a_correct_password_does_not_spend_the_budget(self):
        """Logging in repeatedly is not an attack, and must not lock anyone out."""
        for _ in range(10):
            response = self.attempt(PASSWORD)
            self.assertEqual(response.status_code, 200, response.content)

    def test_one_account_is_capped_across_many_addresses(self):
        """The per-IP limit alone would let a botnet spread under it."""
        codes = [
            self.attempt("wrong", ip=f"203.0.113.{n}").status_code
            for n in range(1, 8)
        ]
        self.assertIn(429, codes, codes)

    def test_a_different_account_is_unaffected(self):
        other = User.objects.create_user(
            username="editor@archethos.test",
            email="editor@archethos.test",
            password=PASSWORD,
        )
        for _ in range(6):
            self.attempt("wrong")

        response = self.attempt(PASSWORD, ip="198.51.100.9", email=other.email)
        self.assertEqual(response.status_code, 200, response.content)


class ConfigurationTests(TestCase):
    """Rates are configuration, and the resolver is wired in."""

    def test_every_rate_is_read_from_the_environment(self):
        for name in (
            "RATELIMIT_LOGIN_IP",
            "RATELIMIT_LOGIN_USER",
            "RATELIMIT_REFRESH",
            "RATELIMIT_PASSWORD_CHANGE",
            "RATELIMIT_ENQUIRY",
        ):
            with self.subTest(setting=name):
                self.assertTrue(hasattr(settings, name), f"{name} is not defined")

    def test_the_ip_resolver_is_our_own(self):
        """Pins the fix. The stock resolver is what raised in production."""
        self.assertEqual(
            settings.RATELIMIT_IP_META_KEY,
            "archethosbackend.apps.api.ratelimit.client_ip",
        )

    def test_an_empty_rate_disables_that_limit(self):
        """`RATELIMIT_ENQUIRY=` in .env should switch it off, not crash."""
        with override_settings(RATELIMIT_ENABLE=True, RATELIMIT_ENQUIRY=""):
            cache.clear()
            for _ in range(12):
                response = Client().post(
                    reverse("v1:public:enquiry-submit"),
                    {
                        "name": "A Visitor",
                        "email": "visitor@example.com",
                        "message": "Hello, I would like to discuss a project.",
                    },
                    content_type="application/json",
                    REMOTE_ADDR="203.0.113.5",
                )
            self.assertEqual(response.status_code, 201, response.content)
