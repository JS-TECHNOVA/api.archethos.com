from django.db import migrations


PROJECT_CATEGORIES = [
    "Residential",
    "Interior",
    "Commercial",
    "Renovation",
    "Hospitality",
    "Institutional",
    "Landscape",
    "Mixed-use",
]


def seed_project_categories(apps, schema_editor):
    ProjectCategory = apps.get_model("projects", "ProjectCategory")
    for order, name in enumerate(PROJECT_CATEGORIES, start=1):
        ProjectCategory.objects.get_or_create(name=name, defaults={"order": order})


def remove_seeded_project_categories(apps, schema_editor):
    ProjectCategory = apps.get_model("projects", "ProjectCategory")
    ProjectCategory.objects.filter(name__in=PROJECT_CATEGORIES).delete()


class Migration(migrations.Migration):
    dependencies = [("projects", "0013_projectdetailedstage_description_json")]

    operations = [migrations.RunPython(seed_project_categories, remove_seeded_project_categories)]
