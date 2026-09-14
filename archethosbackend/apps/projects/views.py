from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination

from .models import Project, ProjectCategory, ProjectDetailedStage, ProjectGallery, ProjectPage
from .serializers import ProjectCategorySerializer, ProjectDetailedStageSerializer, ProjectGallerySerializer, ProjectPageSerializer, ProjectSerializer


class ProjectPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


@extend_schema(tags=["Projects"])
class ProjectListCreateAPIView(generics.ListCreateAPIView):
    queryset = Project.objects.select_related("category", "cover_image")
    serializer_class = ProjectSerializer
    pagination_class = ProjectPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["category", "project_type", "status", "is_featured", "slug"]


@extend_schema(tags=["Projects"])
class ProjectDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.select_related("category", "cover_image").prefetch_related("gallery__asset", "detailed_stages__media")
    serializer_class = ProjectSerializer


@extend_schema(tags=["Project categories"])
class ProjectCategoryListCreateAPIView(generics.ListCreateAPIView):
    queryset = ProjectCategory.objects.all()
    serializer_class = ProjectCategorySerializer


@extend_schema(tags=["Project categories"])
class ProjectCategoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProjectCategory.objects.all()
    serializer_class = ProjectCategorySerializer


@extend_schema(tags=["Project gallery"])
class ProjectGalleryListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ProjectGallerySerializer

    def get_queryset(self):
        return ProjectGallery.objects.filter(project_id=self.kwargs["project_id"]).select_related("asset")

    def perform_create(self, serializer):
        serializer.save(project_id=self.kwargs["project_id"])


@extend_schema(tags=["Project gallery"])
class ProjectGalleryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectGallerySerializer

    def get_queryset(self):
        return ProjectGallery.objects.filter(project_id=self.kwargs["project_id"]).select_related("asset")


@extend_schema(tags=["Project stages"])
class ProjectDetailedStageListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ProjectDetailedStageSerializer

    def get_queryset(self):
        return ProjectDetailedStage.objects.filter(project_id=self.kwargs["project_id"]).select_related("media")

    def perform_create(self, serializer):
        serializer.save(project_id=self.kwargs["project_id"])


@extend_schema(tags=["Project stages"])
class ProjectDetailedStageDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectDetailedStageSerializer

    def get_queryset(self):
        return ProjectDetailedStage.objects.filter(project_id=self.kwargs["project_id"]).select_related("media")


@extend_schema(tags=["Projects page"])
class ProjectPageAPIView(generics.RetrieveUpdateAPIView):
    queryset = ProjectPage.objects.select_related("hero_image")
    serializer_class = ProjectPageSerializer

    def get_object(self):
        page, _ = ProjectPage.objects.get_or_create(pk=ProjectPage.SINGLETON_PK)
        return page
