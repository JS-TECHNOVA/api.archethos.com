"""
Routes for /api/v1/admin/.

Every route is written out explicitly — no routers anywhere in this project
(DEVELOPMENT_PLAN.md §2.8).
"""

from django.urls import path

from archethosbackend.apps.content.admin_views import (
    BlogCategoryDetailAPIView,
    BlogCategoryListCreateAPIView,
    BlogPostDetailAPIView,
    BlogPostListCreateAPIView,
    BlogPostPublishAPIView,
    BlogPostUnpublishAPIView,
    CounterDetailAPIView,
    CounterListCreateAPIView,
    FAQDetailAPIView,
    FAQListCreateAPIView,
    ProjectDetailAPIView,
    ProjectGalleryItemAPIView,
    ProjectGalleryListCreateAPIView,
    ProjectGalleryReorderAPIView,
    ProjectListCreateAPIView,
    ServiceDetailAPIView,
    ServiceListCreateAPIView,
)

from archethosbackend.apps.pages.admin_views import (
    CompanyAPIView,
    PageDetailAPIView,
    PageListCreateAPIView,
    PageSectionDetailAPIView,
    PageSectionListCreateAPIView,
    PageSectionReorderAPIView,
)

from archethosbackend.apps.sections.views import (
    SectionBrowseAPIView,
    SectionDetailAPIView,
    SectionItemDetailAPIView,
    SectionItemListCreateAPIView,
    SectionItemReorderAPIView,
    SectionListCreateAPIView,
    SectionTypeCatalogueAPIView,
    SectionUsageAPIView,
)

from archethosbackend.apps.media_library.views import (
    MediaDetailAPIView,
    MediaDuplicateCheckAPIView,
    MediaListAPIView,
    MediaUploadAPIView,
    MediaUsageAPIView,
    MediaYouTubeAPIView,
)

from archethosbackend.apps.accounts.admin_views import (
    GroupDetailAPIView,
    GroupListCreateAPIView,
    PermissionListAPIView,
    UserActivateAPIView,
    UserDeactivateAPIView,
    UserDetailAPIView,
    UserListCreateAPIView,
    UserSetPasswordAPIView,
)

urlpatterns = [
    # Users
    path("users/", UserListCreateAPIView.as_view(), name="user-list"),
    path("users/<int:pk>/", UserDetailAPIView.as_view(), name="user-detail"),
    path(
        "users/<int:pk>/deactivate/",
        UserDeactivateAPIView.as_view(),
        name="user-deactivate",
    ),
    path("users/<int:pk>/activate/", UserActivateAPIView.as_view(), name="user-activate"),
    path(
        "users/<int:pk>/set-password/",
        UserSetPasswordAPIView.as_view(),
        name="user-set-password",
    ),
    # Groups
    path("groups/", GroupListCreateAPIView.as_view(), name="group-list"),
    path("groups/<int:pk>/", GroupDetailAPIView.as_view(), name="group-detail"),
    # Permissions (read-only catalogue)
    path("permissions/", PermissionListAPIView.as_view(), name="permission-list"),
    # Media library.  Upload and YouTube are separate endpoints rather than modes
    # of one create view: they take different payloads (multipart vs JSON) and
    # share nothing but the table they write to.
    path("media/", MediaListAPIView.as_view(), name="media-list"),
    path("media/upload/", MediaUploadAPIView.as_view(), name="media-upload"),
    path("media/youtube/", MediaYouTubeAPIView.as_view(), name="media-youtube"),
    path(
        "media/check-duplicate/",
        MediaDuplicateCheckAPIView.as_view(),
        name="media-check-duplicate",
    ),
    path("media/<int:pk>/", MediaDetailAPIView.as_view(), name="media-detail"),
    path("media/<int:pk>/usage/", MediaUsageAPIView.as_view(), name="media-usage"),
    # Services
    path("services/", ServiceListCreateAPIView.as_view(), name="service-list"),
    path("services/<int:pk>/", ServiceDetailAPIView.as_view(), name="service-detail"),
    # Projects, with their own gallery
    path("projects/", ProjectListCreateAPIView.as_view(), name="project-list"),
    path("projects/<int:pk>/", ProjectDetailAPIView.as_view(), name="project-detail"),
    path(
        "projects/<int:pk>/gallery/",
        ProjectGalleryListCreateAPIView.as_view(),
        name="project-gallery-list",
    ),
    path(
        "projects/<int:pk>/gallery/reorder/",
        ProjectGalleryReorderAPIView.as_view(),
        name="project-gallery-reorder",
    ),
    path(
        "projects/<int:pk>/gallery/<int:item_id>/",
        ProjectGalleryItemAPIView.as_view(),
        name="project-gallery-item",
    ),
    # Blog
    path("blogs/", BlogPostListCreateAPIView.as_view(), name="blog-list"),
    path("blogs/<int:pk>/", BlogPostDetailAPIView.as_view(), name="blog-detail"),
    path(
        "blogs/<int:pk>/publish/",
        BlogPostPublishAPIView.as_view(),
        name="blog-publish",
    ),
    path(
        "blogs/<int:pk>/unpublish/",
        BlogPostUnpublishAPIView.as_view(),
        name="blog-unpublish",
    ),
    path(
        "blog-categories/",
        BlogCategoryListCreateAPIView.as_view(),
        name="blog-category-list",
    ),
    path(
        "blog-categories/<int:pk>/",
        BlogCategoryDetailAPIView.as_view(),
        name="blog-category-detail",
    ),
    # FAQs and counters
    path("faqs/", FAQListCreateAPIView.as_view(), name="faq-list"),
    path("faqs/<int:pk>/", FAQDetailAPIView.as_view(), name="faq-detail"),
    path("counters/", CounterListCreateAPIView.as_view(), name="counter-list"),
    path("counters/<int:pk>/", CounterDetailAPIView.as_view(), name="counter-detail"),
    # ── Sections ──────────────────────────────────────────────────────────────
    # One set of routes serves every section type. <segment> resolves through
    # SECTION_REGISTRY, so a new section type needs no new URL entry.
    path("sections/", SectionBrowseAPIView.as_view(), name="section-browse"),
    path(
        "sections/types/",
        SectionTypeCatalogueAPIView.as_view(),
        name="section-type-list",
    ),
    path(
        "sections/<slug:segment>/",
        SectionListCreateAPIView.as_view(),
        name="section-list",
    ),
    path(
        "sections/<slug:segment>/<int:pk>/",
        SectionDetailAPIView.as_view(),
        name="section-detail",
    ),
    path(
        "sections/<slug:segment>/<int:pk>/usage/",
        SectionUsageAPIView.as_view(),
        name="section-usage",
    ),
    path(
        "sections/<slug:segment>/<int:pk>/items/",
        SectionItemListCreateAPIView.as_view(),
        name="section-item-list",
    ),
    path(
        "sections/<slug:segment>/<int:pk>/items/reorder/",
        SectionItemReorderAPIView.as_view(),
        name="section-item-reorder",
    ),
    path(
        "sections/<slug:segment>/<int:pk>/items/<int:item_id>/",
        SectionItemDetailAPIView.as_view(),
        name="section-item-detail",
    ),
    # ── Pages and composition ─────────────────────────────────────────────────
    path("pages/", PageListCreateAPIView.as_view(), name="page-list"),
    path("pages/<int:pk>/", PageDetailAPIView.as_view(), name="page-detail"),
    path(
        "pages/<int:pk>/sections/",
        PageSectionListCreateAPIView.as_view(),
        name="page-section-list",
    ),
    path(
        "pages/<int:pk>/sections/reorder/",
        PageSectionReorderAPIView.as_view(),
        name="page-section-reorder",
    ),
    path(
        "pages/<int:pk>/sections/<int:page_section_id>/",
        PageSectionDetailAPIView.as_view(),
        name="page-section-detail",
    ),
    # Site-wide settings (singleton: no id, no list)
    path("company/", CompanyAPIView.as_view(), name="company-detail"),
]
