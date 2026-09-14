from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination

from .models import Blog, BlogCategory, BlogComment, BlogsPage
from .serializers import BlogCategorySerializer, BlogCommentSerializer, BlogSerializer, BlogsPageSerializer


class BlogPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


@extend_schema(tags=["Blogs"])
class BlogListCreateAPIView(generics.ListCreateAPIView):
    queryset = Blog.objects.select_related("author", "category", "featured_image").prefetch_related("comments__author")
    serializer_class = BlogSerializer
    pagination_class = BlogPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["category", "status", "slug"]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


@extend_schema(tags=["Blogs"])
class BlogDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Blog.objects.select_related("author", "category", "featured_image").prefetch_related("comments__author")
    serializer_class = BlogSerializer


@extend_schema(tags=["Blogs page"])
class BlogsPageAPIView(generics.RetrieveUpdateAPIView):
    queryset = BlogsPage.objects.select_related("hero_image")
    serializer_class = BlogsPageSerializer

    def get_object(self):
        page, _ = BlogsPage.objects.get_or_create(pk=BlogsPage.SINGLETON_PK)
        return page


@extend_schema(tags=["Blog categories"])
class CategoryListCreateAPIView(generics.ListCreateAPIView):
    queryset = BlogCategory.objects.all()
    serializer_class = BlogCategorySerializer


@extend_schema(tags=["Blog categories"])
class CategoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BlogCategory.objects.all()
    serializer_class = BlogCategorySerializer


@extend_schema(tags=["Blog comments"])
class BlogCommentListCreateAPIView(generics.ListCreateAPIView):
    queryset = BlogComment.objects.none()
    serializer_class = BlogCommentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["author"]

    def get_queryset(self):
        return BlogComment.objects.filter(blog_id=self.kwargs["blog_id"]).select_related("author")

    def perform_create(self, serializer):
        serializer.save(blog_id=self.kwargs["blog_id"], author=self.request.user)


@extend_schema(tags=["Blog comments"])
class BlogCommentDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BlogCommentSerializer

    def get_queryset(self):
        return BlogComment.objects.filter(blog_id=self.kwargs["blog_id"]).select_related("author")
