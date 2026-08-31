from django.db import models

from archethosbackend.apps.core.models import (
    PublishableModel,
    SEOModel,
    SluggedModel,
    TimeStampedModel,
)


class Service(SluggedModel, PublishableModel, SEOModel, TimeStampedModel):
    """What the studio offers: Architecture, Interior Design, Vastu Consultancy…

    Reused by ServicesSection and linked from Projects, so it is master content
    rather than something a section owns.
    """

    short_description = models.CharField(
        max_length=500, blank=True, help_text="One line, used on cards and in listings."
    )
    description = models.TextField(blank=True)

    featured_image = models.ForeignKey(
        "media_library.MediaAsset",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    icon = models.ForeignKey(
        "media_library.MediaAsset",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    #: Default display order in listings; a ServicesSection can override it.
    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["order", "title"]
        indexes = [models.Index(fields=["status", "published_at"])]
