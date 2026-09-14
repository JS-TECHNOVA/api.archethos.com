from django.urls import path

from .views import (
    FAQDetailAPIView, FAQListCreateAPIView,
    GalleryAPIView, GalleryCategoryDetailAPIView, GalleryCategoryListCreateAPIView,
    GalleryItemDetailAPIView, GalleryItemListCreateAPIView,
)

urlpatterns = [
    path("faqs/", FAQListCreateAPIView.as_view()),
    path("faqs/<int:pk>/", FAQDetailAPIView.as_view()),
    path("gallery/", GalleryAPIView.as_view()),
    path("gallery/categories/", GalleryCategoryListCreateAPIView.as_view()),
    path("gallery/categories/<int:pk>/", GalleryCategoryDetailAPIView.as_view()),
    path("gallery/items/", GalleryItemListCreateAPIView.as_view()),
    path("gallery/items/<int:pk>/", GalleryItemDetailAPIView.as_view()),
]
