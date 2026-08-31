from django.apps import AppConfig


class PagesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "archethosbackend.apps.pages"
    # Keeps permission codenames as "pages.add_<model>" rather than
    # inheriting the dotted package path.
    label = "pages"
    verbose_name = "Pages"
