"""Routes for /api/v1/public/ — unauthenticated, read-only, live content only."""

from django.urls import path

from archethosbackend.apps.pages.public_views import (
    PageAggregateAPIView,
    PublicCompanyAPIView,
)

from archethosbackend.apps.content.public_views import (
    PublicBlogCategoryListAPIView,
    PublicBlogPostDetailAPIView,
    PublicBlogPostListAPIView,
    PublicCounterListAPIView,
    PublicFAQListAPIView,
    PublicProjectDetailAPIView,
    PublicProjectListAPIView,
    PublicServiceDetailAPIView,
    PublicServiceListAPIView,
)

urlpatterns = [
    # The aggregate endpoint: one request renders a whole page.
    # <path:slug> not <slug:slug> - page slugs mirror frontend routes, which
    # nest ("legal/privacy"), and the slug converter does not match "/".
    path("pages/<path:slug>/", PageAggregateAPIView.as_view(), name="page-aggregate"),
    path("company/", PublicCompanyAPIView.as_view(), name="company"),
    path("projects/", PublicProjectListAPIView.as_view(), name="project-list"),
    path(
        "projects/<slug:slug>/",
        PublicProjectDetailAPIView.as_view(),
        name="project-detail",
    ),
    path("services/", PublicServiceListAPIView.as_view(), name="service-list"),
    path(
        "services/<slug:slug>/",
        PublicServiceDetailAPIView.as_view(),
        name="service-detail",
    ),
    # The frontend route is /journal/..., but the resource keeps its model name.
    path("blogs/", PublicBlogPostListAPIView.as_view(), name="blog-list"),
    path("blogs/<slug:slug>/", PublicBlogPostDetailAPIView.as_view(), name="blog-detail"),
    path(
        "blog-categories/",
        PublicBlogCategoryListAPIView.as_view(),
        name="blog-category-list",
    ),
    path("faqs/", PublicFAQListAPIView.as_view(), name="faq-list"),
    path("counters/", PublicCounterListAPIView.as_view(), name="counter-list"),
]
