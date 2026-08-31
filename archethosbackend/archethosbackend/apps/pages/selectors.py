"""
Resolving a page into everything needed to render it.

The one real cost of multi-table inheritance is turning `Section` rows into their
concrete subclasses. Done naively that is N+1. `InheritanceManager`'s
all-subclass LEFT JOIN is worse: it is slower *and* it cannot apply the different
prefetches each type needs — an FAQ section wants `items__faq`, a gallery wants
`items__media`.

So this batches: group the placements by `section_type`, then issue **one query
per distinct type present**, each with that type's prefetches from
SECTION_REGISTRY. The result is a query count bounded by the number of section
*types* on the page, not by the number of sections or the volume of content
inside them. A page with 40 gallery images costs the same as one with 4
(DEVELOPMENT_PLAN.md §13).
"""

import logging
from dataclasses import dataclass

from archethosbackend.apps.sections.registry import SECTION_REGISTRY

from .models import Page, PageSection

logger = logging.getLogger(__name__)


@dataclass
class ResolvedSection:
    """One rendered section, ready to serialize."""

    placement_id: int
    section_key: str
    section_type: str
    data: dict


@dataclass
class ResolvedPage:
    page: Page
    sections: list


def get_live_page(slug):
    """The published page for a slug, or None.

    Draft and archived pages return None so the view can 404. A 403 would confirm
    the page exists, which is information the public API should not leak.
    """
    return (
        Page.objects.live()
        .select_related("og_image")
        .filter(slug=slug)
        .first()
    )


def resolve_page(page):
    """Load and serialize every visible section on a page."""
    placements = list(
        PageSection.objects.filter(page=page, is_visible=True)
        .select_related("section")
        .order_by("order", "id")
    )

    by_type = {}
    for placement in placements:
        by_type.setdefault(placement.section.section_type, []).append(
            placement.section_id
        )

    # One query per distinct type, with that type's prefetches applied.
    concrete = {}
    for section_type, ids in by_type.items():
        spec = SECTION_REGISTRY.get(section_type)
        if spec is None:
            # A section whose type is not registered cannot be rendered. Skip it
            # rather than 500 the whole page, and make the gap findable.
            logger.warning(
                "Section type %r is not in SECTION_REGISTRY; skipping %s section(s) "
                "on page %r.",
                section_type, len(ids), page.slug,
            )
            continue

        queryset = spec.public_queryset(spec.model.objects.filter(pk__in=ids))
        for instance in queryset:
            concrete[instance.pk] = (spec, instance)

    resolved = []
    for placement in placements:
        found = concrete.get(placement.section_id)
        if found is None:
            continue
        spec, instance = found
        resolved.append(
            ResolvedSection(
                placement_id=placement.id,
                section_key=placement.section_key,
                section_type=placement.section.section_type,
                data=spec.public_serializer(instance).data,
            )
        )

    return ResolvedPage(page=page, sections=resolved), placements, concrete


def last_modified(page, placements, concrete):
    """Newest `updated_at` anywhere in the page's graph, for the ETag.

    Everything here is already in memory, so this costs no extra queries.
    """
    stamps = [page.updated_at]
    stamps.extend(placement.updated_at for placement in placements)
    stamps.extend(instance.updated_at for _, instance in concrete.values())
    return max(stamps)
