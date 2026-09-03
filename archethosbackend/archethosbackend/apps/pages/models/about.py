"""
The about page.

Mission, vision and the founder message are section content rather than master
data: they describe this studio once, on this page, and are not displayed
anywhere else. Locations are the opposite — the same two cities appear here, on
the home page and on the locations page, so they come through an item model.
"""

from django.db import models

from archethosbackend.apps.core.models import OrderedItemModel, TimeStampedModel

from .base import SectionedPage
from .shared import (
    CTASection,
    HeroSection,
    ProcessSection,
    SectionHeading,
    Tone,
    section,
)


class StudioStorySection(SectionHeading, TimeStampedModel):
    """How the studio came to work the way it does."""

    body = models.TextField(blank=True)
    tone = models.CharField(max_length=16, choices=Tone.choices, default=Tone.BONE)

    media = models.ForeignKey(
        "media_library.MediaAsset",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.heading or "Studio story"


class MissionVisionSection(TimeStampedModel):
    """Two numbered blocks, rendered as a pair.

    A block table rather than two sets of mission_* / vision_* columns: they are
    structurally identical and the design alternates their image side, which is
    per-block configuration rather than a property of either one.
    """

    tone = models.CharField(max_length=16, choices=Tone.choices, default=Tone.BONE_DEEP)

    def __str__(self):
        return "Mission and vision"


class MissionVisionBlock(OrderedItemModel, TimeStampedModel):
    SIDE_CHOICES = [("left", "Image left"), ("right", "Image right")]

    section = models.ForeignKey(
        MissionVisionSection, on_delete=models.CASCADE, related_name="blocks"
    )

    #: Authored, e.g. "01" — see ProcessStep.number.
    numeral = models.CharField(max_length=8, blank=True)
    eyebrow = models.CharField(max_length=120, blank=True)
    heading = models.CharField(max_length=255)
    body = models.TextField(blank=True)

    #: Short supporting statements, one per line in the design.
    points = models.JSONField(default=list, blank=True)

    media = models.ForeignKey(
        "media_library.MediaAsset",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )
    side = models.CharField(max_length=8, choices=SIDE_CHOICES, default="right")

    class Meta(OrderedItemModel.Meta):
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return self.heading


class FounderSection(SectionHeading, TimeStampedModel):
    """A message from the studio.

    Name, role, credentials and portrait are all optional and must stay that
    way. The studio has not confirmed a principal, and the frontend renders a
    neutral attribution while they are blank. Never populate these with
    plausible values — an invented principal is the most damaging thing a
    practice site can carry.
    """

    #: Paragraphs, one entry each.
    message = models.JSONField(default=list, blank=True)

    name = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=255, blank=True)
    credentials = models.CharField(max_length=255, blank=True)
    fallback_attribution = models.CharField(
        max_length=255,
        blank=True,
        help_text="Used while the name above is blank.",
    )

    portrait = models.ForeignKey(
        "media_library.MediaAsset",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )
    media = models.ForeignKey(
        "media_library.MediaAsset",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )

    @property
    def is_attributed(self):
        """False while the studio has not confirmed a principal."""
        return bool(self.name)

    def __str__(self):
        return self.heading or "Founder message"


class PhilosophySection(SectionHeading, TimeStampedModel):
    statement_lines = models.JSONField(
        default=list,
        blank=True,
        help_text="One string per rendered line of the statement.",
    )
    tone = models.CharField(max_length=16, choices=Tone.choices, default=Tone.INK)

    def __str__(self):
        return self.heading or "Philosophy"


class PhilosophyPoint(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        PhilosophySection, on_delete=models.CASCADE, related_name="points"
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)

    class Meta(OrderedItemModel.Meta):
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return self.title


class AboutPresenceSection(SectionHeading, TimeStampedModel):
    LAYOUT_CHOICES = [("grid", "Grid"), ("stacked", "Stacked")]

    layout = models.CharField(max_length=16, choices=LAYOUT_CHOICES, default="stacked")
    tone = models.CharField(max_length=16, choices=Tone.choices, default=Tone.BONE)

    def __str__(self):
        return self.heading or "Our presence"


class AboutLocationItem(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        AboutPresenceSection, on_delete=models.CASCADE, related_name="items"
    )
    location = models.ForeignKey(
        "content.Location", on_delete=models.PROTECT, related_name="about_section_items"
    )

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["section", "location"], name="unique_about_location_item"
            )
        ]
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return str(self.location)


class AboutPage(SectionedPage):
    required_sections = ("hero", "story", "cta")

    hero = section(HeroSection)
    story = section(StudioStorySection)
    mission_vision = section(MissionVisionSection)
    founder = section(FounderSection)
    process = section(ProcessSection)
    philosophy = section(PhilosophySection)
    presence = section(AboutPresenceSection)
    cta = section(CTASection)

    class Meta:
        verbose_name = "About page"
        verbose_name_plural = "About page"
