"""
Projects — the portfolio's primary content type.

Everything the detail route at `/projects/[slug]` renders lives here: the five
narrative blocks, the materials schedule and the media. Sections that list
projects reference these rows through item models and never copy their fields.
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


class ProjectStatus(models.TextChoices):
    CONCEPT = "CONCEPT", "Concept"
    ONGOING = "ONGOING", "Ongoing"
    COMPLETED = "COMPLETED", "Completed"


class ProjectCategory(models.TextChoices):
    RESIDENTIAL = "RESIDENTIAL", "Residential"
    COMMERCIAL = "COMMERCIAL", "Commercial"
    INTERIOR = "INTERIOR", "Interior"
    RENOVATION = "RENOVATION", "Renovation"


class ProjectLayout(models.TextChoices):
    """How wide the project's card sits in the index grid.

    A composition decision the studio makes per project — a landscape hero
    earns a full-width card, a portrait one does not — so it belongs to the
    project rather than to the section that happens to list it.
    """

    FULL = "full", "Full width"
    WIDE = "wide", "Wide"
    HALF = "half", "Half width"
    PORTRAIT = "portrait", "Portrait"


class Project(SluggedModel, PublishableModel, SEOModel, TimeStampedModel):
    """One project in the portfolio."""

    short_description = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)

    location = models.CharField(max_length=255, blank=True)
    project_year = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    project_status = models.CharField(
        max_length=16, choices=ProjectStatus.choices, default=ProjectStatus.COMPLETED
    )
    category = models.CharField(
        max_length=16,
        choices=ProjectCategory.choices,
        default=ProjectCategory.RESIDENTIAL,
        db_index=True,
    )
    layout = models.CharField(
        max_length=16, choices=ProjectLayout.choices, default=ProjectLayout.HALF
    )

    cover_image = models.ForeignKey(
        "media_library.MediaAsset",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    # ── The narrative ────────────────────────────────────────────────────────
    # Five named blocks rather than one rich-text body. Every project answers
    # the same five questions, and naming them is what stops a detail page from
    # becoming whatever the last person to write one felt like including.
    design_intent = models.TextField(blank=True)
    spatial_planning = models.TextField(blank=True)
    interior_note = models.TextField(blank=True)
    construction_note = models.TextField(blank=True)
    outcome_note = models.TextField(blank=True)

    #: Curation, not publishing — a featured project can still be a draft.
    is_featured = models.BooleanField(default=False, db_index=True)

    services = models.ManyToManyField(
        "content.Service", blank=True, related_name="projects"
    )

    #: Weighted tsvector, maintained in save(). Never edited by hand.
    search_vector = SearchVectorField(null=True, editable=False)

    class Meta:
        ordering = ["-project_year", "-created_at"]
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["is_featured", "status"]),
            models.Index(fields=["category", "status"]),
            GinIndex(fields=["search_vector"]),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_search_vector()

    def update_search_vector(self):
        """Recompute the tsvector for this row.

        A follow-up UPDATE rather than a value computed in Python, because the
        stemming and weighting are Postgres's job. One extra query per save,
        which is nothing at CMS write volume.

        Rows changed by `update()` or `bulk_update()` bypass this — run
        `manage.py rebuild_search_index` after any bulk edit.
        """
        type(self).objects.filter(pk=self.pk).update(
            search_vector=(
                SearchVector("title", weight="A", config="english")
                + SearchVector("short_description", weight="B", config="english")
                + SearchVector("location", weight="B", config="english")
                + SearchVector("description", weight="C", config="english")
                + SearchVector("design_intent", weight="D", config="english")
            )
        )


class ProjectMaterial(OrderedItemModel, TimeStampedModel):
    """One line of the materials schedule.

    A child table rather than JSON because the studio edits these individually
    and the same material recurs across projects — which makes "every project
    using Kota stone" a question worth being able to answer.
    """

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="materials"
    )

    name = models.CharField(max_length=255, help_text='e.g. "Board-marked concrete".')
    note = models.CharField(
        max_length=500, blank=True, help_text='Where it is used, e.g. "Court paving".'
    )

    class Meta(OrderedItemModel.Meta):
        indexes = [models.Index(fields=["project", "order"])]

    def __str__(self):
        return f"{self.project.title} — {self.name}"


class ProjectMediaKind(models.TextChoices):
    """Which of the three media strips an item belongs to.

    One table with a discriminator rather than three near-identical ones: they
    hold the same fields, are reordered by the same endpoint and are rendered by
    the same component with a different heading.
    """

    GALLERY = "GALLERY", "Gallery"
    FLOOR_PLAN = "FLOOR_PLAN", "Floor plan"
    DRAWING = "DRAWING", "Drawing"


class ProjectGalleryItem(OrderedItemModel, TimeStampedModel):
    """One piece of media attached to a project.

    Media is PROTECT so an image cannot be deleted out from under a published
    project. `order` carries no unique constraint, which is what lets reordering
    be a plain `bulk_update` inside one transaction.

    The uniqueness rule spans `kind` on purpose: the same drawing can legitimately
    appear once in the gallery and once among the drawings, but not twice in
    either.
    """

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="gallery_items"
    )
    media = models.ForeignKey(
        "media_library.MediaAsset", on_delete=models.PROTECT, related_name="+"
    )

    kind = models.CharField(
        max_length=16,
        choices=ProjectMediaKind.choices,
        default=ProjectMediaKind.GALLERY,
        db_index=True,
    )

    #: Per-project, per-placement text. Distinct from the asset's own caption in
    #: the media library, which describes the file wherever it is used; this
    #: describes what it is doing on *this* project.
    title = models.CharField(max_length=255, blank=True)
    caption = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["project", "media", "kind"],
                name="unique_project_media_per_kind",
            )
        ]
        indexes = [
            models.Index(fields=["project", "kind", "order"]),
        ]

    def __str__(self):
        return f"{self.project.title} — {self.get_kind_display()} {self.order}"
