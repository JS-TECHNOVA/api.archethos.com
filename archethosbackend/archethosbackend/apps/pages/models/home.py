"""
The home page.

Read the field list on `HomePage` top to bottom and you have the page as it
renders — that is the whole point of this design. Adding a section here is a
migration and a component, deliberately: the running order of a nine-page
corporate site is a code decision, not something to be dragged around in an
admin (§16).
"""

from django.db import models

from archethosbackend.apps.core.models import OrderedItemModel, TimeStampedModel

from .base import SectionedPage
from .shared import CTASection, HeroSection, SectionHeading, Tone, section


class HomeIntroSection(SectionHeading, TimeStampedModel):
    """The studio statement below the hero."""

    #: The design breaks this headline by hand — the line breaks carry the
    #: sentence, so they are content and not a CSS concern.
    statement_lines = models.JSONField(
        default=list,
        blank=True,
        help_text="One string per rendered line of the headline.",
    )
    body = models.TextField(blank=True)

    media = models.ForeignKey(
        "media_library.MediaAsset",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.heading or "Studio introduction"


class StatsSection(SectionHeading, TimeStampedModel):
    """The "at a glance" band. The figures themselves are master data."""

    tone = models.CharField(max_length=16, choices=Tone.choices, default=Tone.INK)

    def __str__(self):
        return self.eyebrow or "Statistics"


class StatsSectionItem(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        StatsSection, on_delete=models.CASCADE, related_name="items"
    )
    counter = models.ForeignKey(
        "content.Counter", on_delete=models.PROTECT, related_name="section_items"
    )

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["section", "counter"], name="unique_stats_item"
            )
        ]
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return str(self.counter)


class FeaturedProjectSection(SectionHeading, TimeStampedModel):
    """One project, given the full width of the page.

    A single FK rather than an item table: the design shows exactly one, and an
    ordered list of one would misrepresent what the page can do.
    """

    project = models.ForeignKey(
        "content.Project",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Featured: {self.project}" if self.project_id else "Featured project"


class HomeServicesSection(SectionHeading, TimeStampedModel):
    tone = models.CharField(max_length=16, choices=Tone.choices, default=Tone.BONE)

    def __str__(self):
        return self.heading or "Services"


class HomeServiceItem(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        HomeServicesSection, on_delete=models.CASCADE, related_name="items"
    )
    service = models.ForeignKey(
        "content.Service", on_delete=models.PROTECT, related_name="home_section_items"
    )

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["section", "service"], name="unique_home_service_item"
            )
        ]
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return str(self.service)


class DesignBuildSection(SectionHeading, TimeStampedModel):
    """Why the studio draws and builds the same project."""

    body = models.TextField(blank=True)
    tone = models.CharField(max_length=16, choices=Tone.choices, default=Tone.INK)

    media = models.ForeignKey(
        "media_library.MediaAsset",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.heading or "Design and build"


class DesignBuildPoint(OrderedItemModel, TimeStampedModel):
    """A supporting point. Local to this section, so not master data."""

    section = models.ForeignKey(
        DesignBuildSection, on_delete=models.CASCADE, related_name="points"
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)

    class Meta(OrderedItemModel.Meta):
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return self.title


class HomeProjectsSection(SectionHeading, TimeStampedModel):
    tone = models.CharField(max_length=16, choices=Tone.choices, default=Tone.BONE)

    def __str__(self):
        return self.heading or "Selected work"


class HomeProjectItem(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        HomeProjectsSection, on_delete=models.CASCADE, related_name="items"
    )
    project = models.ForeignKey(
        "content.Project", on_delete=models.PROTECT, related_name="home_section_items"
    )

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["section", "project"], name="unique_home_project_item"
            )
        ]
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return str(self.project)


class HomeGallerySection(SectionHeading, TimeStampedModel):
    """The auto-advancing gallery strip."""

    autoplay_seconds = models.DecimalField(max_digits=4, decimal_places=1, default=6.5)

    def __str__(self):
        return self.eyebrow or "Gallery"


class HomeGalleryItem(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        HomeGallerySection, on_delete=models.CASCADE, related_name="items"
    )
    gallery_item = models.ForeignKey(
        "content.GalleryItem", on_delete=models.PROTECT, related_name="section_items"
    )

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["section", "gallery_item"], name="unique_home_gallery_item"
            )
        ]
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return str(self.gallery_item)


class VastuSection(SectionHeading, TimeStampedModel):
    """The Vastu consultancy teaser."""

    statement = models.TextField(blank=True)
    body = models.TextField(blank=True)
    tone = models.CharField(max_length=16, choices=Tone.choices, default=Tone.BONE_DEEP)

    media = models.ForeignKey(
        "media_library.MediaAsset",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.heading or "Vastu"


class HomeLocationsSection(SectionHeading, TimeStampedModel):
    LAYOUT_CHOICES = [("grid", "Grid"), ("stacked", "Stacked")]

    layout = models.CharField(max_length=16, choices=LAYOUT_CHOICES, default="grid")

    def __str__(self):
        return self.heading or "Locations"


class HomeLocationItem(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        HomeLocationsSection, on_delete=models.CASCADE, related_name="items"
    )
    location = models.ForeignKey(
        "content.Location", on_delete=models.PROTECT, related_name="home_section_items"
    )

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["section", "location"], name="unique_home_location_item"
            )
        ]
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return str(self.location)


class HomePage(SectionedPage):
    """The field order below is the render order on the site."""

    required_sections = ("hero", "intro", "cta")

    hero = section(HeroSection)
    intro = section(HomeIntroSection)
    stats = section(StatsSection)
    featured_project = section(FeaturedProjectSection)
    services = section(HomeServicesSection)
    design_build = section(DesignBuildSection)
    projects = section(HomeProjectsSection)
    gallery = section(HomeGallerySection)
    vastu = section(VastuSection)
    locations = section(HomeLocationsSection)
    cta = section(CTASection)

    class Meta:
        verbose_name = "Home page"
        verbose_name_plural = "Home page"
