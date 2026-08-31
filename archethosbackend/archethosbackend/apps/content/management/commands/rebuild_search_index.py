"""Recompute every search vector.

Needed after a bulk edit: `update()` and `bulk_update()` do not call `save()`,
so they leave the vector stale. Also the way to backfill after adding a model to
the search layer.
"""

from django.core.management.base import BaseCommand

from archethosbackend.apps.content.models import BlogPost, Project, Service

SEARCHABLE = [Project, Service, BlogPost]


class Command(BaseCommand):
    help = "Recompute search vectors for all searchable content."

    def handle(self, *args, **options):
        for model in SEARCHABLE:
            count = 0
            for instance in model.objects.iterator():
                instance.update_search_vector()
                count += 1
            self.stdout.write(f"  {model.__name__:<12} {count} rows")
        self.stdout.write(self.style.SUCCESS("Search index rebuilt."))
