from django.urls import path

from .views import PageDetailAPIView, PageListCreateAPIView


urlpatterns = [
    path("pages/", PageListCreateAPIView.as_view()),
    path("pages/<int:pk>/", PageDetailAPIView.as_view()),
]
