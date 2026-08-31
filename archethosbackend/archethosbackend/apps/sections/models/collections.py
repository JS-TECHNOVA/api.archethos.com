"""
Sections that select and order reusable master content.

Every one follows the same shape:

    Section ──1:N──> SectionItem ──N:1──> master content

The intermediate model exists because the relationship carries data of its own —
order, and sometimes a caption or a per-placement label override. A plain
ManyToMany could not hold any of it.

Constraints on every item model:
  * UniqueConstraint(section, content) — the same FAQ cannot be added twice
  * `order` in no constraint at all (plan §2.3), which is what lets bulk reorder
    be a single transaction with no intermediate state to violate
"""

from django.db import models

from archethosbackend.apps.core.models import OrderedItemModel, TimeStampedModel

from .base import Section, SectionType


class HeadedSection(Section):
    """Shared heading block for the collection sections."""

    eyebrow = models.CharField(max_length=255, blank=True)
    heading = models.CharField(max_length=255, blank=True)
    subheading = models.TextField(blank=True)

    class Meta:
        abstract = True


# ─── Counters ────────────────────────────────────────────────────────────────


class CounterSection(HeadedSection):
    SECTION_TYPE = SectionType.COUNTER

    class Meta:
        verbose_name = "Counter section"


class CounterSectionItem(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        CounterSection, on_delete=models.CASCADE, related_name="items"
    )
    counter = models.ForeignKey(
        "content.Counter", on_delete=models.PROTECT, related_name="section_items"
    )

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["section", "counter"], name="unique_counter_per_section"
            )
        ]
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return f"{self.section.internal_label} — {self.counter}"


# ─── Featured projects ───────────────────────────────────────────────────────


class FeaturedProjectsSection(HeadedSection):
    SECTION_TYPE = SectionType.FEATURED_PROJECTS

    class Meta:
        verbose_name = "Featured projects section"


class FeaturedProjectItem(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        FeaturedProjectsSection, on_delete=models.CASCADE, related_name="items"
    )
    project = models.ForeignKey(
        "content.Project", on_delete=models.PROTECT, related_name="section_items"
    )
    #: Lets one project render large and the rest as a grid within one section.
    display_variant = models.CharField(
        max_length=32,
        blank=True,
        help_text='Optional per-placement hint, e.g. "large" or "compact".',
    )

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["section", "project"], name="unique_project_per_section"
            )
        ]
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return f"{self.section.internal_label} — {self.project.title}"


# ─── Services ────────────────────────────────────────────────────────────────


class ServicesSection(HeadedSection):
    SECTION_TYPE = SectionType.SERVICES

    class Meta:
        verbose_name = "Services section"


class ServiceSectionItem(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        ServicesSection, on_delete=models.CASCADE, related_name="items"
    )
    service = models.ForeignKey(
        "content.Service", on_delete=models.PROTECT, related_name="section_items"
    )
    #: Shorter wording for a cramped placement, without editing the Service.
    label_override = models.CharField(max_length=255, blank=True)

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["section", "service"], name="unique_service_per_section"
            )
        ]
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return f"{self.section.internal_label} — {self.service.title}"


# ─── Gallery ─────────────────────────────────────────────────────────────────


class GalleryLayout(models.TextChoices):
    GRID = "GRID", "Grid"
    MASONRY = "MASONRY", "Masonry"
    SLIDER = "SLIDER", "Slider"


class GallerySection(HeadedSection):
    SECTION_TYPE = SectionType.GALLERY

    layout_variant = models.CharField(
        max_length=16, choices=GalleryLayout.choices, default=GalleryLayout.GRID
    )

    class Meta:
        verbose_name = "Gallery section"


class GallerySectionItem(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        GallerySection, on_delete=models.CASCADE, related_name="items"
    )
    media = models.ForeignKey(
        "media_library.MediaAsset", on_delete=models.PROTECT, related_name="+"
    )
    caption = models.CharField(max_length=500, blank=True)

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["section", "media"], name="unique_media_per_gallery_section"
            )
        ]
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return f"{self.section.internal_label} — media {self.media_id}"


# ─── FAQ ─────────────────────────────────────────────────────────────────────


class FAQSection(HeadedSection):
    SECTION_TYPE = SectionType.FAQ

    class Meta:
        verbose_name = "FAQ section"


class FAQSectionItem(OrderedItemModel, TimeStampedModel):
    """The canonical case for this whole pattern.

    The same FAQ appears on the homepage and the Vastu page in a different
    order, and must be edited in exactly one place.
    """

    section = models.ForeignKey(
        FAQSection, on_delete=models.CASCADE, related_name="items"
    )
    faq = models.ForeignKey(
        "content.FAQ", on_delete=models.PROTECT, related_name="section_items"
    )

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["section", "faq"], name="unique_faq_per_section"
            )
        ]
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return f"{self.section.internal_label} — {self.faq.question[:50]}"
