from django.apps import AppConfig


class MediaLibraryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "archethosbackend.apps.media_library"
    # Keeps permission codenames as "media_library.add_<model>" rather than
    # inheriting the dotted package path.
    label = "media_library"
    verbose_name = "Media Library"
