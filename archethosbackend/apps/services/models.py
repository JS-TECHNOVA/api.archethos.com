from django.db import models


class Service(models.Model):
    number = models.CharField(max_length=10, blank=True)
    order = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=200)
    title_lines = models.JSONField(default=list, blank=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    is_featured = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)
    hero_heading = models.CharField(max_length=255, blank=True)
    short_description = models.TextField(blank=True)
    description = models.TextField(blank=True)
    hero_image = models.ForeignKey("media_library.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="service_hero_images")
    index_image = models.ForeignKey("media_library.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="service_index_images")
    sections = models.JSONField(default=list, blank=True)
    process_eyebrow = models.CharField(max_length=255, blank=True)
    gallery = models.ManyToManyField("media_library.MediaAsset", blank=True, related_name="service_galleries")
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "title"]


class ServicesWorkProcess(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="work_processes")
    number = models.CharField(max_length=10, blank=True)
    title = models.CharField(max_length=255)
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
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="services_page_singleton")]
