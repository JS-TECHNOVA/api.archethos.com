from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "archethosbackend.apps.api"
    # Keeps permission codenames as "api.add_<model>" rather than
    # inheriting the dotted package path.
    label = "api"
    verbose_name = "API"
