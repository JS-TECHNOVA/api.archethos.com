from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "archethosbackend.apps.projects"
    # Keeps permission codenames as "projects.add_<model>" rather than
    # inheriting the dotted package path.
    label = "projects"
    verbose_name = "Projects"
