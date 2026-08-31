"""Routes for /api/v1/public/ — unauthenticated, read-only, live content only."""

from django.urls import path

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
