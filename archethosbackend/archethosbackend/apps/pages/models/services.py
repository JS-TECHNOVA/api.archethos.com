"""
The services index page.

The five disciplines are master data — a Service exists whether or not this page
lists it, and the same records drive `/services/[slug]` and the home page. This
page owns only the framing around them.
"""

from django.db import models

from archethosbackend.apps.core.models import OrderedItemModel, TimeStampedModel

from .base import SectionedPage
from .shared import (
    CTASection,
    HeroSection,
    ProcessSection,
    SectionHeading,
    section,
)


class ServiceIndexSection(SectionHeading, TimeStampedModel):
    """The list of what the studio does."""

    def __str__(self):
        return self.heading or "Service index"


class ServiceIndexItem(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        ServiceIndexSection, on_delete=models.CASCADE, related_name="items"
    )
    service = models.ForeignKey(
        "content.Service", on_delete=models.PROTECT, related_name="index_section_items"
    )

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["section", "service"], name="unique_service_index_item"
            )
        ]
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return str(self.service)


class ServicesPage(SectionedPage):
    required_sections = ("hero", "index", "cta")

    hero = section(HeroSection)
    index = section(ServiceIndexSection)
    process = section(ProcessSection)
    cta = section(CTASection)

    class Meta:
        verbose_name = "Services page"
        verbose_name_plural = "Services page"
