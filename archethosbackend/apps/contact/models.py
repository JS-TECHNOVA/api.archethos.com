from django.db import models


class ContactPage(models.Model):
    SINGLETON_PK = 1
    slider = models.ForeignKey("home.Slider", null=True, blank=True, on_delete=models.SET_NULL, related_name="contact_pages")
    form_eyebrow = models.CharField(max_length=255, blank=True)
    sidebar_image = models.ForeignKey("media_library.MediaAsset", null=True, blank=True, on_delete=models.SET_NULL, related_name="contact_sidebar_images")
    next_eyebrow = models.CharField(max_length=255, blank=True)
    next_title = models.CharField(max_length=255, blank=True)
    next_steps = models.JSONField(default=list, blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="contact_page_singleton")]
