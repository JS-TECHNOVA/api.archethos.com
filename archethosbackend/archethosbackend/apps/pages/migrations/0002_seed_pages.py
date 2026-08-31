"""
Seed one Page row per frontend route.

These are the routes the Next.js app actually has (DEVELOPMENT_PLAN.md §18).
Creating them here rather than by hand means the aggregate endpoint answers for
every real route from the first deploy, instead of 404ing until someone
remembers to add a row.

Seeded as DRAFT: a page with no sections attached yet has nothing to render, so
publishing is a deliberate act once its composition exists.

Additive and idempotent — `get_or_create` by slug, so re-running never disturbs
a page an editor has since renamed or published.
"""

from django.db import migrations

PAGES = [
    ("home", "Home"),
    ("about", "About"),
    ("contact", "Contact"),
    ("gallery", "Gallery"),
    ("journal", "Journal"),
    ("projects", "Projects"),
    ("services", "Services"),
    ("locations", "Locations"),
    ("legal/privacy", "Privacy Policy"),
    ("legal/terms", "Terms of Use"),
]


def seed(apps, schema_editor):
    Page = apps.get_model("pages", "Page")
    for slug, name in PAGES:
        Page.objects.get_or_create(slug=slug, defaults={"name": name})


def unseed(apps, schema_editor):
    Page = apps.get_model("pages", "Page")
    # Only remove pages nothing has been attached to, so a reverse migration
    # cannot silently discard an editor's composition.
    for slug, _ in PAGES:
        page = Page.objects.filter(slug=slug).first()
        if page and not page.page_sections.exists():
            page.delete()


class Migration(migrations.Migration):

    dependencies = [("pages", "0001_initial")]

    operations = [migrations.RunPython(seed, unseed)]
