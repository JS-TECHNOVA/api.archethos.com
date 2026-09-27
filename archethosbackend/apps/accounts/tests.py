from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AuditLog


class MeViewTests(APITestCase):
    def test_me_returns_groups_and_permissions(self):
        user = get_user_model().objects.create_user("editor", password="test")
        group = Group.objects.create(name="Editors")
        permission = Permission.objects.get(content_type__app_label="master", codename="view_faq")
        user.groups.add(group)
        user.user_permissions.add(permission)
        self.client.force_authenticate(user)

        response = self.client.get("/api/v1/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["groups"], [{"id": group.id, "name": "Editors"}])
        self.assertIn("master.view_faq", response.data["permissions"])
        self.assertFalse(response.data["is_superuser"])

    def test_me_identifies_superusers(self):
        user = get_user_model().objects.create_superuser("admin", "admin@example.com", "test")
        self.client.force_authenticate(user)

        response = self.client.get("/api/v1/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_superuser"])


class AuditLogTests(APITestCase):
    def test_staff_api_write_creates_a_structured_audit_event(self):
        user = get_user_model().objects.create_user("editor", password="test", is_staff=True)
        self.client.cookies[settings.AUTH_COOKIE_ACCESS_NAME] = str(RefreshToken.for_user(user).access_token)

        response = self.client.post("/api/v1/faqs/", {"question": "What is this?", "answer": "A test FAQ."}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = AuditLog.objects.get()
        self.assertEqual(event.actor, user)
        self.assertEqual(event.action, AuditLog.Action.CREATED)
        self.assertEqual(event.resource, "Faq")
        self.assertEqual(event.object_repr, "What is this?")
