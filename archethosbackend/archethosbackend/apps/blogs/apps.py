from django.apps import AppConfig


class BlogsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "archethosbackend.apps.blogs"
    # Keeps permission codenames as "blogs.add_<model>" rather than
    # inheriting the dotted package path.
    label = "blogs"
    verbose_name = "Blogs"
