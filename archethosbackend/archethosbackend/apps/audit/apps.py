from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "archethosbackend.apps.audit"
    # Keeps permission codenames as "audit.add_<model>" rather than
    # inheriting the dotted package path.
    label = "audit"
    verbose_name = "Audit"
