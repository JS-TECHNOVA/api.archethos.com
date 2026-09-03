"""
Create the row behind each of the site's pages.

    manage.py ensure_pages

Idempotent, and safe on every deploy. A page model with no row is a page an
editor cannot open, so this runs after `migrate` the way `sync_cms_groups` does
— adding a page means adding a model, and this is what makes it appear in the
admin without anyone remembering a manual step.

Rows are created unpublished. Nothing reaches the public API until an editor
fills in the required sections and publishes it.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from archethosbackend.apps.pages.models import ORDERED_PAGES


class Command(BaseCommand):
    help = "Create any missing page rows. Safe to re-run."

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0

        for route, model in ORDERED_PAGES.items():
            _, was_created = model.objects.get_or_create(pk=model.SINGLETON_PK)
            created += was_created

            missing = model.objects.get(pk=model.SINGLETON_PK).missing_sections()
            state = "created" if was_created else "exists"
            note = f" — needs {', '.join(missing)}" if missing else ""
            self.stdout.write(f"  /{route:<16} {state}{note}")

        self.stdout.write(
            self.style.SUCCESS(
                f"{len(ORDERED_PAGES)} pages checked, {created} created."
            )
        )
