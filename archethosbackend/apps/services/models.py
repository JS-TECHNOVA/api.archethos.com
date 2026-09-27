from django.db import models


class Service(models.Model):
    eyebrow = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=200)
    tagline = models.TextField(blank=True)
    short_description = models.TextField(blank=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.JSONField(default=dict, blank=True)
    sections = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    image = models.ForeignKey("media_library.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="service_images")
    how_it_moves = models.JSONField(default=dict, blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]


class ServiceWorkStage(models.Model):
    IMAGE_SIDE_CHOICES = [("left", "Left"), ("right", "Right")]

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="work_stages")
    eyebrow = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255)
    description = models.JSONField(default=dict, blank=True)
    media = models.ForeignKey("media_library.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="service_stage_media")
    image_side = models.CharField(max_length=5, choices=IMAGE_SIDE_CHOICES, blank=True, default="")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class ServicesGallery(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="gallery")
    asset = models.ForeignKey("media_library.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="service_gallery_items")
    title = models.CharField(max_length=255, blank=True)
    caption = models.TextField(blank=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class ServicesPage(models.Model):
    SINGLETON_PK = 1
    hero_eyebrow = models.CharField(max_length=255, blank=True)
    hero_title = models.CharField(max_length=255, blank=True)
    hero_description = models.TextField(blank=True)
    hero_image = models.ForeignKey("media_library.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="services_page_hero_images")
    how_project_moves = models.JSONField(default=dict, blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="services_page_singleton")]
