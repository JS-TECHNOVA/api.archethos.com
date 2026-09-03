"""
The gallery page.

Images are master data (`content.GalleryItem`); this page chooses which of them
appear and in what order. The category filter is derived from the items
themselves rather than stored, so it cannot drift out of step with them.
"""

from django.db import models

from archethosbackend.apps.core.models import OrderedItemModel, TimeStampedModel

from .base import SectionedPage
from .shared import CTASection, HeroSection, SectionHeading, Tone, section


class GalleryGridSection(SectionHeading, TimeStampedModel):
    tone = models.CharField(max_length=16, choices=Tone.choices, default=Tone.BONE)
    show_filter = models.BooleanField(
        default=True, help_text="Render the category filter above the grid."
    )

    def __str__(self):
        return self.heading or "Gallery grid"


class GalleryGridItem(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        GalleryGridSection, on_delete=models.CASCADE, related_name="items"
    )
    gallery_item = models.ForeignKey(
        "content.GalleryItem",
        on_delete=models.PROTECT,
        related_name="grid_section_items",
    )

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["section", "gallery_item"], name="unique_gallery_grid_item"
            )
        ]
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return str(self.gallery_item)


class GalleryPage(SectionedPage):
    required_sections = ("hero", "grid")

    hero = section(HeroSection)
    grid = section(GalleryGridSection)
    cta = section(CTASection)

    class Meta:
        verbose_name = "Gallery page"
        verbose_name_plural = "Gallery page"
