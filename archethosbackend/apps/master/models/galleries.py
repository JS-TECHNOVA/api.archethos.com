from django.conf import settings
from django.db import models


class Gallery(models.Model):
    SINGLETON_PK = 1

    hero_title = models.CharField(max_length=255, blank=True)
    hero_description = models.TextField(blank=True)
    hero_image = models.ForeignKey(
        "media_library.MediaAsset",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="gallery_hero_images",
    )
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="gallery_singleton")]


class GalleryCategory(models.Model):
    gallery = models.ForeignKey(Gallery, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [models.UniqueConstraint(fields=["gallery", "name"], name="unique_gallery_category_name")]


class GalleryItem(models.Model):
    category = models.ForeignKey(GalleryCategory, on_delete=models.PROTECT, related_name="items")
    asset = models.ForeignKey(
        "media_library.MediaAsset",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="gallery_items",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="added_gallery_items"
    )

    class Meta:
        ordering = ["order", "id"]
        constraints = [models.UniqueConstraint(fields=["asset"], name="unique_gallery_asset")]
