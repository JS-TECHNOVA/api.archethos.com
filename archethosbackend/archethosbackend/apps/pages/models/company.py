"""
Site-wide settings.

One row, loaded with `Company.load()`. Not a page: this is the header, footer
and contact information every page renders, so it lives beside the pages rather
than inside one of them.
"""

from django.core.exceptions import ValidationError
from django.db import models

from archethosbackend.apps.core.models import SingletonModel, TimeStampedModel


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
