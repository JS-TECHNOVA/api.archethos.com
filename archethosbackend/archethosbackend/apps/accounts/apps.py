from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "archethosbackend.apps.accounts"
    # Keeps permission codenames as "accounts.add_<model>" rather than
    # inheriting the dotted package path.
    label = "accounts"
    verbose_name = "Accounts"
