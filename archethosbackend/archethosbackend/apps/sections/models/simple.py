"""Sections with no child collection — their content is entirely their own fields."""

from django.db import models

from .base import Section, SectionType


class IntroSection(Section):
    """A block of studio narrative with one supporting image."""

    SECTION_TYPE = SectionType.INTRO

    eyebrow = models.CharField(max_length=255, blank=True)
    heading = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)

    image = models.ForeignKey(
        "media_library.MediaAsset",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    cta_label = models.CharField(max_length=100, blank=True)
    cta_url = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name = "Intro section"


class CTASection(Section):
    """Deliberately reusable — one "Start a project" CTA is shared by many pages.

    That is why `PageSection.section` is PROTECT: detaching it from one page must
    never delete it out from under the others.
    """

    SECTION_TYPE = SectionType.CTA

    eyebrow = models.CharField(max_length=255, blank=True)
    heading = models.CharField(max_length=255)
    body = models.TextField(blank=True)

    background_media = models.ForeignKey(
        "media_library.MediaAsset",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    button_label = models.CharField(max_length=100, blank=True)
    button_url = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name = "CTA section"


class ContactInfoSection(Section):
    SECTION_TYPE = SectionType.CONTACT_INFO

    heading = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=64, blank=True)
    email = models.EmailField(blank=True)
    office_hours = models.CharField(max_length=255, blank=True)
    map_embed_url = models.URLField(max_length=500, blank=True)

    class Meta:
        verbose_name = "Contact info section"


class RichTextSection(Section):
    """Long-form prose. Carries /legal/privacy and /legal/terms.

    `body` holds HTML produced by the admin editor. It is rendered by the
    frontend, so whoever can write it can inject script into that page — the same
    exposure as Company.head_inject. Treat `sections.change_richtextsection` as a
    trusted permission and do not hand it to routine editors.
    """

    SECTION_TYPE = SectionType.RICH_TEXT

    heading = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)

    #: e.g. "Last updated 12 March 2026" — legal pages need a visible date.
    updated_note = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Rich text section"
