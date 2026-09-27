from django.db import models


class Slider(models.Model):
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


class HomePage(models.Model):
    SINGLETON_PK = 1
    sliders = models.ManyToManyField(Slider, blank=True, related_name="home_pages")
    featured_project = models.ForeignKey("projects.Project", null=True, blank=True, on_delete=models.SET_NULL, related_name="featured_on_home_pages")
    featured_service = models.ForeignKey("services.Service", null=True, blank=True, on_delete=models.SET_NULL, related_name="featured_on_home_pages")
    home_counters = models.JSONField(default=list, blank=True)
    design_build_process = models.JSONField(default=dict, blank=True)
    selected_work_title = models.CharField(max_length=255, blank=True)
    selected_work_description = models.TextField(blank=True)
    selected_work = models.ManyToManyField("projects.Project", blank=True, related_name="selected_on_home_pages")
    gallery = models.ManyToManyField("master.GalleryItem", blank=True, related_name="home_pages")
    section_content = models.JSONField(default=dict, blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="home_page_singleton")]
