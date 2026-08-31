from django.apps import AppConfig


class ContentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "archethosbackend.apps.content"
    # Keeps permission codenames as "content.add_project" rather than
    # inheriting the dotted package path.
    label = "content"
    verbose_name = "Content"
