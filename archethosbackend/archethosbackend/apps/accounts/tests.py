"""Authentication flow tests.

Covers the security properties the architecture depends on, not just the happy
path: refresh tokens must not authenticate, rotated tokens must be rejected on
reuse, cookies must be HttpOnly, and CSRF must be enforced on cookie auth.
"""

from django.conf import settings
from django.contrib.auth.models import Group, Permission, User
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

ACCESS = settings.AUTH_COOKIE_ACCESS_NAME
REFRESH = settings.AUTH_COOKIE_REFRESH_NAME


class AuthFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = "correct-horse-battery-staple"
        cls.user = User.objects.create_user(
            username="editor@archethos.test",
            email="editor@archethos.test",
            password=cls.password,
            first_name="Ed",
            last_name="Itor",
        )
        # A name of its own: the bootstrap migration already creates the four
        # default CMS roles, so reusing one of those collides.
        group = Group.objects.create(name="Test Reviewers")
        group.permissions.add(
            *Permission.objects.filter(
                codename__in=["add_group", "change_group", "view_group"]
            )
        )
        cls.user.groups.add(group)

    def login(self, client=None, email=None, password=None):
        client = client or Client()
        response = client.post(
            reverse("v1:auth:login"),
            {"email": email or self.user.email, "password": password or self.password},
            content_type="application/json",
        )
        return client, response

    # ── login ────────────────────────────────────────────────────────────────

    def test_login_sets_httponly_cookies_and_hides_tokens(self):
        client, response = self.login()

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["email"], self.user.email)

        # Token values must never appear in the body.
        self.assertNotIn("access", body["data"])
        self.assertNotIn("refresh", body["data"])
        self.assertNotIn("token", str(body["data"]).lower())

        for name, path in (
            (ACCESS, settings.AUTH_COOKIE_ACCESS_PATH),
            (REFRESH, settings.AUTH_COOKIE_REFRESH_PATH),
        ):
            cookie = response.cookies[name]
            self.assertTrue(cookie["httponly"], f"{name} must be HttpOnly")
            self.assertEqual(cookie["path"], path)
            self.assertEqual(cookie["samesite"], settings.AUTH_COOKIE_SAMESITE)

    def test_login_rejects_bad_password(self):
        _, response = self.login(password="wrong")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_login_rejects_inactive_user(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        _, response = self.login()
        self.assertEqual(response.status_code, 400)

    def test_login_message_does_not_distinguish_failure_modes(self):
        _, wrong_password = self.login(password="wrong")
        _, unknown_email = self.login(email="nobody@archethos.test")
        self.assertEqual(wrong_password.json()["errors"], unknown_email.json()["errors"])

    # ── me ───────────────────────────────────────────────────────────────────

    def test_me_requires_authentication(self):
        response = Client().get(reverse("v1:auth:me"))
        self.assertEqual(response.status_code, 401)
        self.assertFalse(response.json()["success"])

    def test_me_returns_groups_and_effective_permissions(self):
        client, _ = self.login()
        data = client.get(reverse("v1:auth:me")).json()["data"]

        self.assertEqual(data["email"], self.user.email)
        self.assertEqual([g["name"] for g in data["groups"]], ["Test Reviewers"])
        # Group-derived permissions must be included, not just direct ones.
        self.assertIn("auth.change_group", data["permissions"])
        self.assertNotIn("auth.delete_group", data["permissions"])

    def test_me_expands_superuser_permissions(self):
        User.objects.filter(pk=self.user.pk).update(is_superuser=True)
        client, _ = self.login()
        permissions = client.get(reverse("v1:auth:me")).json()["data"]["permissions"]
        self.assertIn("auth.delete_user", permissions)

    # ── token type separation ────────────────────────────────────────────────

    def test_refresh_token_cannot_authenticate_api_requests(self):
        client = Client()
        refresh = RefreshToken.for_user(self.user)
        client.cookies[ACCESS] = str(refresh)

        response = client.get(reverse("v1:auth:me"))
        self.assertEqual(response.status_code, 401)

    def test_garbage_access_token_is_rejected(self):
        client = Client()
        client.cookies[ACCESS] = "not-a-jwt"
        self.assertEqual(client.get(reverse("v1:auth:me")).status_code, 401)

    # ── refresh + rotation ───────────────────────────────────────────────────

    def test_refresh_rotates_and_blacklists_the_old_token(self):
        client, login_response = self.login()
        original_refresh = login_response.cookies[REFRESH].value

        response = client.post(reverse("v1:auth:refresh"))
        self.assertEqual(response.status_code, 200)

        rotated_refresh = response.cookies[REFRESH].value
        self.assertNotEqual(rotated_refresh, original_refresh)
        self.assertEqual(BlacklistedToken.objects.count(), 1)

        # The rotated-out token must not work again.
        client.cookies[REFRESH] = original_refresh
        replay = client.post(reverse("v1:auth:refresh"))
        self.assertEqual(replay.status_code, 401)
        self.assertEqual(replay.json()["code"], "invalid_refresh_token")

    def test_refresh_without_cookie_returns_401_and_clears_cookies(self):
        response = Client().post(reverse("v1:auth:refresh"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.cookies[ACCESS].value, "")
        self.assertEqual(response.cookies[REFRESH].value, "")

    def test_refreshed_access_token_works(self):
        client, _ = self.login()
        client.post(reverse("v1:auth:refresh"))
        self.assertEqual(client.get(reverse("v1:auth:me")).status_code, 200)

    # ── logout ───────────────────────────────────────────────────────────────

    def test_logout_blacklists_and_clears_cookies(self):
        client, _ = self.login()
        response = client.post(reverse("v1:auth:logout"))

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.cookies[ACCESS].value, "")
        self.assertEqual(response.cookies[REFRESH].value, "")
        self.assertEqual(BlacklistedToken.objects.count(), 1)

    def test_logout_succeeds_without_a_session(self):
        self.assertEqual(Client().post(reverse("v1:auth:logout")).status_code, 204)

    # ── password change ──────────────────────────────────────────────────────

    def test_password_change_requires_current_password(self):
        client, _ = self.login()
        response = client.post(
            reverse("v1:auth:password-change"),
            {"current_password": "wrong", "new_password": "another-long-password-42"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("current_password", response.json()["errors"])

    def test_password_change_enforces_validators(self):
        client, _ = self.login()
        response = client.post(
            reverse("v1:auth:password-change"),
            {"current_password": self.password, "new_password": "123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("new_password", response.json()["errors"])

    def test_password_change_succeeds_and_ends_the_session(self):
        client, _ = self.login()
        response = client.post(
            reverse("v1:auth:password-change"),
            {"current_password": self.password, "new_password": "a-brand-new-secret-99"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies[ACCESS].value, "")

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("a-brand-new-secret-99"))


class CSRFTests(TestCase):
    """Cookie auth is CSRF-relevant; header auth is not."""

    @classmethod
    def setUpTestData(cls):
        cls.password = "correct-horse-battery-staple"
        cls.user = User.objects.create_user(
            username="csrf@archethos.test",
            email="csrf@archethos.test",
            password=cls.password,
        )

    def test_unsafe_cookie_request_without_csrf_token_is_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.post(
            reverse("v1:auth:login"),
            {"email": self.user.email, "password": self.password},
            content_type="application/json",
        )
        # Authenticated by cookie, but no X-CSRFToken header supplied.
        response = client.post(
            reverse("v1:auth:password-change"),
            {"current_password": self.password, "new_password": "irrelevant-here-1234"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("CSRF", response.json()["message"])

    def test_unsafe_cookie_request_with_csrf_token_is_allowed(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse("v1:auth:csrf"))
        token = client.cookies["csrftoken"].value

        client.post(
            reverse("v1:auth:login"),
            {"email": self.user.email, "password": self.password},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        )
        token = client.cookies["csrftoken"].value

        response = client.post(
            reverse("v1:auth:password-change"),
            {"current_password": self.password, "new_password": "a-valid-new-secret-77"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)

    def test_safe_cookie_request_needs_no_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.post(
            reverse("v1:auth:login"),
            {"email": self.user.email, "password": self.password},
            content_type="application/json",
        )
        self.assertEqual(client.get(reverse("v1:auth:me")).status_code, 200)

    def test_bearer_header_bypasses_csrf(self):
        """Non-browser clients carry no ambient cookie, so CSRF cannot apply."""
        client = Client(enforce_csrf_checks=True)
        access = RefreshToken.for_user(self.user).access_token
        response = client.post(
            reverse("v1:auth:password-change"),
            {"current_password": self.password, "new_password": "header-auth-secret-88"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {access}",
        )
        self.assertEqual(response.status_code, 200)


class EmailUniquenessTests(TestCase):
    """The DB index that makes email login unambiguous."""

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user(username="a", email="dup@archethos.test", password="x")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    username="b", email="DUP@archethos.test", password="x"
                )

    def test_blank_emails_do_not_collide(self):
        User.objects.create_user(username="no-email-1", email="", password="x")
        User.objects.create_user(username="no-email-2", email="", password="x")
        self.assertEqual(User.objects.filter(email="").count(), 2)
