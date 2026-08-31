from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
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

    #: Weighted tsvector, maintained in save(). Never edited by hand.
    search_vector = SearchVectorField(null=True, editable=False)

    class Meta:
        ordering = ["order", "title"]
        indexes = [
            models.Index(fields=["status", "published_at"]),
            GinIndex(fields=["search_vector"]),
        ]

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
                + SearchVector("short_description", weight="B", config="english")
                + SearchVector("description", weight="C", config="english")
            )
        )
