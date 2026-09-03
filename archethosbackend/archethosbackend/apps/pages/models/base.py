"""
The shared behaviour of a page.

Every page is a singleton — there is exactly one home page — carrying SEO and a
fixed set of sections. What differs between them is only *which* sections, which
is why this is an abstract base and not a `Page` table.
"""

from django.core.exceptions import ValidationError
from django.db import models

from archethosbackend.apps.core.models import (
    SEOModel,
    SingletonModel,
    TimeStampedModel,
)


class SectionedPage(SingletonModel, SEOModel, TimeStampedModel):
    """Abstract: adds no table, and every page below is a real, named model.

    Deliberately not called `BasePage` — the point of this refactor was to
    delete the generic page table of that name. This is a mixin carrying SEO,
    publish state and the required-section check, the way `SEOModel` carries
    meta tags. It never makes a page generic: `HomePage.hero` is still a real
    column on a real table.

    `required_sections` is the §17 contract. A page that names a section in this
    tuple cannot be published without it, so the frontend never has to guard
    against a missing hero.
    """

    #: Field names on the subclass that must be populated before publishing.
    required_sections: tuple[str, ...] = ()

    is_published = models.BooleanField(
        default=False,
        help_text="Unpublished pages are hidden from the public API.",
    )

    class Meta:
        abstract = True

    def missing_sections(self):
        return [
            name
            for name in self.required_sections
            if getattr(self, f"{name}_id", None) is None
        ]

    def clean(self):
        super().clean()
        missing = self.missing_sections()
        if self.is_published and missing:
            raise ValidationError(
                {
                    name: "Required before this page can be published."
                    for name in missing
                }
            )

    def __str__(self):
        return self._meta.verbose_name
