from django.apps import AppConfig


class SectionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "archethosbackend.apps.sections"
    # Keeps permission codenames as "sections.add_<model>" rather than
    # inheriting the dotted package path.
    label = "sections"
    verbose_name = "CMS Sections"
