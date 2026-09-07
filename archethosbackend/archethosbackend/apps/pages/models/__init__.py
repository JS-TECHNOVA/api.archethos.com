"""
Pages and their sections.

    Page ──1:1──> Section ──1:N──> Item ──N:1──> Master data

Nine pages, each a singleton, each declaring its sections as named fields in
render order. There is no `Page` table, no `PageSection` join and no section
registry: the structure of this site is fixed and lives in code, while the CMS
owns the words and the pictures.

    HomePage.hero          → HeroSection
    HomePage.services      → HomeServicesSection → HomeServiceItem → content.Service

`ORDERED_PAGES` maps the public route to its model and is the one place that
knows the site has nine pages. Adding a page means adding a model, a serializer
and an entry here.
"""

from .about import (
    AboutLocationItem,
    AboutPage,
    AboutPresenceSection,
    FounderSection,
    MissionVisionBlock,
    MissionVisionSection,
    PhilosophyPoint,
    PhilosophySection,
    StudioStorySection,
)
from .base import SectionedPage
from .company import Company
from .contact import (
    ContactDetailsSection,
    ContactFormSection,
    ContactPage,
    WhatHappensSection,
    WhatHappensStep,
)
from .gallery import GalleryGridItem, GalleryGridSection, GalleryPage
from .home import (
    DesignBuildPoint,
    DesignBuildSection,
    FeaturedProjectSection,
    HomeGalleryItem,
    HomeGallerySection,
    HomeIntroSection,
    HomeLocationItem,
    HomeLocationsSection,
    HomePage,
    HomeProjectItem,
    HomeProjectsSection,
    HomeServiceItem,
    HomeServicesSection,
    StatsSection,
    StatsSectionItem,
    VastuSection,
)
from .journal import (
    JournalFeaturedItem,
    JournalFeaturedSection,
    JournalListSection,
    JournalPage,
)
from .legal import PrivacyPage, TermsPage
from .locations import (
    LocationsListItem,
    LocationsListSection,
    LocationsPage,
    VisitingSection,
)
from .projects import ProjectIndexItem, ProjectIndexSection, ProjectsPage
from .services import ServiceIndexItem, ServiceIndexSection, ServicesPage
from .shared import (
    CTASection,
    HeroSection,
    HeroSlide,
    ProcessSection,
    ProcessStep,
    RichTextBlock,
    RichTextSection,
    SectionHeading,
    section,
)

#: Public route → page model, in site navigation order.
ORDERED_PAGES = {
    "home": HomePage,
    "about": AboutPage,
    "services": ServicesPage,
    "projects": ProjectsPage,
    "gallery": GalleryPage,
    "journal": JournalPage,
    "locations": LocationsPage,
    "contact": ContactPage,
    "legal/privacy": PrivacyPage,
    "legal/terms": TermsPage,
}

__all__ = [
    "ORDERED_PAGES",
    # pages
    "AboutPage",
    "ContactPage",
    "GalleryPage",
    "HomePage",
    "JournalPage",
    "LocationsPage",
    "PrivacyPage",
    "ProjectsPage",
    "ServicesPage",
    "TermsPage",
    "SectionedPage",
    # site-wide
    "Company",
    # shared sections
    "CTASection",
    "HeroSection",
    "HeroSlide",
    "ProcessSection",
    "ProcessStep",
    "RichTextBlock",
    "RichTextSection",
    "SectionHeading",
    "section",
    # home
    "DesignBuildPoint",
    "DesignBuildSection",
    "FeaturedProjectSection",
    "HomeGalleryItem",
    "HomeGallerySection",
    "HomeIntroSection",
    "HomeLocationItem",
    "HomeLocationsSection",
    "HomeProjectItem",
    "HomeProjectsSection",
    "HomeServiceItem",
    "HomeServicesSection",
    "StatsSection",
    "StatsSectionItem",
    "VastuSection",
    # about
    "AboutLocationItem",
    "AboutPresenceSection",
    "FounderSection",
    "MissionVisionBlock",
    "MissionVisionSection",
    "PhilosophyPoint",
    "PhilosophySection",
    "StudioStorySection",
    # services
    "ServiceIndexItem",
    "ServiceIndexSection",
    # projects
    "ProjectIndexItem",
    "ProjectIndexSection",
    # gallery
    "GalleryGridItem",
    "GalleryGridSection",
    # journal
    "JournalFeaturedItem",
    "JournalFeaturedSection",
    "JournalListSection",
    # locations
    "LocationsListItem",
    "LocationsListSection",
    "VisitingSection",
    # contact
    "ContactDetailsSection",
    "ContactFormSection",
    "WhatHappensSection",
    "WhatHappensStep",
]
