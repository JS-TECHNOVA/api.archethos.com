from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "archethosbackend.apps.core"
    # Keeps permission codenames as "core.add_<model>" rather than
    # inheriting the dotted package path.
    label = "core"
    verbose_name = "Core"
