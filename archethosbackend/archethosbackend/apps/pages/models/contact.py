"""
The contact page.

The enquiry form itself lives in the `enquiries` app — this page owns the copy
around it, not the submission. Studio contact details come from `Company`
rather than being retyped here, so a changed phone number is changed once.
"""

from django.db import models

from archethosbackend.apps.core.models import OrderedItemModel, TimeStampedModel

from .base import SectionedPage
from .shared import CTASection, HeroSection, SectionHeading, Tone, section


class ContactFormSection(SectionHeading, TimeStampedModel):
    """The enquiry form and the copy framing it."""

    tone = models.CharField(max_length=16, choices=Tone.choices, default=Tone.BONE)

    submit_label = models.CharField(max_length=120, blank=True)
    success_message = models.TextField(
        blank=True, help_text="Shown after an enquiry is accepted."
    )
    consent_note = models.TextField(
        blank=True, help_text="Small print beneath the submit button."
    )

    media = models.ForeignKey(
        "media_library.MediaAsset",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.heading or "Enquiry form"


class ContactDetailsSection(SectionHeading, TimeStampedModel):
    """Studio details beside the form.

    Deliberately thin: the email, phone and address render from `Company`. This
    section exists for the words around them and for a note to show when the
    studio has not published direct contact details.
    """

    body = models.TextField(blank=True)
    no_details_note = models.TextField(
        blank=True,
        help_text="Shown when Company has no published email or phone.",
    )

    def __str__(self):
        return self.heading or "Contact details"


class WhatHappensSection(SectionHeading, TimeStampedModel):
    """What the studio does after an enquiry arrives."""

    tone = models.CharField(max_length=16, choices=Tone.choices, default=Tone.INK)

    def __str__(self):
        return self.heading or "What happens next"


class WhatHappensStep(OrderedItemModel, TimeStampedModel):
    section = models.ForeignKey(
        WhatHappensSection, on_delete=models.CASCADE, related_name="steps"
    )

    number = models.CharField(max_length=8, blank=True)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)

    class Meta(OrderedItemModel.Meta):
        indexes = [models.Index(fields=["section", "order"])]

    def __str__(self):
        return self.title


class ContactPage(SectionedPage):
    required_sections = ("hero", "form")

    hero = section(HeroSection)
    form = section(ContactFormSection)
    details = section(ContactDetailsSection)
    what_happens = section(WhatHappensSection)
    cta = section(CTASection)

    class Meta:
        verbose_name = "Contact page"
        verbose_name_plural = "Contact page"
