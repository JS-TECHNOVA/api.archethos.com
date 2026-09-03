"""Routes for /api/v1/public/ — unauthenticated, read-only, live content only."""

from django.urls import path

from archethosbackend.apps.content.search_views import PublicSearchAPIView
from archethosbackend.apps.enquiries.views import EnquirySubmitAPIView

from archethosbackend.apps.pages.public_views import (
    PublicCompanyAPIView,
    PublicPageAPIView,
    PublicPageIndexAPIView,
)

from archethosbackend.apps.content.public_views import (
    PublicBlogCategoryListAPIView,
    PublicBlogPostDetailAPIView,
    PublicBlogPostListAPIView,
    PublicCounterListAPIView,
    PublicFAQListAPIView,
    PublicGalleryItemListAPIView,
    PublicLocationListAPIView,
    PublicProjectDetailAPIView,
    PublicProjectListAPIView,
    PublicServiceDetailAPIView,
    PublicServiceListAPIView,
)

urlpatterns = [
    # One request renders a whole route. <path:route> not <slug:route> — page
    # routes mirror the frontend's, which nest ("legal/privacy"), and the slug
    # converter does not match "/".
    path("pages/", PublicPageIndexAPIView.as_view(), name="page-index"),
    path("pages/<path:route>/", PublicPageAPIView.as_view(), name="page-detail"),
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
    path("gallery/", PublicGalleryItemListAPIView.as_view(), name="gallery-list"),
    path("locations/", PublicLocationListAPIView.as_view(), name="location-list"),
    path("search/", PublicSearchAPIView.as_view(), name="search"),
    # The only place an anonymous visitor writes to the database.
    path("enquiries/", EnquirySubmitAPIView.as_view(), name="enquiry-submit"),
]
