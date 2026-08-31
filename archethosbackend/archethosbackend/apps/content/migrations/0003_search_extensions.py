"""
Enable the Postgres extensions the search layer relies on.

`unaccent` so "Kushinagar" matches a query typed without diacritics, and
`pg_trgm` for the similarity fallback that catches typos full-text search misses
("architectre" finds nothing in a tsvector, but is trigram-close to
"architecture").

Both are database-wide and require superuser on first install, which is why they
live in their own migration: on a managed host where the role lacks that right,
this is the single migration to run by hand.
"""

from django.contrib.postgres.operations import TrigramExtension, UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("content", "0002_blogpost_search_vector_project_search_vector_and_more")]

    operations = [
        TrigramExtension(),
        UnaccentExtension(),
    ]
