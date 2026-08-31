"""
Pages and their composition.

A page does not own section content; it owns an **ordered composition** of
sections (DEVELOPMENT_PLAN.md §2.2):

    Page ──1:N──> PageSection ──N:1──> Section

Home, About, Contact, Gallery, Locations and the legal pages are all just `Page`
rows. Adding a page is data entry, not a migration.
"""

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from archethosbackend.apps.core.models import (
    PublishableModel,
    SEOModel,
    SingletonModel,
    TimeStampedModel,
)


#: Page slugs mirror frontend routes, which nest: "legal/privacy" is a real
#: route. A plain SlugField forbids "/", so validation is spelled out here.
#: Lowercase segments of letters, digits and hyphens, separated by single
#: slashes, no leading or trailing slash.
page_slug_validator = RegexValidator(
    regex=r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*$",
    message=(
        "Use lowercase letters, numbers and hyphens. Nested routes are allowed, "
        'e.g. "legal/privacy". No leading or trailing slash.'
    ),
)


class Page(PublishableModel, SEOModel, TimeStampedModel):
    """One route on the public site.

    Uses the same `status` / `published_at` pair as every content model rather
    than a bespoke `is_published` boolean, so "is this live?" means exactly one
    thing across the whole system (plan §2.6).
    """

    name = models.CharField(max_length=255, help_text="Admin-facing page name.")
    slug = models.CharField(
        max_length=255,
        unique=True,
        validators=[page_slug_validator],
        help_text=(
            "Public identifier: /api/v1/public/pages/<slug>/. Matches the "
            'frontend route, e.g. "home", "about", "legal/privacy".'
        ),
    )

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["status", "published_at"])]

    def __str__(self):
        return self.name


class PageSection(TimeStampedModel):
    """A section's placement on a page.

    Carries what only the placement knows: where in the order it sits, whether it
    is currently shown, and what role it plays on this particular page.
    """

    page = models.ForeignKey(
        Page, on_delete=models.CASCADE, related_name="page_sections"
    )

    # PROTECT: detaching a section from a page must never delete the section,
    # which may well be composed into several other pages.
    section = models.ForeignKey(
        "sections.Section", on_delete=models.PROTECT, related_name="page_usages"
    )

    section_key = models.CharField(
        max_length=100,
        help_text=(
            'What this instance is for on this page, e.g. "main_hero", '
            '"bottom_cta". Distinct from the section\'s type, which says which '
            "component renders it. Lets one page carry two CTAs."
        ),
    )

    #: Display order only — in no constraint, so bulk reorder is one bulk_update
    #: with no intermediate state to violate (plan §2.3).
    order = models.PositiveIntegerField(default=0, db_index=True)

    is_visible = models.BooleanField(
        default=True,
        help_text="Hide on this page without detaching it or affecting other pages.",
    )

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            # Two sections cannot claim the same slot on one page. Note there is
            # deliberately no unique(page, order): that would deadlock the atomic
            # reorder it is meant to protect.
            models.UniqueConstraint(
                fields=["page", "section_key"], name="unique_page_section_key"
            )
        ]
        indexes = [models.Index(fields=["page", "order"])]

    def __str__(self):
        return f"{self.page.name} / {self.section_key}"


class Company(SingletonModel, TimeStampedModel):
    """Site-wide settings: one row, loaded with `Company.load()`."""

    name = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)

    logo = models.ForeignKey(
        "media_library.MediaAsset",
        null=True, blank=True, on_delete=models.PROTECT, related_name="+",
    )
    favicon = models.ForeignKey(
        "media_library.MediaAsset",
        null=True, blank=True, on_delete=models.PROTECT, related_name="+",
    )

    # JSONB rather than TextField holding JSON: same payload over the wire, but
    # validated on write and queryable.
    social_urls = models.JSONField(
        default=dict, blank=True,
        help_text='{"instagram": "https://...", "linkedin": "https://..."}',
    )
    contacts = models.JSONField(
        default=dict, blank=True,
        help_text='{"emails": ["..."], "phones": ["..."], "whatsapp": "..."}',
    )
    header_links = models.JSONField(
        default=list, blank=True,
        help_text='[{"label": "Projects", "url": "/projects"}]',
    )
    footer_links = models.JSONField(
        default=list, blank=True,
        help_text='[{"heading": "Company", "links": [{"label": "...", "url": "..."}]}]',
    )

    # ⚠ Raw markup rendered on every page of the live site. Whoever can write
    # these can execute arbitrary JavaScript for every visitor, so the write
    # serializer restricts *these two fields only* to superusers.
    head_inject = models.TextField(
        blank=True, help_text="Raw markup injected into <head>. Superuser only."
    )
    body_inject = models.TextField(
        blank=True, help_text="Raw markup injected before </body>. Superuser only."
    )

    # Global SEO defaults; a Page's own SEO fields override these when set.
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Company"

    def __str__(self):
        return self.name or "Company settings"


def validate_link_list(value):
    """`[{"label": ..., "url": ...}]` — the shape header_links must hold."""
    if not isinstance(value, list):
        raise ValidationError("Expected a list of {label, url} objects.")
    for entry in value:
        if not isinstance(entry, dict):
            raise ValidationError("Each entry must be an object.")
        missing = {"label", "url"} - set(entry)
        if missing:
            raise ValidationError(
                f"Each entry needs 'label' and 'url'; missing {', '.join(sorted(missing))}."
            )


def validate_footer_groups(value):
    """`[{"heading": ..., "links": [{"label", "url"}]}]`."""
    if not isinstance(value, list):
        raise ValidationError("Expected a list of {heading, links} objects.")
    for group in value:
        if not isinstance(group, dict) or "links" not in group:
            raise ValidationError("Each group needs a 'links' list.")
        validate_link_list(group["links"])


def validate_string_map(value):
    """A flat object of string values, e.g. social_urls."""
    if not isinstance(value, dict):
        raise ValidationError("Expected an object of string values.")
    for key, item in value.items():
        if not isinstance(item, str):
            raise ValidationError(f"'{key}' must be a string.")


def validate_contacts(value):
    """`{"emails": [...], "phones": [...], ...}` — lists or strings only."""
    if not isinstance(value, dict):
        raise ValidationError("Expected an object.")
    for key, item in value.items():
        if isinstance(item, list):
            if not all(isinstance(entry, str) for entry in item):
                raise ValidationError(f"'{key}' must be a list of strings.")
        elif not isinstance(item, str):
            raise ValidationError(f"'{key}' must be a string or a list of strings.")
