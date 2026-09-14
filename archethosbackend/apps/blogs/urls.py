from django.urls import path

from .views import (
    BlogCommentDetailAPIView,
    BlogCommentListCreateAPIView,
    BlogDetailAPIView,
    BlogListCreateAPIView,
    BlogsPageAPIView,
    CategoryDetailAPIView,
    CategoryListCreateAPIView,
)


urlpatterns = [
    path("blogs/page/", BlogsPageAPIView.as_view()),
    path("blogs/", BlogListCreateAPIView.as_view()),
    path("blogs/<int:pk>/", BlogDetailAPIView.as_view()),
    path("blogs/<int:blog_id>/comments/", BlogCommentListCreateAPIView.as_view()),
    path("blogs/<int:blog_id>/comments/<int:pk>/", BlogCommentDetailAPIView.as_view()),
    path("categories/", CategoryListCreateAPIView.as_view()),
    path("categories/<int:pk>/", CategoryDetailAPIView.as_view()),
]
