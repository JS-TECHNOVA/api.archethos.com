from django.apps import AppConfig


class ServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "archethosbackend.apps.services"
    # Keeps permission codenames as "services.add_<model>" rather than
    # inheriting the dotted package path.
    label = "services"
    verbose_name = "Services"
