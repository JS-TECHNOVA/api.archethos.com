"""
Public read-only content API.

Every queryset here starts from `.live()`. Draft, scheduled and archived content
must never be reachable, so the filtering happens in `get_queryset()` rather than
being something a serializer could forget.

Lookup is by slug, not id: public URLs are /projects/<slug>, and exposing
sequential ids invites enumeration of unpublished neighbours.
"""

import django_filters
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny

from ..content.models import FAQ, BlogCategory, BlogPost, Counter, Project, ProjectGalleryItem, Service
from .serializers import (
    PublicBlogCategorySerializer,
    PublicBlogPostDetailSerializer,
    PublicBlogPostSerializer,
    PublicCounterSerializer,
    PublicFAQSerializer,
    PublicProjectDetailSerializer,
    PublicProjectSerializer,
    PublicServiceDetailSerializer,
    PublicServiceSerializer,
)


class PublicAPIView:
    """Shared defaults: no auth, read-only, live content only."""

    authentication_classes = []
    permission_classes = [AllowAny]
    lookup_field = "slug"


# ─── Projects ────────────────────────────────────────────────────────────────


class PublicProjectFilterSet(django_filters.FilterSet):
    featured = django_filters.BooleanFilter(field_name="is_featured")
    service = django_filters.CharFilter(field_name="services__slug")
    year = django_filters.NumberFilter(field_name="project_year")

    class Meta:
        model = Project
        fields = ["featured", "service", "year", "project_status"]


class PublicProjectListAPIView(PublicAPIView, generics.ListAPIView):
    ordering = ["-project_year", "-published_at", "-id"]
    serializer_class = PublicProjectSerializer
    filterset_class = PublicProjectFilterSet
    search_fields = ["title", "short_description", "location"]
    ordering_fields = ["project_year", "published_at", "title"]

    def get_queryset(self):
        return (
            Project.objects.live()
            .select_related("featured_image")
            .distinct()
        )

    @extend_schema(tags=["public"], summary="List published projects")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PublicProjectDetailAPIView(PublicAPIView, generics.RetrieveAPIView):
    serializer_class = PublicProjectDetailSerializer

    def get_queryset(self):
        return (
            Project.objects.live()
            .select_related("featured_image", "og_image")
            .prefetch_related(
                "services",
                Prefetch(
                    "gallery_items",
                    queryset=ProjectGalleryItem.objects.select_related("media"),
                ),
            )
        )

    @extend_schema(tags=["public"], summary="Retrieve a published project by slug")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


# ─── Services ────────────────────────────────────────────────────────────────


class PublicServiceListAPIView(PublicAPIView, generics.ListAPIView):
    ordering = ["order", "title", "id"]
    serializer_class = PublicServiceSerializer
    search_fields = ["title", "short_description"]
    ordering_fields = ["order", "title", "published_at"]

    def get_queryset(self):
        return Service.objects.live().select_related("featured_image", "icon")

    @extend_schema(tags=["public"], summary="List published services")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PublicServiceDetailAPIView(PublicAPIView, generics.RetrieveAPIView):
    serializer_class = PublicServiceDetailSerializer

    def get_queryset(self):
        return Service.objects.live().select_related(
            "featured_image", "icon", "og_image"
        )

    @extend_schema(tags=["public"], summary="Retrieve a published service by slug")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


# ─── Blog / journal ──────────────────────────────────────────────────────────


class PublicBlogFilterSet(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category__slug")

    class Meta:
        model = BlogPost
        fields = ["category"]


class PublicBlogPostListAPIView(PublicAPIView, generics.ListAPIView):
    ordering = ["-published_at", "-id"]
    serializer_class = PublicBlogPostSerializer
    filterset_class = PublicBlogFilterSet
    search_fields = ["title", "excerpt", "content"]
    ordering_fields = ["published_at", "title", "reading_time"]

    def get_queryset(self):
        return BlogPost.objects.live().select_related("featured_image", "category")

    @extend_schema(tags=["public"], summary="List published posts")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PublicBlogPostDetailAPIView(PublicAPIView, generics.RetrieveAPIView):
    serializer_class = PublicBlogPostDetailSerializer

    def get_queryset(self):
        return BlogPost.objects.live().select_related(
            "featured_image", "og_image", "category", "author"
        )

    @extend_schema(tags=["public"], summary="Retrieve a published post by slug")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PublicBlogCategoryListAPIView(PublicAPIView, generics.ListAPIView):
    serializer_class = PublicBlogCategorySerializer
    pagination_class = None  # a handful of rows; the frontend renders them all

    def get_queryset(self):
        return BlogCategory.objects.all()

    @extend_schema(tags=["public"], summary="List blog categories")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


# ─── FAQs and counters ───────────────────────────────────────────────────────


class PublicFAQListAPIView(PublicAPIView, generics.ListAPIView):
    ordering = ["-created_at", "-id"]
    serializer_class = PublicFAQSerializer
    filterset_fields = ["category"]

    def get_queryset(self):
        return FAQ.objects.live()

    @extend_schema(tags=["public"], summary="List published FAQs")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PublicCounterListAPIView(PublicAPIView, generics.ListAPIView):
    ordering = ["-created_at", "-id"]
    serializer_class = PublicCounterSerializer

    def get_queryset(self):
        return Counter.objects.live()

    @extend_schema(tags=["public"], summary="List published counters")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
