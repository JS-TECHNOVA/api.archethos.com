"""
The journal index page.

Featured entries are curated through an item model; the list below them is not,
because a journal that needs a manual entry per post stops being written in.
The list section therefore configures paging and ordering only.
"""

from django.db import models

from archethosbackend.apps.core.models import OrderedItemModel, TimeStampedModel

from .base import SectionedPage
from .shared import CTASection, HeroSection, SectionHeading, section


class JournalFeaturedSection(SectionHeading, TimeStampedModel):
    """The entries worth starting with."""

    def __str__(self):
        return self.heading or "Featured writing"


class JournalFeaturedItem(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        JournalFeaturedSection, on_delete=models.CASCADE, related_name="items"
    )
    post = models.ForeignKey(
        "content.BlogPost", on_delete=models.PROTECT, related_name="featured_items"
    )

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["section", "post"], name="unique_journal_featured_item"
            )
        ]
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return str(self.post)


class JournalListSection(SectionHeading, TimeStampedModel):
    """Every published post, newest first. Not curated by design."""

    page_size = models.PositiveSmallIntegerField(default=12)
    show_categories = models.BooleanField(default=True)

    def __str__(self):
        return self.heading or "Journal list"


class JournalPage(SectionedPage):
    required_sections = ("hero", "list")

    hero = section(HeroSection)
    featured = section(JournalFeaturedSection)
    list = section(JournalListSection)
    cta = section(CTASection)

    class Meta:
        verbose_name = "Journal page"
        verbose_name_plural = "Journal page"
