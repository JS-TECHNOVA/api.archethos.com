from django.urls import path

from .views import MediaDetailAPIView, MediaListCreateAPIView

urlpatterns = [
    path("", MediaListCreateAPIView.as_view()),
    path("<int:pk>/", MediaDetailAPIView.as_view()),
]
