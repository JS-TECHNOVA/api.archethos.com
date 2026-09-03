"""
The projects index page.

An empty selection means "show every published project", which is what the
studio wants by default — otherwise a new project would be invisible until
someone remembered to add it here. Populate the items only to curate.
"""

from django.db import models

from archethosbackend.apps.core.models import OrderedItemModel, TimeStampedModel

from .base import SectionedPage
from .shared import CTASection, HeroSection, SectionHeading, Tone, section


class ProjectIndexSection(SectionHeading, TimeStampedModel):
    tone = models.CharField(max_length=16, choices=Tone.choices, default=Tone.BONE)
    show_filter = models.BooleanField(
        default=True, help_text="Render the category filter above the grid."
    )

    def __str__(self):
        return self.heading or "Project index"

    @property
    def is_curated(self):
        """False when the section falls back to every published project."""
        return self.items.exists()


class ProjectIndexItem(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        ProjectIndexSection, on_delete=models.CASCADE, related_name="items"
    )
    project = models.ForeignKey(
        "content.Project", on_delete=models.PROTECT, related_name="index_section_items"
    )

    class Meta(OrderedItemModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["section", "project"], name="unique_project_index_item"
            )
        ]
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return str(self.project)


class ProjectsPage(SectionedPage):
    required_sections = ("hero", "index")

    hero = section(HeroSection)
    index = section(ProjectIndexSection)
    cta = section(CTASection)

    class Meta:
        verbose_name = "Projects page"
        verbose_name_plural = "Projects page"
