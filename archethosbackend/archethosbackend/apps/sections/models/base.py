"""
The Section hierarchy.

`Section` is a **concrete** parent (Django multi-table inheritance) so
`PageSection.section` can be a real ForeignKey with real database integrity.
See DEVELOPMENT_PLAN.md §2.9 for why MTI beat GenericForeignKey, a dozen sparse
nullable FKs, and a JSONField blob.
"""

from django.db import models

from archethosbackend.apps.core.models import TimeStampedModel


class SectionType(models.TextChoices):
    """One value per frontend component.

    The string is the contract with the Next.js section registry: the frontend
    maps `section.type` to a component, so these values must not be renamed
    casually.
    """

    HERO = "hero", "Hero"
    INTRO = "intro", "Studio intro"
    COUNTER = "counter", "Counters / stats band"
    FEATURED_PROJECTS = "featured_projects", "Featured projects"
    SERVICES = "services", "Services"
    GALLERY = "gallery", "Gallery"
    FAQ = "faq", "FAQ"
    CTA = "cta", "Call to action"
    CONTACT_INFO = "contact_info", "Contact info"
    RICH_TEXT = "rich_text", "Rich text"


class Section(TimeStampedModel):
    """Common parent for every section type.

    Carries only what page composition needs to work without knowing the
    concrete type: what kind of section this is, and what to call it in the CMS.
    Everything else lives on the subclass.
    """

    #: Overridden on each concrete subclass; never accepted from a client.
    SECTION_TYPE = None

    section_type = models.CharField(
        max_length=32,
        choices=SectionType.choices,
        db_index=True,
        editable=False,
        help_text="Set automatically from the concrete model.",
    )

    internal_label = models.CharField(
        max_length=255,
        help_text=(
            'Admin-facing name, e.g. "Home - main hero" or "About - studio hero". '
            "Never shown on the public site; it exists so the section browser can "
            "tell several heroes apart."
        ),
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["section_type", "-created_at"])]

    def __str__(self):
        return f"{self.get_section_type_display()} — {self.internal_label}"

    def save(self, *args, **kwargs):
        # Derived from the class, so section_type can never drift from reality —
        # which the aggregate API depends on when it batches by type.
        if self.SECTION_TYPE is not None:
            self.section_type = self.SECTION_TYPE
        super().save(*args, **kwargs)

    # NOTE: `used_by_pages` lives here once PageSection exists (Phase 9). Sections
    # are shared, so the admin must show which pages compose one before offering
    # a delete.
