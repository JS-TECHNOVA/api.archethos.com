from django.apps import AppConfig


class CompanyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "archethosbackend.apps.company"
    # Keeps permission codenames as "company.add_<model>" rather than
    # inheriting the dotted package path.
    label = "company"
    verbose_name = "Company"
