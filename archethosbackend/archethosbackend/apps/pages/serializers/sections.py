"""
Section serializers.

Two shapes per section that lists master data:

  * the **item** serializer writes the link — a master-data id and nothing else,
    because a section must never be able to edit the record it points at;
  * the **summary** serializer reads it back inlined, so the frontend gets
    `{"items": [{"id": 1, "title": "…"}]}` rather than a list of join-table rows
    it would have to resolve itself (§13).

Ordering is the array index, handled by `SectionSerializer` — no `order` field
crosses the wire.
"""

from rest_framework import serializers

from archethosbackend.apps.api.fields import MediaDetailField, MediaReferenceField
from archethosbackend.apps.content.models import (
    BlogPost,
    Counter,
    GalleryItem,
    Location,
    Project,
    Service,
)

from ..models import (
    AboutLocationItem,
    AboutPresenceSection,
    CTASection,
    ContactDetailsSection,
    ContactFormSection,
    DesignBuildPoint,
    DesignBuildSection,
    FeaturedProjectSection,
    FounderSection,
    GalleryGridItem,
    GalleryGridSection,
    HeroSection,
    HeroSlide,
    HomeGalleryItem,
    HomeGallerySection,
    HomeIntroSection,
    HomeLocationItem,
    HomeLocationsSection,
    HomeProjectItem,
    HomeProjectsSection,
    HomeServiceItem,
    HomeServicesSection,
    JournalFeaturedItem,
    JournalFeaturedSection,
    JournalListSection,
    LocationsListItem,
    LocationsListSection,
    MissionVisionBlock,
    MissionVisionSection,
    PhilosophyPoint,
    PhilosophySection,
    ProcessSection,
    ProcessStep,
    ProjectIndexItem,
    ProjectIndexSection,
    RichTextBlock,
    RichTextSection,
    ServiceIndexItem,
    ServiceIndexSection,
    StatsSection,
    StatsSectionItem,
    StudioStorySection,
    VastuSection,
    VisitingSection,
    WhatHappensSection,
    WhatHappensStep,
)
from .base import SectionSerializer

# ─── Master-data summaries ───────────────────────────────────────────────────
# Deliberately thin. A section lists master data; it does not reproduce it. The
# detail routes are where the full record lives.


class CounterSummary(serializers.ModelSerializer):
    class Meta:
        model = Counter
        fields = ["id", "prefix", "content", "postfix", "subtitle", "description"]


class ServiceSummary(serializers.ModelSerializer):
    image = MediaReferenceField(source="index_image", read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "number", "title", "title_lines", "slug",
            "short_description", "image",
        ]


class ProjectSummary(serializers.ModelSerializer):
    image = MediaReferenceField(source="cover_image", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "title", "slug", "location", "category", "layout",
            "project_year", "short_description", "image",
        ]


class GalleryItemSummary(serializers.ModelSerializer):
    image = MediaReferenceField(read_only=True)
    image_detail = MediaDetailField("image")

    class Meta:
        model = GalleryItem
        fields = ["id", "title", "caption", "category", "image", "image_detail"]


class LocationSummary(serializers.ModelSerializer):
    image = MediaReferenceField(read_only=True)

    class Meta:
        model = Location
        fields = [
            "id", "city", "state", "coordinates", "blurb", "image",
            "address", "phone", "email", "map_url",
        ]


class BlogPostSummary(serializers.ModelSerializer):
    image = MediaReferenceField(source="featured_image", read_only=True)

    class Meta:
        model = BlogPost
        fields = ["id", "title", "slug", "excerpt", "published_at", "image"]


# ─── Item serializers ────────────────────────────────────────────────────────


def _flatten_for_public(self, instance):
    """Admin sees `{"service": 3, "detail": {...}}`; the public sees the record.

    The admin form needs the id it will PATCH back. The frontend needs the
    record itself — a list of join rows it then has to resolve is exactly the
    database detail §13 says not to expose. One serializer, two audiences,
    switched by the context the public view sets.
    """
    data = serializers.ModelSerializer.to_representation(self, instance)
    return data["detail"] if self.context.get("public") else data


def _link(model, field, queryset, summary):
    """Build an item serializer that writes an id and reads the record inlined.

    Every one of these is the same three lines, and writing eleven of them by
    hand would only create eleven chances to spell one differently.
    """

    return type(
        f"{model.__name__}Serializer",
        (serializers.ModelSerializer,),
        {
            field: serializers.PrimaryKeyRelatedField(queryset=queryset),
            "detail": summary(source=field, read_only=True),
            "to_representation": _flatten_for_public,
            "Meta": type("Meta", (), {"model": model, "fields": [field, "detail"]}),
        },
    )


StatsSectionItemSerializer = _link(
    StatsSectionItem, "counter", Counter.objects.all(), CounterSummary
)
HomeServiceItemSerializer = _link(
    HomeServiceItem, "service", Service.objects.all(), ServiceSummary
)
HomeProjectItemSerializer = _link(
    HomeProjectItem, "project", Project.objects.all(), ProjectSummary
)
HomeGalleryItemSerializer = _link(
    HomeGalleryItem, "gallery_item", GalleryItem.objects.all(), GalleryItemSummary
)
HomeLocationItemSerializer = _link(
    HomeLocationItem, "location", Location.objects.all(), LocationSummary
)
AboutLocationItemSerializer = _link(
    AboutLocationItem, "location", Location.objects.all(), LocationSummary
)
ServiceIndexItemSerializer = _link(
    ServiceIndexItem, "service", Service.objects.all(), ServiceSummary
)
ProjectIndexItemSerializer = _link(
    ProjectIndexItem, "project", Project.objects.all(), ProjectSummary
)
GalleryGridItemSerializer = _link(
    GalleryGridItem, "gallery_item", GalleryItem.objects.all(), GalleryItemSummary
)
LocationsListItemSerializer = _link(
    LocationsListItem, "location", Location.objects.all(), LocationSummary
)
JournalFeaturedItemSerializer = _link(
    JournalFeaturedItem, "post", BlogPost.objects.all(), BlogPostSummary
)


class HeroSlideSerializer(serializers.ModelSerializer):
    media = MediaReferenceField()
    media_detail = MediaDetailField("media")

    class Meta:
        model = HeroSlide
        fields = ["eyebrow", "heading", "lead", "media", "media_detail"]


class ProcessStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessStep
        fields = ["number", "title", "body"]


class WhatHappensStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatHappensStep
        fields = ["number", "title", "body"]


class DesignBuildPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesignBuildPoint
        fields = ["title", "body"]


class PhilosophyPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhilosophyPoint
        fields = ["title", "body"]


class RichTextBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = RichTextBlock
        fields = ["title", "body"]


class MissionVisionBlockSerializer(serializers.ModelSerializer):
    media = MediaReferenceField()

    class Meta:
        model = MissionVisionBlock
        fields = ["numeral", "eyebrow", "heading", "body", "points", "media", "side"]


# ─── Shared sections ─────────────────────────────────────────────────────────

HEADING = ["eyebrow", "heading", "lead", "link_label", "link_url"]


class HeroSectionSerializer(SectionSerializer):
    slides = HeroSlideSerializer(many=True, required=False)
    collections = {"slides": "slides"}

    class Meta:
        model = HeroSection
        fields = ["variant", "autoplay_seconds", "slides"]


class CTASectionSerializer(SectionSerializer):
    media = MediaReferenceField()
    media_detail = MediaDetailField("media")

    class Meta:
        model = CTASection
        fields = HEADING + ["body", "media", "media_detail",
                            "secondary_label", "secondary_url"]


class ProcessSectionSerializer(SectionSerializer):
    steps = ProcessStepSerializer(many=True, required=False)
    collections = {"steps": "steps"}

    class Meta:
        model = ProcessSection
        fields = HEADING + ["tone", "steps"]


class RichTextSectionSerializer(SectionSerializer):
    blocks = RichTextBlockSerializer(many=True, required=False)
    collections = {"blocks": "blocks"}

    class Meta:
        model = RichTextSection
        fields = HEADING + ["intro", "updated_on", "blocks"]


# ─── Home ────────────────────────────────────────────────────────────────────


class HomeIntroSectionSerializer(SectionSerializer):
    media = MediaReferenceField()

    class Meta:
        model = HomeIntroSection
        fields = HEADING + ["statement_lines", "body", "media"]


class StatsSectionSerializer(SectionSerializer):
    items = StatsSectionItemSerializer(many=True, required=False)
    collections = {"items": "items"}

    class Meta:
        model = StatsSection
        fields = HEADING + ["tone", "items"]


class FeaturedProjectSectionSerializer(SectionSerializer):
    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), required=False, allow_null=True
    )
    detail = ProjectSummary(source="project", read_only=True)

    class Meta:
        model = FeaturedProjectSection
        fields = HEADING + ["project", "detail"]


class HomeServicesSectionSerializer(SectionSerializer):
    items = HomeServiceItemSerializer(many=True, required=False)
    collections = {"items": "items"}

    class Meta:
        model = HomeServicesSection
        fields = HEADING + ["tone", "items"]


class DesignBuildSectionSerializer(SectionSerializer):
    media = MediaReferenceField()
    points = DesignBuildPointSerializer(many=True, required=False)
    collections = {"points": "points"}

    class Meta:
        model = DesignBuildSection
        fields = HEADING + ["body", "tone", "media", "points"]


class HomeProjectsSectionSerializer(SectionSerializer):
    items = HomeProjectItemSerializer(many=True, required=False)
    collections = {"items": "items"}

    class Meta:
        model = HomeProjectsSection
        fields = HEADING + ["tone", "items"]


class HomeGallerySectionSerializer(SectionSerializer):
    items = HomeGalleryItemSerializer(many=True, required=False)
    collections = {"items": "items"}

    class Meta:
        model = HomeGallerySection
        fields = HEADING + ["autoplay_seconds", "items"]


class VastuSectionSerializer(SectionSerializer):
    media = MediaReferenceField()

    class Meta:
        model = VastuSection
        fields = HEADING + ["statement", "body", "tone", "media"]


class HomeLocationsSectionSerializer(SectionSerializer):
    items = HomeLocationItemSerializer(many=True, required=False)
    collections = {"items": "items"}

    class Meta:
        model = HomeLocationsSection
        fields = HEADING + ["layout", "items"]


# ─── About ───────────────────────────────────────────────────────────────────


class StudioStorySectionSerializer(SectionSerializer):
    media = MediaReferenceField()

    class Meta:
        model = StudioStorySection
        fields = HEADING + ["body", "tone", "media"]


class MissionVisionSectionSerializer(SectionSerializer):
    blocks = MissionVisionBlockSerializer(many=True, required=False)
    collections = {"blocks": "blocks"}

    class Meta:
        model = MissionVisionSection
        fields = ["tone", "blocks"]


class FounderSectionSerializer(SectionSerializer):
    portrait = MediaReferenceField()
    media = MediaReferenceField()
    is_attributed = serializers.BooleanField(read_only=True)

    class Meta:
        model = FounderSection
        fields = HEADING + [
            "message", "name", "role", "credentials", "fallback_attribution",
            "portrait", "media", "is_attributed",
        ]


class PhilosophySectionSerializer(SectionSerializer):
    points = PhilosophyPointSerializer(many=True, required=False)
    collections = {"points": "points"}

    class Meta:
        model = PhilosophySection
        fields = HEADING + ["statement_lines", "tone", "points"]


class AboutPresenceSectionSerializer(SectionSerializer):
    items = AboutLocationItemSerializer(many=True, required=False)
    collections = {"items": "items"}

    class Meta:
        model = AboutPresenceSection
        fields = HEADING + ["layout", "tone", "items"]


# ─── Services / Projects / Gallery / Locations / Journal / Contact ───────────


class ServiceIndexSectionSerializer(SectionSerializer):
    items = ServiceIndexItemSerializer(many=True, required=False)
    collections = {"items": "items"}

    class Meta:
        model = ServiceIndexSection
        fields = HEADING + ["tone", "items"]


class ProjectIndexSectionSerializer(SectionSerializer):
    items = ProjectIndexItemSerializer(many=True, required=False)
    is_curated = serializers.BooleanField(read_only=True)
    collections = {"items": "items"}

    class Meta:
        model = ProjectIndexSection
        fields = HEADING + ["tone", "show_filter", "is_curated", "items"]


class GalleryGridSectionSerializer(SectionSerializer):
    items = GalleryGridItemSerializer(many=True, required=False)
    collections = {"items": "items"}

    class Meta:
        model = GalleryGridSection
        fields = HEADING + ["tone", "show_filter", "items"]


class LocationsListSectionSerializer(SectionSerializer):
    items = LocationsListItemSerializer(many=True, required=False)
    collections = {"items": "items"}

    class Meta:
        model = LocationsListSection
        fields = HEADING + ["layout", "tone", "items"]


class VisitingSectionSerializer(SectionSerializer):
    class Meta:
        model = VisitingSection
        fields = HEADING + ["body", "tone"]


class JournalFeaturedSectionSerializer(SectionSerializer):
    items = JournalFeaturedItemSerializer(many=True, required=False)
    collections = {"items": "items"}

    class Meta:
        model = JournalFeaturedSection
        fields = HEADING + ["tone", "items"]


class JournalListSectionSerializer(SectionSerializer):
    class Meta:
        model = JournalListSection
        fields = HEADING + ["tone", "page_size", "show_categories"]


class ContactFormSectionSerializer(SectionSerializer):
    media = MediaReferenceField()

    class Meta:
        model = ContactFormSection
        fields = HEADING + [
            "tone", "submit_label", "success_message", "consent_note", "media",
        ]


class ContactDetailsSectionSerializer(SectionSerializer):
    class Meta:
        model = ContactDetailsSection
        fields = HEADING + ["body", "no_details_note"]


class WhatHappensSectionSerializer(SectionSerializer):
    steps = WhatHappensStepSerializer(many=True, required=False)
    collections = {"steps": "steps"}

    class Meta:
        model = WhatHappensSection
        fields = HEADING + ["tone", "steps"]
