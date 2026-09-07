"""
The locations page.

The cities are master data. This page adds the framing and a visiting note —
the latter exists because the studio has confirmed the cities but not the
premises, and the page must read sensibly while addresses are blank.
"""

from django.db import models

from archethosbackend.apps.core.models import OrderedItemModel, TimeStampedModel

from .base import SectionedPage
from .shared import CTASection, HeroSection, SectionHeading, section


class LocationsListSection(SectionHeading, TimeStampedModel):
    """Every city the studio works from."""

    def __str__(self):
        return self.heading or "Locations"


class LocationsListItem(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        LocationsListSection, on_delete=models.CASCADE, related_name="items"
    )
    location = models.ForeignKey(
        "content.Location", on_delete=models.PROTECT, related_name="list_section_items"
    )

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["section", "location"], name="unique_locations_list_item"
            )
        ]
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return str(self.location)


class VisitingSection(SectionHeading, TimeStampedModel):
    """How to arrange a visit while there is no published street address."""

    body = models.TextField(blank=True)

    def __str__(self):
        return self.heading or "Visiting"


class LocationsPage(SectionedPage):
    required_sections = ("hero", "locations")

    hero = section(HeroSection)
    locations = section(LocationsListSection)
    visiting = section(VisitingSection)
    cta = section(CTASection)

    class Meta:
        verbose_name = "Locations page"
        verbose_name_plural = "Locations page"
