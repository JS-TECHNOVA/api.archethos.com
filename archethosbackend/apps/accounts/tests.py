from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import status
from rest_framework.test import APITestCase


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
