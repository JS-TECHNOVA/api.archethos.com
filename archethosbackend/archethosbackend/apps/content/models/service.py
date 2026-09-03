"""
Services — what the studio offers.

Master content: a Service is referenced by the home page, the services index,
individual projects and its own detail route at `/services/[slug]`, so every
field the detail page renders belongs here rather than in any one section.
"""

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.db import models

from archethosbackend.apps.core.models import (
    OrderedItemModel,
    PublishableModel,
    SEOModel,
    SluggedModel,
    TimeStampedModel,
)


class Service(SluggedModel, PublishableModel, SEOModel, TimeStampedModel):
    """One discipline: Architecture Design, Interior Design, Vastu Consultancy…"""

    #: Authored, e.g. "01". Printed as an index numeral beside the title and not
    #: derived from `order`, so a service can be reordered without renumbering.
    number = models.CharField(max_length=8, blank=True)

    #: The stacked editorial index breaks the title across lines by hand, and
    #: where it breaks is an editorial decision rather than a CSS one.
    title_lines = models.JSONField(
        default=list,
        blank=True,
        help_text="One string per rendered line of the title. Falls back to title.",
    )

    #: A longer headline used only at the top of the detail page.
    hero_heading = models.CharField(max_length=500, blank=True)

    short_description = models.CharField(
        max_length=500, blank=True, help_text="One line, used on cards and in listings."
    )
    description = models.TextField(blank=True)

    hero_image = models.ForeignKey(
        "media_library.MediaAsset",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Full-bleed image at the top of the service detail page.",
    )
    index_image = models.ForeignKey(
        "media_library.MediaAsset",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        help_text="Used wherever the service appears in a list.",
    )
    icon = models.ForeignKey(
        "media_library.MediaAsset",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    #: Curation, not publishing — a featured service can still be a draft.
    is_featured = models.BooleanField(default=False, db_index=True)

    #: Heading above the process steps, e.g. "How it moves".
    process_label = models.CharField(max_length=120, blank=True)

    #: Default display order in listings; a section's items can override it.
    order = models.PositiveIntegerField(default=0, db_index=True)

    #: Weighted tsvector, maintained in save(). Never edited by hand.
    search_vector = SearchVectorField(null=True, editable=False)

    class Meta:
        ordering = ["order", "title"]
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["is_featured", "status"]),
            GinIndex(fields=["search_vector"]),
        ]

    @property
    def display_lines(self):
        """What the index renders. One line unless the studio split the title."""
        return self.title_lines or [self.title]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_search_vector()

    def update_search_vector(self):
        """Recompute the tsvector for this row.

        Done as a follow-up UPDATE rather than in Python because the weighting
        and stemming are Postgres's job. Costs one extra query per save, which
        is nothing at CMS write volume.

        Rows changed by `update()` or `bulk_update()` bypass this — run
        `manage.py rebuild_search_index` after any bulk edit.
        """
        type(self).objects.filter(pk=self.pk).update(
            search_vector=(
                SearchVector("title", weight="A", config="english")
                + SearchVector("hero_heading", weight="B", config="english")
                + SearchVector("short_description", weight="B", config="english")
                + SearchVector("description", weight="C", config="english")
            )
        )


class ServiceDetailSection(OrderedItemModel, TimeStampedModel):
    """One chapter of a service's detail page.

    Owned by the service, not by a page: these describe the discipline itself
    and read identically wherever the service is expanded. That is what keeps
    them out of `pages` — no page composes them, the service does.
    """

    RATIO_CHOICES = [
        ("16/9", "16:9"),
        ("4/5", "4:5"),
        ("21/9", "21:9"),
        ("1/1", "Square"),
    ]

    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="detail_sections"
    )

    label = models.CharField(max_length=255, help_text='e.g. "Concept & Planning".')
    heading = models.CharField(max_length=500, blank=True)
    body = models.TextField(blank=True)

    #: A plain list of short bullet strings. They carry no fields of their own and
    #: are never referenced individually, so a child table would add a join for
    #: nothing.
    items = models.JSONField(default=list, blank=True)

    image = models.ForeignKey(
        "media_library.MediaAsset",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    image_ratio = models.CharField(
        max_length=8, choices=RATIO_CHOICES, default="16/9"
    )

    class Meta(OrderedItemModel.Meta):
        indexes = [models.Index(fields=["service", "order"])]

    def __str__(self):
        return f"{self.service.title} — {self.label}"


class ServiceProcessStep(OrderedItemModel, TimeStampedModel):
    """A stage in how this particular service runs.

    Distinct from `pages.ProcessStep`, which belongs to a page section: this one
    is the service's own process and travels with it.
    """

    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="process_steps"
    )

    number = models.CharField(max_length=8, blank=True)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)

    class Meta(OrderedItemModel.Meta):
        indexes = [models.Index(fields=["service", "order"])]

    def __str__(self):
        return f"{self.service.title} — {self.title}"


class ServiceGalleryItem(OrderedItemModel, TimeStampedModel):
    """Supporting imagery on a service detail page."""

    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="gallery_items"
    )
    media = models.ForeignKey(
        "media_library.MediaAsset", on_delete=models.PROTECT, related_name="+"
    )
    caption = models.CharField(max_length=500, blank=True)

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["service", "media"], name="unique_service_gallery_media"
            )
        ]
        indexes = [models.Index(fields=["service", "order"])]

    def __str__(self):
        return f"{self.service.title} — image {self.order}"
