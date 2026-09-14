from django.db import models


class Slider(models.Model):
    label = models.CharField(max_length=100, blank=True)
    eyebrow = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    media = models.ForeignKey("media_library.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="sliders")
    primary_cta_label = models.CharField(max_length=100, blank=True)
    primary_cta_url = models.CharField(max_length=255, blank=True)
    secondary_cta_label = models.CharField(max_length=100, blank=True)
    secondary_cta_url = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]


class Counter(models.Model):
    value = models.CharField(max_length=50)
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]


class WorkProcessGroup(models.Model):
    eyebrow = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    is_visible = models.BooleanField(default=True)


class WorkProcessStep(models.Model):
    group = models.ForeignKey(WorkProcessGroup, on_delete=models.CASCADE, related_name="steps")
    number = models.CharField(max_length=10, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class HomePage(models.Model):
    SINGLETON_PK = 1
    sliders = models.ManyToManyField(Slider, blank=True, related_name="home_pages")
    featured_project = models.ForeignKey("projects.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="featured_on_home_pages")
    featured_service = models.ForeignKey("services.Service", null=True, blank=True, on_delete=models.SET_NULL, related_name="featured_on_home_pages")
    selected_gallery_items = models.ManyToManyField("master.GalleryItem", blank=True, related_name="selected_on_home_pages")
    work_process_group = models.ForeignKey(WorkProcessGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="home_pages")
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="home_page_singleton")]


class HomeServicesGroup(models.Model):
    page = models.OneToOneField(HomePage, on_delete=models.CASCADE, related_name="services_group")
    eyebrow = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    services = models.ManyToManyField("services.Service", blank=True, related_name="home_service_groups")


class HomeProjectsGroup(models.Model):
    page = models.OneToOneField(HomePage, on_delete=models.CASCADE, related_name="projects_group")
    eyebrow = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    projects = models.ManyToManyField("projects.Project", blank=True, related_name="home_project_groups")


class HomeGalleryGroup(models.Model):
    page = models.OneToOneField(HomePage, on_delete=models.CASCADE, related_name="gallery_group")
    eyebrow = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    gallery_items = models.ManyToManyField("master.GalleryItem", blank=True, related_name="home_gallery_groups")


class HomeCountersGroup(models.Model):
    page = models.OneToOneField(HomePage, on_delete=models.CASCADE, related_name="counters_group")
    eyebrow = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    counters = models.ManyToManyField(Counter, blank=True, related_name="home_counter_groups")


HOME_CONTENT_GROUP_CHOICES = [
    ("intro", "Studio introduction"),
    ("design_build", "Design and build"),
    ("vastu", "Vastu preview"),
    ("locations", "Locations preview"),
    ("cta", "CTA"),
]


class HomeContentGroup(models.Model):
    page = models.ForeignKey(HomePage, on_delete=models.CASCADE, related_name="content_groups")
    group_type = models.CharField(max_length=30, choices=HOME_CONTENT_GROUP_CHOICES)
    eyebrow = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    content = models.JSONField(default=dict, blank=True)
    media = models.ForeignKey("media_library.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="home_content_group_media")
    secondary_media = models.ForeignKey("media_library.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="home_content_group_secondary_media")
    cta_label = models.CharField(max_length=100, blank=True)
    cta_url = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [models.UniqueConstraint(fields=["page", "group_type"], name="home_page_content_group_type_unique")]
