"""
The legal pages.

Two singletons rather than one table with a slug. They are genuinely two fixed
pages at two fixed routes, and a `LegalPage(slug=...)` table would be the same
generic-page mistake this refactor removed, in miniature — it would invite a
third row that no route renders.

Both hold a `RichTextSection`, which is the reuse that actually matters here.
"""

from .base import SectionedPage
from .shared import RichTextSection, section


class PrivacyPage(SectionedPage):
    required_sections = ("body",)

    body = section(RichTextSection)

    class Meta:
        verbose_name = "Privacy page"
        verbose_name_plural = "Privacy page"


class TermsPage(SectionedPage):
    required_sections = ("body",)

    body = section(RichTextSection)

    class Meta:
        verbose_name = "Terms page"
        verbose_name_plural = "Terms page"
