"""
The section registry.

One mapping from `section_type` to everything the rest of the system needs to
know about that type. There is deliberately no `if section_type == "hero"`
anywhere else in the codebase — adding a section means adding a model, its
serializers and one entry here, and the URLs, admin CRUD and aggregate page API
all start working.

`public_queryset` is the important field: the aggregate page API resolves a
page's sections by grouping them by type and issuing **one query per distinct
type**, applying that type's prefetches. That is what keeps the query count flat
as content grows (DEVELOPMENT_PLAN.md §13).
"""

from dataclasses import dataclass
from typing import Callable

from django.db.models import Prefetch, QuerySet

from archethosbackend.apps.content.models import ProjectGalleryItem

from .models import (
    ContactInfoSection,
    CounterSection,
    CounterSectionItem,
    CTASection,
    FAQSection,
    FAQSectionItem,
    FeaturedProjectItem,
    FeaturedProjectsSection,
    GallerySection,
    GallerySectionItem,
    HeroSection,
    HeroSlide,
    IntroSection,
    RichTextSection,
    SectionType,
    ServiceSectionItem,
    ServicesSection,
)
from .serializers import (
    ContactInfoSectionDetailSerializer,
    ContactInfoSectionListSerializer,
    ContactInfoSectionWriteSerializer,
    CounterSectionDetailSerializer,
    CounterSectionItemSerializer,
    CounterSectionItemWriteSerializer,
    CounterSectionListSerializer,
    CounterSectionWriteSerializer,
    CTASectionDetailSerializer,
    CTASectionListSerializer,
    CTASectionWriteSerializer,
    FAQSectionDetailSerializer,
    FAQSectionItemSerializer,
    FAQSectionItemWriteSerializer,
    FAQSectionListSerializer,
    FAQSectionWriteSerializer,
    FeaturedProjectItemSerializer,
    FeaturedProjectItemWriteSerializer,
    FeaturedProjectsSectionDetailSerializer,
    FeaturedProjectsSectionListSerializer,
    FeaturedProjectsSectionWriteSerializer,
    GallerySectionDetailSerializer,
    GallerySectionItemSerializer,
    GallerySectionItemWriteSerializer,
    GallerySectionListSerializer,
    GallerySectionWriteSerializer,
    HeroSectionDetailSerializer,
    HeroSectionListSerializer,
    HeroSectionWriteSerializer,
    HeroSlideSerializer,
    HeroSlideWriteSerializer,
    IntroSectionDetailSerializer,
    IntroSectionListSerializer,
    IntroSectionWriteSerializer,
    PublicContactInfoSectionSerializer,
    PublicCounterSectionSerializer,
    PublicCTASectionSerializer,
    PublicFAQSectionSerializer,
    PublicFeaturedProjectsSectionSerializer,
    PublicGallerySectionSerializer,
    PublicHeroSectionSerializer,
    PublicIntroSectionSerializer,
    PublicRichTextSectionSerializer,
    PublicServicesSectionSerializer,
    RichTextSectionDetailSerializer,
    RichTextSectionListSerializer,
    RichTextSectionWriteSerializer,
    ServiceSectionItemSerializer,
    ServiceSectionItemWriteSerializer,
    ServicesSectionDetailSerializer,
    ServicesSectionListSerializer,
    ServicesSectionWriteSerializer,
)


@dataclass(frozen=True)
class ItemSpec:
    """An ordered child collection belonging to a section type."""

    model: type
    #: Reverse accessor from the section, e.g. "items" or "slides".
    related_name: str
    serializer: type
    write_serializer: type
    #: FK on the item pointing at the master content, e.g. "faq". None for slides,
    #: which own their content rather than referencing it.
    content_field: str | None


@dataclass(frozen=True)
class SectionSpec:
    model: type
    url_segment: str
    list_serializer: type
    detail_serializer: type
    write_serializer: type
    public_serializer: type
    #: Applied by the aggregate API when batch-loading this type.
    public_queryset: Callable[[QuerySet], QuerySet]
    #: Applied by the admin detail view.
    admin_queryset: Callable[[QuerySet], QuerySet]
    #: Annotation name -> count field, applied by the admin list view.
    list_annotations: dict
    items: ItemSpec | None = None


def _identity(queryset):
    return queryset


SECTION_REGISTRY: dict[str, SectionSpec] = {
    SectionType.HERO: SectionSpec(
        model=HeroSection,
        url_segment="hero",
        list_serializer=HeroSectionListSerializer,
        detail_serializer=HeroSectionDetailSerializer,
        write_serializer=HeroSectionWriteSerializer,
        public_serializer=PublicHeroSectionSerializer,
        public_queryset=lambda qs: qs.prefetch_related(
            Prefetch("slides", queryset=HeroSlide.objects.select_related("media"))
        ),
        admin_queryset=lambda qs: qs.prefetch_related(
            Prefetch("slides", queryset=HeroSlide.objects.select_related("media"))
        ),
        list_annotations={"slides_count": "slides"},
        items=ItemSpec(
            model=HeroSlide,
            related_name="slides",
            serializer=HeroSlideSerializer,
            write_serializer=HeroSlideWriteSerializer,
            content_field=None,
        ),
    ),
    SectionType.INTRO: SectionSpec(
        model=IntroSection,
        url_segment="intro",
        list_serializer=IntroSectionListSerializer,
        detail_serializer=IntroSectionDetailSerializer,
        write_serializer=IntroSectionWriteSerializer,
        public_serializer=PublicIntroSectionSerializer,
        public_queryset=lambda qs: qs.select_related("image"),
        admin_queryset=lambda qs: qs.select_related("image"),
        list_annotations={},
    ),
    SectionType.COUNTER: SectionSpec(
        model=CounterSection,
        url_segment="counter",
        list_serializer=CounterSectionListSerializer,
        detail_serializer=CounterSectionDetailSerializer,
        write_serializer=CounterSectionWriteSerializer,
        public_serializer=PublicCounterSectionSerializer,
        public_queryset=lambda qs: qs.prefetch_related(
            Prefetch(
                "items", queryset=CounterSectionItem.objects.select_related("counter")
            )
        ),
        admin_queryset=lambda qs: qs.prefetch_related(
            Prefetch(
                "items", queryset=CounterSectionItem.objects.select_related("counter")
            )
        ),
        list_annotations={"items_count": "items"},
        items=ItemSpec(
            model=CounterSectionItem,
            related_name="items",
            serializer=CounterSectionItemSerializer,
            write_serializer=CounterSectionItemWriteSerializer,
            content_field="counter",
        ),
    ),
    SectionType.FEATURED_PROJECTS: SectionSpec(
        model=FeaturedProjectsSection,
        url_segment="featured-projects",
        list_serializer=FeaturedProjectsSectionListSerializer,
        detail_serializer=FeaturedProjectsSectionDetailSerializer,
        write_serializer=FeaturedProjectsSectionWriteSerializer,
        public_serializer=PublicFeaturedProjectsSectionSerializer,
        public_queryset=lambda qs: qs.prefetch_related(
            Prefetch(
                "items",
                queryset=FeaturedProjectItem.objects.select_related(
                    "project", "project__featured_image"
                ),
            )
        ),
        admin_queryset=lambda qs: qs.prefetch_related(
            Prefetch(
                "items", queryset=FeaturedProjectItem.objects.select_related("project")
            )
        ),
        list_annotations={"items_count": "items"},
        items=ItemSpec(
            model=FeaturedProjectItem,
            related_name="items",
            serializer=FeaturedProjectItemSerializer,
            write_serializer=FeaturedProjectItemWriteSerializer,
            content_field="project",
        ),
    ),
    SectionType.SERVICES: SectionSpec(
        model=ServicesSection,
        url_segment="services",
        list_serializer=ServicesSectionListSerializer,
        detail_serializer=ServicesSectionDetailSerializer,
        write_serializer=ServicesSectionWriteSerializer,
        public_serializer=PublicServicesSectionSerializer,
        public_queryset=lambda qs: qs.prefetch_related(
            Prefetch(
                "items",
                queryset=ServiceSectionItem.objects.select_related(
                    "service", "service__icon", "service__featured_image"
                ),
            )
        ),
        admin_queryset=lambda qs: qs.prefetch_related(
            Prefetch(
                "items", queryset=ServiceSectionItem.objects.select_related("service")
            )
        ),
        list_annotations={"items_count": "items"},
        items=ItemSpec(
            model=ServiceSectionItem,
            related_name="items",
            serializer=ServiceSectionItemSerializer,
            write_serializer=ServiceSectionItemWriteSerializer,
            content_field="service",
        ),
    ),
    SectionType.GALLERY: SectionSpec(
        model=GallerySection,
        url_segment="gallery",
        list_serializer=GallerySectionListSerializer,
        detail_serializer=GallerySectionDetailSerializer,
        write_serializer=GallerySectionWriteSerializer,
        public_serializer=PublicGallerySectionSerializer,
        public_queryset=lambda qs: qs.prefetch_related(
            Prefetch(
                "items", queryset=GallerySectionItem.objects.select_related("media")
            )
        ),
        admin_queryset=lambda qs: qs.prefetch_related(
            Prefetch(
                "items", queryset=GallerySectionItem.objects.select_related("media")
            )
        ),
        list_annotations={"items_count": "items"},
        items=ItemSpec(
            model=GallerySectionItem,
            related_name="items",
            serializer=GallerySectionItemSerializer,
            write_serializer=GallerySectionItemWriteSerializer,
            content_field="media",
        ),
    ),
    SectionType.FAQ: SectionSpec(
        model=FAQSection,
        url_segment="faq",
        list_serializer=FAQSectionListSerializer,
        detail_serializer=FAQSectionDetailSerializer,
        write_serializer=FAQSectionWriteSerializer,
        public_serializer=PublicFAQSectionSerializer,
        public_queryset=lambda qs: qs.prefetch_related(
            Prefetch("items", queryset=FAQSectionItem.objects.select_related("faq"))
        ),
        admin_queryset=lambda qs: qs.prefetch_related(
            Prefetch("items", queryset=FAQSectionItem.objects.select_related("faq"))
        ),
        list_annotations={"items_count": "items"},
        items=ItemSpec(
            model=FAQSectionItem,
            related_name="items",
            serializer=FAQSectionItemSerializer,
            write_serializer=FAQSectionItemWriteSerializer,
            content_field="faq",
        ),
    ),
    SectionType.CTA: SectionSpec(
        model=CTASection,
        url_segment="cta",
        list_serializer=CTASectionListSerializer,
        detail_serializer=CTASectionDetailSerializer,
        write_serializer=CTASectionWriteSerializer,
        public_serializer=PublicCTASectionSerializer,
        public_queryset=lambda qs: qs.select_related("background_media"),
        admin_queryset=lambda qs: qs.select_related("background_media"),
        list_annotations={},
    ),
    SectionType.CONTACT_INFO: SectionSpec(
        model=ContactInfoSection,
        url_segment="contact-info",
        list_serializer=ContactInfoSectionListSerializer,
        detail_serializer=ContactInfoSectionDetailSerializer,
        write_serializer=ContactInfoSectionWriteSerializer,
        public_serializer=PublicContactInfoSectionSerializer,
        public_queryset=_identity,
        admin_queryset=_identity,
        list_annotations={},
    ),
    SectionType.RICH_TEXT: SectionSpec(
        model=RichTextSection,
        url_segment="rich-text",
        list_serializer=RichTextSectionListSerializer,
        detail_serializer=RichTextSectionDetailSerializer,
        write_serializer=RichTextSectionWriteSerializer,
        public_serializer=PublicRichTextSectionSerializer,
        public_queryset=_identity,
        admin_queryset=_identity,
        list_annotations={},
    ),
}

#: url_segment -> section_type, for resolving /admin/sections/<segment>/ routes.
SEGMENT_TO_TYPE = {spec.url_segment: key for key, spec in SECTION_REGISTRY.items()}


def spec_for_type(section_type):
    return SECTION_REGISTRY.get(section_type)


def spec_for_segment(segment):
    section_type = SEGMENT_TO_TYPE.get(segment)
    return SECTION_REGISTRY.get(section_type) if section_type else None
