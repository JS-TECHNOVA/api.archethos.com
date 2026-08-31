from django.apps import AppConfig


class FaqsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "archethosbackend.apps.faqs"
    # Keeps permission codenames as "faqs.add_<model>" rather than
    # inheriting the dotted package path.
    label = "faqs"
    verbose_name = "FAQs"
