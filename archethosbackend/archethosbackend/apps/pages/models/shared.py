"""
Section building blocks used by more than one page.

A section model is shared when its *structure* is genuinely identical across
pages — every page opens with a hero and closes with a call to action, and those
carry the same fields wherever they appear. Each page still owns its own row, so
the copy differs; only the shape is reused.

Where a section merely looks similar but holds different content, it gets its
own model in that page's module instead.
"""

from django.db import models

from archethosbackend.apps.core.models import OrderedItemModel, TimeStampedModel


class SectionHeading(models.Model):
    """Eyebrow / heading / lead / link — the standard block above a section.

    Abstract, so it adds no table. This is shared shape, not a shared row: the
    generic `PageSection` table this refactor removed is what happens when the
    two get confused.
    """

    eyebrow = models.CharField(max_length=120, blank=True)
    heading = models.CharField(max_length=255, blank=True)
    lead = models.TextField(blank=True)

    link_label = models.CharField(max_length=120, blank=True)
    link_url = models.CharField(max_length=500, blank=True)

    class Meta:
        abstract = True


class HeroSection(TimeStampedModel):
    """The opening frame of a page.

    Slides are a child table even where the design shows one, because a static
    hero is a slider with a single slide — modelling it as nullable fields on
    the section *and* as slides would give two places to look.

    There is no `variant` field. Whether this renders as one frame or advances
    through several is the page's own decision, written into its component: the
    home page's hero is a slider and the about page's is not, and no value stored
    here would change that. A column the site never reads is worse than a missing
    one, because it looks like a setting.
    """

    #: Only meaningful where the page renders a slider; harmless elsewhere.
    autoplay_seconds = models.DecimalField(
        max_digits=4, decimal_places=1, default=6.5
    )

    def __str__(self):
        first = self.slides.first()
        return first.heading if first else "Hero (empty)"


class HeroSlide(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        HeroSection, on_delete=models.CASCADE, related_name="slides"
    )

    eyebrow = models.CharField(max_length=120, blank=True)
    heading = models.CharField(max_length=255)
    lead = models.TextField(blank=True)

    media = models.ForeignKey(
        "media_library.MediaAsset", on_delete=models.PROTECT, related_name="+"
    )

    class Meta(OrderedItemModel.Meta):
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return self.heading


class CTASection(SectionHeading, TimeStampedModel):
    """The closing call to action. Every page has one."""

    body = models.TextField(blank=True)

    media = models.ForeignKey(
        "media_library.MediaAsset",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )

    #: `link_label`/`link_url` from SectionHeading carry the primary action.
    secondary_label = models.CharField(max_length=120, blank=True)
    secondary_url = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return self.heading or "Call to action"


class ProcessSection(SectionHeading, TimeStampedModel):
    """A numbered sequence of stages.

    Shared by the about and services pages, which describe the same four-stage
    process in different words. Same structure, two rows.
    """

    def __str__(self):
        return self.heading or "Process"


class ProcessStep(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        ProcessSection, on_delete=models.CASCADE, related_name="steps"
    )

    #: Authored, not derived from `order`: the studio writes "01", and a step
    #: may be renumbered in copy without being reordered on the page.
    number = models.CharField(max_length=8, blank=True)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)

    class Meta(OrderedItemModel.Meta):
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return self.title


class RichTextSection(SectionHeading, TimeStampedModel):
    """Long-form prose with headed blocks — the legal pages.

    Blocks rather than one HTML field so the frontend can render an anchor list
    and the studio cannot paste markup into the page.
    """

    intro = models.TextField(blank=True)
    updated_on = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.heading or "Rich text"


class RichTextBlock(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        RichTextSection, on_delete=models.CASCADE, related_name="blocks"
    )

    title = models.CharField(max_length=255)
    body = models.TextField()

    class Meta(OrderedItemModel.Meta):
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return self.title


def section(to):
    """A page's link to one of its sections.

    Declared on the page so the model reads as the page's structure — open
    HomePage and the field list *is* the running order (see §16: page structure
    is code, not data). Nullable so a page row can exist before its sections are
    populated; `Page.clean()` is what refuses to publish an incomplete one.

    PROTECT because a section is meaningful only as part of its page: deleting
    one out from under a live page should fail loudly, not blank the page.
    """
    return models.OneToOneField(
        to,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )
