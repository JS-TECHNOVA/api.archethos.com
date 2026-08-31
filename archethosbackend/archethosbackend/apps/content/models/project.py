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


class Project(SluggedModel, PublishableModel, SEOModel, TimeStampedModel):
    """An architecture project — the portfolio's primary content type."""

    short_description = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)

    location = models.CharField(max_length=255, blank=True)
    project_year = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    project_status = models.CharField(
        max_length=16, choices=ProjectStatus.choices, default=ProjectStatus.COMPLETED
    )

    featured_image = models.ForeignKey(
        "media_library.MediaAsset",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    #: Curation, not publishing — a featured project can still be a draft.
    is_featured = models.BooleanField(default=False, db_index=True)

    services = models.ManyToManyField(
        "content.Service", blank=True, related_name="projects"
    )

    class Meta:
        ordering = ["-project_year", "-created_at"]
        indexes = [
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["is_featured", "status"]),
        ]


class ProjectGalleryItem(OrderedItemModel, TimeStampedModel):
    """One image in a project's own gallery.

    Media is PROTECT so an image cannot be deleted out from under a published
    project. `order` carries no constraint (plan §2.3), which is what lets
    reordering be a plain bulk_update inside one transaction.
    """

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="gallery_items"
    )
    media = models.ForeignKey(
        "media_library.MediaAsset", on_delete=models.PROTECT, related_name="+"
    )
    caption = models.CharField(max_length=500, blank=True)

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["project", "media"], name="unique_project_gallery_media"
            )
        ]
        indexes = [models.Index(fields=["project", "order"])]

    def __str__(self):
        return f"{self.project.title} — image {self.order}"
