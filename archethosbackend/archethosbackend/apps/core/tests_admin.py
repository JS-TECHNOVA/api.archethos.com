"""
Every registered admin screen actually opens.

`register_app` generates 72 `ModelAdmin` classes from field names. `manage.py
check` validates their configuration, but it cannot catch a `__str__` that
raises on a half-built row, a `list_display` column that blows up at render
time, or a form that cannot build a widget for a field. Those only appear when
someone opens the page — which, for a rescue tool, is the worst moment to find
out.

Walking every screen is cheap and needs no maintenance: a model added later is
covered the day it is registered.
"""

from django.contrib import admin
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

PROJECT_APPS = {"content", "pages", "media_library", "enquiries"}


def project_models():
    return sorted(
        (model for model in admin.site._registry if model._meta.app_label in PROJECT_APPS),
        key=lambda m: (m._meta.app_label, m._meta.model_name),
    )


class AdminSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            username="admin@archethos.test",
            email="admin@archethos.test",
            password="correct-horse-battery-staple",
        )

    def setUp(self):
        self.client_ = Client()
        self.client_.force_login(self.user)

    def test_every_model_is_registered(self):
        """A model nobody registered is invisible when it is needed most."""
        from django.apps import apps

        for label in sorted(PROJECT_APPS):
            for model in apps.get_app_config(label).get_models():
                with self.subTest(model=model._meta.label):
                    self.assertIn(model, admin.site._registry)

    def test_every_changelist_opens(self):
        for model in project_models():
            meta = model._meta
            with self.subTest(model=meta.label):
                url = reverse(f"admin:{meta.app_label}_{meta.model_name}_changelist")
                response = self.client_.get(url)
                self.assertEqual(response.status_code, 200, url)

    def test_every_add_form_renders(self):
        """Catches a field the admin cannot build a widget for."""
        for model in project_models():
            meta = model._meta
            with self.subTest(model=meta.label):
                url = reverse(f"admin:{meta.app_label}_{meta.model_name}_add")
                response = self.client_.get(url)
                self.assertEqual(response.status_code, 200, url)

    def test_the_search_box_does_not_error(self):
        """`search_fields` naming a non-text field is a 500, not a check error."""
        for model in project_models():
            meta = model._meta
            if not admin.site._registry[model].search_fields:
                continue
            with self.subTest(model=meta.label):
                url = reverse(f"admin:{meta.app_label}_{meta.model_name}_changelist")
                response = self.client_.get(url, {"q": "archethos"})
                self.assertEqual(response.status_code, 200, url)
