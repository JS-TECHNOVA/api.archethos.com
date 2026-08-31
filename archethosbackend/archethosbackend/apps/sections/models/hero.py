"""Hero sections.

The live homepage hero is a slider of three frames, each with its own headline —
"design it, live in it, build it" — so the sequence is an argument rather than a
slideshow. A single-headline hero model could not express that, so slides are an
ordered child collection.
"""

from django.db import models

from archethosbackend.apps.core.models import OrderedItemModel, TimeStampedModel

from .base import Section, SectionType


class HeroSection(Section):
    SECTION_TYPE = SectionType.HERO

    #: Optional: a one-slide hero is a perfectly ordinary use of this model.
    autoplay_seconds = models.PositiveSmallIntegerField(
        default=0,
        help_text="0 disables auto-advance. Ignored when there is a single slide.",
    )

    class Meta:
        verbose_name = "Hero section"


class HeroSlide(OrderedItemModel, TimeStampedModel):
    """One frame of a hero.

    `heading_lines` is stored as text with one line per row rather than as a JSON
    array: the line breaks are a typographic decision the editor makes, and a
    textarea is the natural way to make it. The serializer splits it back into a
    list for the frontend.
    """

    section = models.ForeignKey(
        HeroSection, on_delete=models.CASCADE, related_name="slides"
    )

    #: Short tab label for the slider control, e.g. "Architecture".
    label = models.CharField(max_length=100, blank=True)
    eyebrow = models.CharField(
        max_length=255, blank=True, help_text='e.g. "Architecture / Interiors / Build".'
    )
    heading = models.TextField(
        help_text="One line per row. Line breaks are preserved as written."
    )
    lead = models.TextField(blank=True)

    media = models.ForeignKey(
        "media_library.MediaAsset",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    cta_label = models.CharField(max_length=100, blank=True)
    cta_url = models.CharField(max_length=500, blank=True)

    class Meta(OrderedItemModel.Meta):
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return self.label or self.heading_lines[0] if self.heading else f"Slide {self.pk}"

    @property
    def heading_lines(self):
        return [line for line in self.heading.splitlines() if line.strip()]
