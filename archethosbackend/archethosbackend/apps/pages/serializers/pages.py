"""
Page serializers — one per page, listing its sections in render order.

Read one of these top to bottom and it matches the model, which matches the
site. That correspondence is the whole point: there is no registry to consult
and no lookup table that could disagree with the component tree.
"""

from rest_framework import serializers

from archethosbackend.apps.api.fields import MediaReferenceField

from ..models import (
    AboutPage,
    ContactPage,
    GalleryPage,
    HomePage,
    JournalPage,
    LocationsPage,
    PrivacyPage,
    ProjectsPage,
    ServicesPage,
    TermsPage,
)
from .base import PageSerializer
from .sections import (
    AboutPresenceSectionSerializer,
    CTASectionSerializer,
    ContactDetailsSectionSerializer,
    ContactFormSectionSerializer,
    DesignBuildSectionSerializer,
    FeaturedProjectSectionSerializer,
    FounderSectionSerializer,
    GalleryGridSectionSerializer,
    HeroSectionSerializer,
    HomeGallerySectionSerializer,
    HomeIntroSectionSerializer,
    HomeLocationsSectionSerializer,
    HomeProjectsSectionSerializer,
    HomeServicesSectionSerializer,
    JournalFeaturedSectionSerializer,
    JournalListSectionSerializer,
    LocationsListSectionSerializer,
    MissionVisionSectionSerializer,
    PhilosophySectionSerializer,
    ProcessSectionSerializer,
    ProjectIndexSectionSerializer,
    RichTextSectionSerializer,
    ServiceIndexSectionSerializer,
    StatsSectionSerializer,
    StudioStorySectionSerializer,
    VastuSectionSerializer,
    VisitingSectionSerializer,
    WhatHappensSectionSerializer,
)

#: Every page carries the same SEO block, so it is named once.
SEO = [
    "meta_title",
    "meta_description",
    "meta_keywords",
    "og_title",
    "og_description",
    "og_image",
    "canonical_url",
    "robots_index",
    "robots_follow",
]

META = ["id", "is_published", "missing_sections", "updated_at"]


class BasePageFields(PageSerializer):
    """The publish state and SEO block shared by all ten pages."""

    og_image = MediaReferenceField()
    #: Which required sections are still empty — what the admin banner reads.
    missing_sections = serializers.SerializerMethodField()

    #: Keys the admin needs and the website has no business seeing.
    ADMIN_ONLY = ("id", "is_published", "missing_sections", "updated_at")

    def get_missing_sections(self, obj) -> list[str]:
        return obj.missing_sections()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context.get("public"):
            for key in self.ADMIN_ONLY:
                data.pop(key, None)
        return data


class HomePageSerializer(BasePageFields):
    hero = HeroSectionSerializer(required=False)
    intro = HomeIntroSectionSerializer(required=False)
    stats = StatsSectionSerializer(required=False)
    featured_project = FeaturedProjectSectionSerializer(required=False)
    services = HomeServicesSectionSerializer(required=False)
    design_build = DesignBuildSectionSerializer(required=False)
    projects = HomeProjectsSectionSerializer(required=False)
    gallery = HomeGallerySectionSerializer(required=False)
    vastu = VastuSectionSerializer(required=False)
    locations = HomeLocationsSectionSerializer(required=False)
    cta = CTASectionSerializer(required=False)

    class Meta:
        model = HomePage
        fields = META + SEO + [
            "hero", "intro", "stats", "featured_project", "services",
            "design_build", "projects", "gallery", "vastu", "locations", "cta",
        ]


class AboutPageSerializer(BasePageFields):
    hero = HeroSectionSerializer(required=False)
    story = StudioStorySectionSerializer(required=False)
    mission_vision = MissionVisionSectionSerializer(required=False)
    founder = FounderSectionSerializer(required=False)
    process = ProcessSectionSerializer(required=False)
    philosophy = PhilosophySectionSerializer(required=False)
    presence = AboutPresenceSectionSerializer(required=False)
    cta = CTASectionSerializer(required=False)

    class Meta:
        model = AboutPage
        fields = META + SEO + [
            "hero", "story", "mission_vision", "founder", "process",
            "philosophy", "presence", "cta",
        ]


class ServicesPageSerializer(BasePageFields):
    hero = HeroSectionSerializer(required=False)
    index = ServiceIndexSectionSerializer(required=False)
    process = ProcessSectionSerializer(required=False)
    cta = CTASectionSerializer(required=False)

    class Meta:
        model = ServicesPage
        fields = META + SEO + ["hero", "index", "process", "cta"]


class ProjectsPageSerializer(BasePageFields):
    hero = HeroSectionSerializer(required=False)
    index = ProjectIndexSectionSerializer(required=False)
    cta = CTASectionSerializer(required=False)

    class Meta:
        model = ProjectsPage
        fields = META + SEO + ["hero", "index", "cta"]


class GalleryPageSerializer(BasePageFields):
    hero = HeroSectionSerializer(required=False)
    grid = GalleryGridSectionSerializer(required=False)
    cta = CTASectionSerializer(required=False)

    class Meta:
        model = GalleryPage
        fields = META + SEO + ["hero", "grid", "cta"]


class JournalPageSerializer(BasePageFields):
    hero = HeroSectionSerializer(required=False)
    featured = JournalFeaturedSectionSerializer(required=False)
    list = JournalListSectionSerializer(required=False)
    cta = CTASectionSerializer(required=False)

    class Meta:
        model = JournalPage
        fields = META + SEO + ["hero", "featured", "list", "cta"]


class LocationsPageSerializer(BasePageFields):
    hero = HeroSectionSerializer(required=False)
    locations = LocationsListSectionSerializer(required=False)
    visiting = VisitingSectionSerializer(required=False)
    cta = CTASectionSerializer(required=False)

    class Meta:
        model = LocationsPage
        fields = META + SEO + ["hero", "locations", "visiting", "cta"]


class ContactPageSerializer(BasePageFields):
    hero = HeroSectionSerializer(required=False)
    form = ContactFormSectionSerializer(required=False)
    details = ContactDetailsSectionSerializer(required=False)
    what_happens = WhatHappensSectionSerializer(required=False)
    cta = CTASectionSerializer(required=False)

    class Meta:
        model = ContactPage
        fields = META + SEO + ["hero", "form", "details", "what_happens", "cta"]


class PrivacyPageSerializer(BasePageFields):
    body = RichTextSectionSerializer(required=False)

    class Meta:
        model = PrivacyPage
        fields = META + SEO + ["body"]


class TermsPageSerializer(BasePageFields):
    body = RichTextSectionSerializer(required=False)

    class Meta:
        model = TermsPage
        fields = META + SEO + ["body"]


#: Route → serializer. Paired with `ORDERED_PAGES`; the view checks they agree.
PAGE_SERIALIZERS = {
    "home": HomePageSerializer,
    "about": AboutPageSerializer,
    "services": ServicesPageSerializer,
    "projects": ProjectsPageSerializer,
    "gallery": GalleryPageSerializer,
    "journal": JournalPageSerializer,
    "locations": LocationsPageSerializer,
    "contact": ContactPageSerializer,
    "legal/privacy": PrivacyPageSerializer,
    "legal/terms": TermsPageSerializer,
}
