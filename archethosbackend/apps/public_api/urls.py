from django.urls import path

from .views import (
    PublicBlogListAPIView,
    PublicBlogDetailAPIView,
    PublicBlogsPageAPIView,
    PublicGalleryItemListAPIView,
    PublicGalleryPageAPIView,
    PublicProjectDetailAPIView,
    PublicProjectListAPIView,
    PublicProjectPageAPIView,
    PublicServiceDetailAPIView,
    PublicServicesPageAPIView,
    PublicHomePageAPIView,
    PublicAboutPageAPIView,
    PublicCompanyAPIView,
    PublicContactPageAPIView,
    PublicPageDetailAPIView,
    PublicFAQListAPIView,
)

urlpatterns = [
    path("faqs/", PublicFAQListAPIView.as_view()),

    path("blog/page/", PublicBlogsPageAPIView.as_view()),
    path("blogs/", PublicBlogListAPIView.as_view()),
    path("blogs/<slug:slug>/", PublicBlogDetailAPIView.as_view()),

    path("gallery/page/", PublicGalleryPageAPIView.as_view()),
    path("gallery/", PublicGalleryItemListAPIView.as_view()),

    path("project/page/", PublicProjectPageAPIView.as_view()),
    path("projects/", PublicProjectListAPIView.as_view()),
    path("project/<slug:slug>/", PublicProjectDetailAPIView.as_view()),

    path("services/page/", PublicServicesPageAPIView.as_view()),
    path("service/<slug:slug>/", PublicServiceDetailAPIView.as_view()),

    path("home/page/", PublicHomePageAPIView.as_view()),

    path("about/page/", PublicAboutPageAPIView.as_view()),

    path("company/", PublicCompanyAPIView.as_view()),

    path("contact/page/", PublicContactPageAPIView.as_view()),
    path("page/custom/<slug:slug>/", PublicPageDetailAPIView.as_view()),
]
