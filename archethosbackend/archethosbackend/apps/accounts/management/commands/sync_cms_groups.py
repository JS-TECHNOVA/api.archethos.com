"""Refresh the default CMS roles after new apps or models are added."""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from archethosbackend.apps.accounts.groups import sync_groups


class Command(BaseCommand):
    help = "Create or refresh the default CMS groups and their permissions."

    def handle(self, *args, **options):
        report = sync_groups(Group, Permission)
        for name, count in report.items():
            self.stdout.write(f"  {name:<20} {count} permissions")
        self.stdout.write(self.style.SUCCESS("CMS groups synced."))
