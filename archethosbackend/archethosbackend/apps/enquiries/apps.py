from django.apps import AppConfig


class EnquiriesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "archethosbackend.apps.enquiries"
    # Keeps permission codenames as "enquiries.add_<model>" rather than
    # inheriting the dotted package path.
    label = "enquiries"
    verbose_name = "Enquiries"
