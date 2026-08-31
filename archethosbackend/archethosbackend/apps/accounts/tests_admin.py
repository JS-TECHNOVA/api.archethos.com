"""
User, group and permission management tests.

The escalation guards get the most attention here: they are the difference
between "this user can edit users" and "this user can make themselves root".
"""

from django.contrib.auth.models import Group, Permission, User
from django.test import Client, TestCase
from django.urls import reverse


def perm(codename):
    return Permission.objects.get(codename=codename)


class AdminAPITestCase(TestCase):
    """Logs a client in over the real login endpoint, as the frontend would."""

    password = "correct-horse-battery-staple"

    def make_user(self, email, *, superuser=False, permissions=(), groups=()):
        user = User.objects.create_user(
            username=email, email=email, password=self.password
        )
        if superuser:
            user.is_superuser = user.is_staff = True
            user.save(update_fields=["is_superuser", "is_staff"])
        if permissions:
            user.user_permissions.add(*[perm(c) for c in permissions])
        if groups:
            user.groups.add(*groups)
        return User.objects.get(pk=user.pk)  # drop the permission cache

    def client_for(self, user):
        client = Client()
        response = client.post(
            reverse("v1:auth:login"),
            {"email": user.email, "password": self.password},
            content_type="application/json",
        )
        assert response.status_code == 200, response.content
        return client


class PermissionEnforcementTests(AdminAPITestCase):
    def test_anonymous_is_rejected(self):
        self.assertEqual(Client().get(reverse("v1:admin:user-list")).status_code, 401)

    def test_authenticated_without_view_permission_is_forbidden(self):
        """The whole point of StrictDjangoModelPermissions.

        Stock DjangoModelPermissions leaves GET unmapped, so this would be a 200.
        """
        user = self.make_user("nobody@archethos.test")
        response = self.client_for(user).get(reverse("v1:admin:user-list"))
        self.assertEqual(response.status_code, 403)

    def test_view_permission_grants_read_but_not_write(self):
        user = self.make_user("viewer@archethos.test", permissions=["view_user"])
        client = self.client_for(user)

        self.assertEqual(client.get(reverse("v1:admin:user-list")).status_code, 200)

        response = client.post(
            reverse("v1:admin:user-list"),
            {"email": "new@archethos.test", "password": "a-long-enough-secret-1"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_superuser_bypasses_permission_checks(self):
        user = self.make_user("root@archethos.test", superuser=True)
        self.assertEqual(
            self.client_for(user).get(reverse("v1:admin:user-list")).status_code, 200
        )


class UserListTests(AdminAPITestCase):
    def setUp(self):
        self.admin = self.make_user("root@archethos.test", superuser=True)
        self.client_ = self.client_for(self.admin)
        for i in range(5):
            User.objects.create_user(
                username=f"u{i}@archethos.test",
                email=f"u{i}@archethos.test",
                password="x",
                is_active=(i % 2 == 0),
            )

    def test_list_is_paginated_with_envelope(self):
        body = self.client_.get(reverse("v1:admin:user-list") + "?page_size=2").json()

        self.assertTrue(body["success"])
        self.assertEqual(len(body["data"]), 2)
        self.assertEqual(body["pagination"]["page"], 1)
        self.assertEqual(body["pagination"]["page_size"], 2)
        self.assertEqual(body["pagination"]["total_items"], 6)
        self.assertEqual(body["pagination"]["total_pages"], 3)
        self.assertTrue(body["pagination"]["has_next"])
        self.assertFalse(body["pagination"]["has_previous"])

    def test_list_rows_are_flat(self):
        row = self.client_.get(reverse("v1:admin:user-list")).json()["data"][0]
        self.assertNotIn("user_permissions", row)
        self.assertNotIn("effective_permissions", row)
        self.assertIsInstance(row["groups"], list)

    def test_filter_by_is_active(self):
        body = self.client_.get(reverse("v1:admin:user-list") + "?is_active=false").json()
        self.assertTrue(all(r["is_active"] is False for r in body["data"]))
        self.assertEqual(body["pagination"]["total_items"], 2)

    def test_search_by_email(self):
        body = self.client_.get(reverse("v1:admin:user-list") + "?search=u3").json()
        self.assertEqual(body["pagination"]["total_items"], 1)

    def test_ordering(self):
        body = self.client_.get(reverse("v1:admin:user-list") + "?ordering=email").json()
        emails = [r["email"] for r in body["data"]]
        self.assertEqual(emails, sorted(emails))


class UserWriteTests(AdminAPITestCase):
    def setUp(self):
        self.admin = self.make_user("root@archethos.test", superuser=True)
        self.client_ = self.client_for(self.admin)

    def test_create_derives_username_and_hashes_password(self):
        response = self.client_.post(
            reverse("v1:admin:user-list"),
            {
                "email": "editor@archethos.test",
                "first_name": "Ed",
                "password": "a-long-enough-secret-1",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        created = User.objects.get(email="editor@archethos.test")
        self.assertEqual(created.username, "editor@archethos.test")
        self.assertTrue(created.check_password("a-long-enough-secret-1"))
        self.assertNotIn("password", response.json()["data"])

    def test_create_requires_a_password(self):
        response = self.client_.post(
            reverse("v1:admin:user-list"),
            {"email": "nopass@archethos.test"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json()["errors"])

    def test_create_rejects_weak_password(self):
        response = self.client_.post(
            reverse("v1:admin:user-list"),
            {"email": "weak@archethos.test", "password": "123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json()["errors"])

    def test_create_rejects_duplicate_email_case_insensitively(self):
        response = self.client_.post(
            reverse("v1:admin:user-list"),
            {"email": "ROOT@archethos.test", "password": "a-long-enough-secret-1"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json()["errors"])

    def test_detail_exposes_effective_permissions_not_password(self):
        target = self.make_user("t@archethos.test", permissions=["view_user"])
        body = self.client_.get(
            reverse("v1:admin:user-detail", args=[target.pk])
        ).json()["data"]

        self.assertIn("auth.view_user", body["effective_permissions"])
        self.assertNotIn("password", body)

    def test_users_cannot_be_deleted(self):
        target = self.make_user("t@archethos.test")
        response = self.client_.delete(
            reverse("v1:admin:user-detail", args=[target.pk])
        )
        self.assertEqual(response.status_code, 405)


class EscalationGuardTests(AdminAPITestCase):
    """Everything Django's permission system would otherwise allow."""

    def setUp(self):
        # Can manage users, but holds only one content-ish permission itself.
        self.manager = self.make_user(
            "manager@archethos.test",
            permissions=["view_user", "add_user", "change_user", "view_group"],
        )
        self.client_ = self.client_for(self.manager)

    def test_cannot_grant_permissions_they_do_not_hold(self):
        response = self.client_.post(
            reverse("v1:admin:user-list"),
            {
                "email": "puppet@archethos.test",
                "password": "a-long-enough-secret-1",
                "user_permissions": [perm("delete_user").id],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("user_permissions", response.json()["errors"])
        self.assertFalse(User.objects.filter(email="puppet@archethos.test").exists())

    def test_can_grant_permissions_they_do_hold(self):
        response = self.client_.post(
            reverse("v1:admin:user-list"),
            {
                "email": "ok@archethos.test",
                "password": "a-long-enough-secret-1",
                "user_permissions": [perm("view_user").id],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

    def test_cannot_assign_a_group_containing_permissions_they_lack(self):
        group = Group.objects.create(name="Destroyers")
        group.permissions.add(perm("delete_user"))

        response = self.client_.post(
            reverse("v1:admin:user-list"),
            {
                "email": "puppet@archethos.test",
                "password": "a-long-enough-secret-1",
                "groups": [group.id],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("groups", response.json()["errors"])

    def test_cannot_promote_to_superuser(self):
        target = self.make_user("t@archethos.test")
        response = self.client_.patch(
            reverse("v1:admin:user-detail", args=[target.pk]),
            {"is_superuser": True},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("is_superuser", response.json()["errors"])

        target.refresh_from_db()
        self.assertFalse(target.is_superuser)

    def test_cannot_grant_staff_access(self):
        target = self.make_user("t@archethos.test")
        response = self.client_.patch(
            reverse("v1:admin:user-detail", args=[target.pk]),
            {"is_staff": True},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_superuser_may_do_all_of_that(self):
        root = self.make_user("root@archethos.test", superuser=True)
        target = self.make_user("t@archethos.test")

        response = self.client_for(root).patch(
            reverse("v1:admin:user-detail", args=[target.pk]),
            {"is_superuser": True, "user_permissions": [perm("delete_user").id]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        target.refresh_from_db()
        self.assertTrue(target.is_superuser)

    def test_cannot_deactivate_self_via_patch(self):
        response = self.client_.patch(
            reverse("v1:admin:user-detail", args=[self.manager.pk]),
            {"is_active": False},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_cannot_deactivate_self_via_endpoint(self):
        response = self.client_.post(
            reverse("v1:admin:user-deactivate", args=[self.manager.pk])
        )
        self.assertEqual(response.status_code, 400)

        self.manager.refresh_from_db()
        self.assertTrue(self.manager.is_active)

    def test_cannot_deactivate_the_last_active_superuser(self):
        root = self.make_user("root@archethos.test", superuser=True)
        response = self.client_.post(
            reverse("v1:admin:user-deactivate", args=[root.pk])
        )
        self.assertEqual(response.status_code, 400)

        root.refresh_from_db()
        self.assertTrue(root.is_active)

    def test_can_deactivate_a_superuser_when_another_remains(self):
        root_a = self.make_user("root-a@archethos.test", superuser=True)
        self.make_user("root-b@archethos.test", superuser=True)

        response = self.client_.post(
            reverse("v1:admin:user-deactivate", args=[root_a.pk])
        )
        self.assertEqual(response.status_code, 200)

        root_a.refresh_from_db()
        self.assertFalse(root_a.is_active)

    def test_deactivated_user_cannot_log_in(self):
        target = self.make_user("t@archethos.test")
        self.client_.post(reverse("v1:admin:user-deactivate", args=[target.pk]))

        response = Client().post(
            reverse("v1:auth:login"),
            {"email": target.email, "password": self.password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_reactivate_restores_login(self):
        target = self.make_user("t@archethos.test")
        self.client_.post(reverse("v1:admin:user-deactivate", args=[target.pk]))
        self.client_.post(reverse("v1:admin:user-activate", args=[target.pk]))

        response = Client().post(
            reverse("v1:auth:login"),
            {"email": target.email, "password": self.password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)


class SetPasswordTests(AdminAPITestCase):
    def test_admin_can_set_another_users_password(self):
        admin = self.make_user("root@archethos.test", superuser=True)
        target = self.make_user("t@archethos.test")

        response = self.client_for(admin).post(
            reverse("v1:admin:user-set-password", args=[target.pk]),
            {"new_password": "a-brand-new-secret-42"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        target.refresh_from_db()
        self.assertTrue(target.check_password("a-brand-new-secret-42"))

    def test_weak_password_is_rejected(self):
        admin = self.make_user("root@archethos.test", superuser=True)
        target = self.make_user("t@archethos.test")

        response = self.client_for(admin).post(
            reverse("v1:admin:user-set-password", args=[target.pk]),
            {"new_password": "123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_requires_change_user_permission(self):
        user = self.make_user("viewer@archethos.test", permissions=["view_user"])
        target = self.make_user("t@archethos.test")

        response = self.client_for(user).post(
            reverse("v1:admin:user-set-password", args=[target.pk]),
            {"new_password": "a-brand-new-secret-42"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)


class GroupTests(AdminAPITestCase):
    def setUp(self):
        self.admin = self.make_user("root@archethos.test", superuser=True)
        self.client_ = self.client_for(self.admin)

    def test_list_is_light_and_counts_members(self):
        group = Group.objects.create(name="Zeta")
        group.permissions.add(perm("view_user"), perm("change_user"))
        self.admin.groups.add(group)

        rows = self.client_.get(reverse("v1:admin:group-list") + "?search=Zeta").json()[
            "data"
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["permissions_count"], 2)
        self.assertEqual(rows[0]["users_count"], 1)
        self.assertNotIn("permissions", rows[0])

    def test_detail_expands_permissions(self):
        group = Group.objects.create(name="Zeta")
        group.permissions.add(perm("view_user"))

        body = self.client_.get(
            reverse("v1:admin:group-detail", args=[group.pk])
        ).json()["data"]
        self.assertEqual(body["permissions"][0]["codename_full"], "auth.view_user")

    def test_create_with_permissions(self):
        response = self.client_.post(
            reverse("v1:admin:group-list"),
            {"name": "Reviewers", "permissions": [perm("view_user").id]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Group.objects.filter(name="Reviewers").exists())

    def test_duplicate_name_is_rejected(self):
        Group.objects.create(name="Reviewers")
        response = self.client_.post(
            reverse("v1:admin:group-list"),
            {"name": "reviewers"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_delete(self):
        group = Group.objects.create(name="Temp")
        response = self.client_.delete(
            reverse("v1:admin:group-detail", args=[group.pk])
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Group.objects.filter(pk=group.pk).exists())

    def test_bootstrap_groups_exist(self):
        names = set(Group.objects.values_list("name", flat=True))
        self.assertTrue(
            {"Administrators", "Content Managers", "Editors", "Media Managers"} <= names
        )


class PermissionCatalogueTests(AdminAPITestCase):
    def test_grouped_by_app_and_model(self):
        admin = self.make_user("root@archethos.test", superuser=True)
        body = self.client_for(admin).get(reverse("v1:admin:permission-list")).json()

        self.assertTrue(body["success"])
        data = body["data"]
        self.assertIn("auth", data)
        self.assertIn("user", data["auth"])

        codenames = {p["codename_full"] for p in data["auth"]["user"]}
        self.assertIn("auth.view_user", codenames)
        self.assertIn("auth.delete_user", codenames)

        # Django plumbing is filtered out of the picker.
        for hidden in ("contenttypes", "sessions", "admin", "token_blacklist"):
            self.assertNotIn(hidden, data)

    def test_requires_view_permission_permission(self):
        user = self.make_user("nobody@archethos.test")
        response = self.client_for(user).get(reverse("v1:admin:permission-list"))
        self.assertEqual(response.status_code, 403)

    def test_is_not_paginated(self):
        admin = self.make_user("root@archethos.test", superuser=True)
        body = self.client_for(admin).get(reverse("v1:admin:permission-list")).json()
        self.assertNotIn("pagination", body)
