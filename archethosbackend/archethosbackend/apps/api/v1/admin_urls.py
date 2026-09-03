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
    GalleryItemDetailAPIView,
    GalleryItemListCreateAPIView,
    LocationDetailAPIView,
    LocationListCreateAPIView,
    ProjectDetailAPIView,
    ProjectGalleryItemAPIView,
    ProjectGalleryListCreateAPIView,
    ProjectGalleryReorderAPIView,
    ProjectListCreateAPIView,
    ServiceDetailAPIView,
    ServiceListCreateAPIView,
)

from archethosbackend.apps.api.dashboard_views import (
    AdminCountsAPIView,
    DashboardStatsAPIView,
)

from archethosbackend.apps.enquiries.views import (
    EnquiryDetailAPIView,
    EnquiryListAPIView,
    EnquiryUnreadCountAPIView,
)

from archethosbackend.apps.pages.admin_views import (
    CompanyAPIView,
    PageDetailAPIView,
    PageListAPIView,
)

from archethosbackend.apps.media_library.views import (
    MediaDetailAPIView,
    MediaDuplicateCheckAPIView,
    MediaListAPIView,
    MediaReplaceAPIView,
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
    # Admin chrome: sidebar badges and the dashboard figures.
    path("counts/", AdminCountsAPIView.as_view(), name="counts"),
    path("dashboard/stats/", DashboardStatsAPIView.as_view(), name="dashboard-stats"),
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
    # Swaps the file in place; the id, path and descriptive fields survive.
    path(
        "media/<int:pk>/replace/",
        MediaReplaceAPIView.as_view(),
        name="media-replace",
    ),
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
    # ── Pages ────────────────────────────────────────────────────────────────
    # Ten fixed pages, addressed by their public route. No create, no delete:
    # the site's structure is code, and `ensure_pages` makes the rows.
    # <path:route> not <slug:route> — "legal/privacy" contains a slash.
    path("pages/", PageListAPIView.as_view(), name="page-list"),
    path("pages/<path:route>/", PageDetailAPIView.as_view(), name="page-detail"),
    # Master data added by the page refactor: both were hardcoded in the
    # frontend and are now edited once and referenced from several pages.
    path("gallery/", GalleryItemListCreateAPIView.as_view(), name="gallery-list"),
    path(
        "gallery/<int:pk>/",
        GalleryItemDetailAPIView.as_view(),
        name="gallery-detail",
    ),
    path("locations/", LocationListCreateAPIView.as_view(), name="location-list"),
    path(
        "locations/<int:pk>/",
        LocationDetailAPIView.as_view(),
        name="location-detail",
    ),
    path("company/", CompanyAPIView.as_view(), name="company-detail"),
    # Enquiries are read-only: they arrive from the public form.
    path("enquiries/", EnquiryListAPIView.as_view(), name="enquiry-list"),
    path(
        "enquiries/unread-count/",
        EnquiryUnreadCountAPIView.as_view(),
        name="enquiry-unread-count",
    ),
    path("enquiries/<int:pk>/", EnquiryDetailAPIView.as_view(), name="enquiry-detail"),
]
