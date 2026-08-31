from django.apps import AppConfig


class CountersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "archethosbackend.apps.counters"
    # Keeps permission codenames as "counters.add_<model>" rather than
    # inheriting the dotted package path.
    label = "counters"
    verbose_name = "Counters"
