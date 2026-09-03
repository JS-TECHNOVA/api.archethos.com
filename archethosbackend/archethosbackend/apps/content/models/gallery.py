from django.db import models

from archethosbackend.apps.core.models import PublishableModel, TimeStampedModel


class GalleryCategory(models.TextChoices):
    ARCHITECTURE = "ARCHITECTURE", "Architecture"
    INTERIORS = "INTERIORS", "Interiors"
    CONSTRUCTION = "CONSTRUCTION", "Construction"
    DETAIL = "DETAIL", "Detail"


class GalleryItem(PublishableModel, TimeStampedModel):
    """One image or clip in the studio's gallery.

    Master content, because the same frame appears in the gallery grid, in the
    home page slider and potentially alongside a project. Storing it once means
    a re-crop or a corrected caption lands everywhere at the same time.

    Distinct from MediaAsset: an asset is a file, this is a published piece of
    work with a title, a caption and a category. Plenty of assets — an OG image,
    a founder portrait — are never gallery items.
    """

    title = models.CharField(max_length=255)
    caption = models.CharField(max_length=500, blank=True)
    category = models.CharField(
        max_length=16,
        choices=GalleryCategory.choices,
        default=GalleryCategory.ARCHITECTURE,
        db_index=True,
    )

    image = models.ForeignKey(
        "media_library.MediaAsset",
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "published_at"])]

    def __str__(self):
        return self.title
