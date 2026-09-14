from django.conf import settings
from django.db import models


class MediaAsset(models.Model):
    file = models.FileField(upload_to="media/", blank=True, null=True)
    thumbnail_file = models.FileField(upload_to="media/thumbnails/", blank=True, null=True)
    media_type = models.CharField(max_length=20, blank=True)
    source_type = models.CharField(max_length=20, blank=True)
    external_url = models.URLField(max_length=500, blank=True)
    external_id = models.CharField(max_length=255, blank=True)
    thumbnail_url = models.URLField(max_length=500, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True)
    alt_text = models.CharField(max_length=255, blank=True)
    caption = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    tags = models.JSONField(blank=True, null=True)
    media_location = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
