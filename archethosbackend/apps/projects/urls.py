from django.urls import path

from .views import (
    ProjectCategoryDetailAPIView, ProjectCategoryListCreateAPIView, ProjectDetailAPIView,
    ProjectDetailedStageDetailAPIView, ProjectDetailedStageListCreateAPIView,
    ProjectGalleryDetailAPIView, ProjectGalleryListCreateAPIView, ProjectListCreateAPIView,
    ProjectPageAPIView,
)


urlpatterns = [
    path("projects/page/", ProjectPageAPIView.as_view()),
    path("projects/", ProjectListCreateAPIView.as_view()),
    path("projects/<int:pk>/", ProjectDetailAPIView.as_view()),
    path("project-categories/", ProjectCategoryListCreateAPIView.as_view()),
    path("project-categories/<int:pk>/", ProjectCategoryDetailAPIView.as_view()),
    path("projects/<int:project_id>/gallery/", ProjectGalleryListCreateAPIView.as_view()),
    path("projects/<int:project_id>/gallery/<int:pk>/", ProjectGalleryDetailAPIView.as_view()),
    path("projects/<int:project_id>/stages/", ProjectDetailedStageListCreateAPIView.as_view()),
    path("projects/<int:project_id>/stages/<int:pk>/", ProjectDetailedStageDetailAPIView.as_view()),
]
