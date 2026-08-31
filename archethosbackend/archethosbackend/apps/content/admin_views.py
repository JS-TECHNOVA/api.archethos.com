"""
Admin CRUD for master content.

Class-based views only (plan §2.8). Publish/unpublish and gallery management are
their own view classes rather than router actions.
"""

import django_filters
from django.db.models import Count, Prefetch
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from archethosbackend.apps.api.generics import (
    AdminListCreateAPIView,
    AdminRetrieveUpdateDestroyAPIView,
    ReorderAPIView,
)
from archethosbackend.apps.api.permissions import HasModelPermission
from archethosbackend.apps.core.models import PublishStatus

from .models import FAQ, BlogCategory, BlogPost, Counter, Project, ProjectGalleryItem, Service
from .serializers import (
    BlogCategoryDetailSerializer,
    BlogCategoryListSerializer,
    BlogCategoryWriteSerializer,
    BlogPostDetailSerializer,
    BlogPostListSerializer,
    BlogPostWriteSerializer,
    CounterDetailSerializer,
    CounterListSerializer,
    CounterWriteSerializer,
    FAQDetailSerializer,
    FAQListSerializer,
    FAQWriteSerializer,
    ProjectDetailSerializer,
    ProjectGalleryItemSerializer,
    ProjectGalleryItemWriteSerializer,
    ProjectListSerializer,
    ProjectWriteSerializer,
    ServiceDetailSerializer,
    ServiceListSerializer,
    ServiceWriteSerializer,
)

COMMON_ORDERING = ["created_at", "updated_at", "title", "status"]

#: Explicit default so pagination is deterministic. Meta.ordering is not
#: enough: annotate(Count(...)) clears it, because Django will not put the
#: ordering column into the GROUP BY.
DEFAULT_ORDERING = ["-created_at", "-id"]


# ─── Services ────────────────────────────────────────────────────────────────


class ServiceListCreateAPIView(AdminListCreateAPIView):
    ordering = ["order", "title", "id"]
    queryset = Service.objects.select_related("featured_image", "icon")
    list_serializer_class = ServiceListSerializer
    write_serializer_class = ServiceWriteSerializer
    filterset_fields = ["status"]
    search_fields = ["title", "short_description", "description"]
    ordering_fields = COMMON_ORDERING + ["order"]

    @extend_schema(tags=["admin:services"], summary="List services")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:services"], summary="Create a service")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ServiceDetailAPIView(AdminRetrieveUpdateDestroyAPIView):
    queryset = Service.objects.select_related("featured_image", "icon", "og_image")
    detail_serializer_class = ServiceDetailSerializer
    write_serializer_class = ServiceWriteSerializer

    @extend_schema(tags=["admin:services"], summary="Retrieve a service")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:services"], summary="Update a service")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(tags=["admin:services"], summary="Delete a service")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# ─── Projects ────────────────────────────────────────────────────────────────


class ProjectFilterSet(django_filters.FilterSet):
    service = django_filters.NumberFilter(field_name="services__id")
    year_from = django_filters.NumberFilter(field_name="project_year", lookup_expr="gte")
    year_to = django_filters.NumberFilter(field_name="project_year", lookup_expr="lte")

    class Meta:
        model = Project
        fields = ["status", "project_status", "is_featured", "project_year", "service"]


class ProjectListCreateAPIView(AdminListCreateAPIView):
    ordering = DEFAULT_ORDERING
    queryset = (
        Project.objects.select_related("featured_image")
        .annotate(gallery_count=Count("gallery_items", distinct=True))
    )
    list_serializer_class = ProjectListSerializer
    write_serializer_class = ProjectWriteSerializer
    filterset_class = ProjectFilterSet
    search_fields = ["title", "short_description", "description", "location"]
    ordering_fields = COMMON_ORDERING + ["project_year", "is_featured"]

    @extend_schema(tags=["admin:projects"], summary="List projects")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:projects"], summary="Create a project")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ProjectDetailAPIView(AdminRetrieveUpdateDestroyAPIView):
    queryset = Project.objects.select_related("featured_image", "og_image").prefetch_related(
        "services",
        Prefetch(
            "gallery_items",
            queryset=ProjectGalleryItem.objects.select_related("media"),
        ),
    )
    detail_serializer_class = ProjectDetailSerializer
    write_serializer_class = ProjectWriteSerializer

    @extend_schema(tags=["admin:projects"], summary="Retrieve a project")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:projects"], summary="Update a project")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(tags=["admin:projects"], summary="Delete a project")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# ─── Project gallery ─────────────────────────────────────────────────────────


class ProjectGalleryMixin:
    """Permissions derive from the parent Project, not the item model.

    "May edit this project" is the real mental model; a separate
    add/change/delete triple for gallery items would clutter the group picker
    without expressing anything a user would think to grant.
    """

    permission_classes = [IsAuthenticated, HasModelPermission]

    #: Lets drf-spectacular introspect the model without a real URL kwarg.
    queryset = ProjectGalleryItem.objects.none()

    def get_project(self):
        return get_object_or_404(Project, pk=self.kwargs["pk"])


class ProjectGalleryListCreateAPIView(ProjectGalleryMixin, AdminListCreateAPIView):
    ordering = ["order", "id"]
    required_permissions = ["content.change_project"]
    list_serializer_class = ProjectGalleryItemSerializer
    write_serializer_class = ProjectGalleryItemWriteSerializer
    pagination_class = None  # a project's gallery is small and always shown whole

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ProjectGalleryItem.objects.none()
        return ProjectGalleryItem.objects.filter(
            project=self.get_project()
        ).select_related("media")

    def get_serializer_context(self):
        if getattr(self, "swagger_fake_view", False):
            return super().get_serializer_context()
        return {**super().get_serializer_context(), "project": self.get_project()}

    @extend_schema(tags=["admin:projects"], summary="List gallery images")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:projects"], summary="Add an image to the gallery")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ProjectGalleryItemAPIView(ProjectGalleryMixin, AdminRetrieveUpdateDestroyAPIView):
    required_permissions = ["content.change_project"]
    detail_serializer_class = ProjectGalleryItemSerializer
    write_serializer_class = ProjectGalleryItemWriteSerializer
    lookup_url_kwarg = "item_id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ProjectGalleryItem.objects.none()
        return ProjectGalleryItem.objects.filter(
            project=self.get_project()
        ).select_related("media")

    def get_serializer_context(self):
        if getattr(self, "swagger_fake_view", False):
            return super().get_serializer_context()
        return {**super().get_serializer_context(), "project": self.get_project()}

    @extend_schema(tags=["admin:projects"], summary="Update a gallery image")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(tags=["admin:projects"], summary="Remove an image from the gallery")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class ProjectGalleryReorderAPIView(ReorderAPIView):
    item_model = ProjectGalleryItem
    parent_model = Project
    parent_field = "project"
    required_permissions = ["content.change_project"]

    @extend_schema(
        tags=["admin:projects"],
        summary="Reorder gallery images",
        request=None,
        responses={200: None},
        description='Atomic. Body: {"items": [{"id": 10, "order": 1}, ...]}',
    )
    def patch(self, request, pk):
        return super().patch(request, pk)


# ─── Blog ────────────────────────────────────────────────────────────────────


class BlogCategoryListCreateAPIView(AdminListCreateAPIView):
    ordering = ["name", "id"]
    queryset = BlogCategory.objects.annotate(posts_count=Count("posts", distinct=True))
    list_serializer_class = BlogCategoryListSerializer
    write_serializer_class = BlogCategoryWriteSerializer
    search_fields = ["name"]
    ordering_fields = ["name", "created_at", "posts_count"]

    @extend_schema(tags=["admin:blogs"], summary="List blog categories")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:blogs"], summary="Create a blog category")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class BlogCategoryDetailAPIView(AdminRetrieveUpdateDestroyAPIView):
    queryset = BlogCategory.objects.all()
    detail_serializer_class = BlogCategoryDetailSerializer
    write_serializer_class = BlogCategoryWriteSerializer

    @extend_schema(tags=["admin:blogs"], summary="Retrieve a blog category")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:blogs"], summary="Update a blog category")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(tags=["admin:blogs"], summary="Delete a blog category")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class BlogPostFilterSet(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name="category__id")
    author = django_filters.NumberFilter(field_name="author__id")

    class Meta:
        model = BlogPost
        fields = ["status", "category", "author"]


class BlogPostListCreateAPIView(AdminListCreateAPIView):
    ordering = DEFAULT_ORDERING
    queryset = BlogPost.objects.select_related("featured_image", "category", "author")
    list_serializer_class = BlogPostListSerializer
    write_serializer_class = BlogPostWriteSerializer
    filterset_class = BlogPostFilterSet
    search_fields = ["title", "excerpt", "content"]
    ordering_fields = COMMON_ORDERING + ["published_at", "reading_time"]

    @extend_schema(tags=["admin:blogs"], summary="List blog posts")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:blogs"], summary="Create a blog post")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class BlogPostDetailAPIView(AdminRetrieveUpdateDestroyAPIView):
    queryset = BlogPost.objects.select_related(
        "featured_image", "og_image", "category", "author"
    )
    detail_serializer_class = BlogPostDetailSerializer
    write_serializer_class = BlogPostWriteSerializer

    @extend_schema(tags=["admin:blogs"], summary="Retrieve a blog post")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:blogs"], summary="Update a blog post")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(tags=["admin:blogs"], summary="Delete a blog post")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


class _PublishToggleAPIView(APIView):
    """Shared body for publish and unpublish.

    A dedicated endpoint rather than PATCHing `status`, because publishing is a
    distinct action with its own permission story and its own audit entry
    (Phase 12), not just another field edit.
    """

    permission_classes = [IsAuthenticated, HasModelPermission]
    model = None
    target_status = None
    detail_serializer = None

    def post(self, request, pk):
        obj = get_object_or_404(self.model, pk=pk)
        obj.status = self.target_status

        if self.target_status == PublishStatus.PUBLISHED and obj.published_at is None:
            obj.published_at = timezone.now()

        obj.save()
        return Response(self.detail_serializer(obj).data, status=status.HTTP_200_OK)


class BlogPostPublishAPIView(_PublishToggleAPIView):
    model = BlogPost
    target_status = PublishStatus.PUBLISHED
    detail_serializer = BlogPostDetailSerializer
    required_permissions = ["content.change_blogpost"]
    envelope_message = "Blog post published"

    @extend_schema(
        tags=["admin:blogs"], summary="Publish a blog post",
        request=None, responses={200: BlogPostDetailSerializer},
    )
    def post(self, request, pk):
        return super().post(request, pk)


class BlogPostUnpublishAPIView(_PublishToggleAPIView):
    model = BlogPost
    target_status = PublishStatus.DRAFT
    detail_serializer = BlogPostDetailSerializer
    required_permissions = ["content.change_blogpost"]
    envelope_message = "Blog post unpublished"

    @extend_schema(
        tags=["admin:blogs"], summary="Unpublish a blog post",
        request=None, responses={200: BlogPostDetailSerializer},
    )
    def post(self, request, pk):
        return super().post(request, pk)


# ─── FAQs ────────────────────────────────────────────────────────────────────


class FAQListCreateAPIView(AdminListCreateAPIView):
    ordering = DEFAULT_ORDERING
    queryset = FAQ.objects.all()
    list_serializer_class = FAQListSerializer
    write_serializer_class = FAQWriteSerializer
    filterset_fields = ["status", "category"]
    search_fields = ["question", "answer"]
    ordering_fields = ["created_at", "updated_at", "status", "category"]

    @extend_schema(tags=["admin:faqs"], summary="List FAQs")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:faqs"], summary="Create an FAQ")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class FAQDetailAPIView(AdminRetrieveUpdateDestroyAPIView):
    queryset = FAQ.objects.all()
    detail_serializer_class = FAQDetailSerializer
    write_serializer_class = FAQWriteSerializer

    @extend_schema(tags=["admin:faqs"], summary="Retrieve an FAQ")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:faqs"], summary="Update an FAQ")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(tags=["admin:faqs"], summary="Delete an FAQ")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# ─── Counters ────────────────────────────────────────────────────────────────


class CounterListCreateAPIView(AdminListCreateAPIView):
    ordering = DEFAULT_ORDERING
    queryset = Counter.objects.all()
    list_serializer_class = CounterListSerializer
    write_serializer_class = CounterWriteSerializer
    filterset_fields = ["status"]
    search_fields = ["subtitle", "description", "content"]
    ordering_fields = ["created_at", "updated_at", "subtitle", "status"]

    @extend_schema(tags=["admin:counters"], summary="List counters")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:counters"], summary="Create a counter")
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CounterDetailAPIView(AdminRetrieveUpdateDestroyAPIView):
    queryset = Counter.objects.all()
    detail_serializer_class = CounterDetailSerializer
    write_serializer_class = CounterWriteSerializer

    @extend_schema(tags=["admin:counters"], summary="Retrieve a counter")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=["admin:counters"], summary="Update a counter")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(tags=["admin:counters"], summary="Delete a counter")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
