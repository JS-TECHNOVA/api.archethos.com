from django.db import models


PROJECT_STATUS_CHOICES = [("draft", "Draft"), ("published", "Published"), ("archived", "Archived")]
PROJECT_WORK_STATUS_CHOICES = [
    ("planning", "Planning"),
    ("ongoing", "Ongoing"),
    ("completed", "Completed"),
    ("on_hold", "On hold"),
]
class ProjectCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]


class Project(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(ProjectCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name="projects")
    location = models.CharField(max_length=255, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    project_status = models.CharField(
        max_length=100,
        choices=PROJECT_WORK_STATUS_CHOICES,
        blank=True,
    )
    services = models.ManyToManyField(
        "services.Service",
        blank=True,
        related_name="projects",
    )
    short_description = models.TextField(blank=True)
    description = models.TextField(blank=True)
    cover_image = models.ForeignKey("media_library.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="project_covers")
    is_featured = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=PROJECT_STATUS_CHOICES, default="draft")
    published_at = models.DateTimeField(null=True, blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]


class ProjectGallery(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="gallery")
    asset = models.ForeignKey("media_library.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="project_gallery_items")
    title = models.CharField(max_length=255, blank=True)
    caption = models.TextField(blank=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class ProjectDetailedStage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="detailed_stages")
    eyebrow = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    media = models.ForeignKey("media_library.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="project_stage_media")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]


class ProjectPage(models.Model):
    SINGLETON_PK = 1
    hero_title = models.CharField(max_length=255, blank=True)
    hero_description = models.TextField(blank=True)
    hero_image = models.ForeignKey("media_library.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="projects_page_hero_images")
    featured_projects = models.ManyToManyField(
        Project,
        blank=True,
        related_name="featured_on_projects_pages",
    )
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="projects_page_singleton")]
