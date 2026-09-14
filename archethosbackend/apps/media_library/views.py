from django.db.models import Q
from django_filters import rest_framework as django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser

from .models import MediaAsset
from .serializers import MediaAssetSerializer


class MediaPagination(PageNumberPagination):
    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 100


class MediaAssetFilter(django_filters.FilterSet):
    media_type = django_filters.CharFilter(method="filter_media_type")
    source_type = django_filters.CharFilter(method="filter_source_type")
    tags = django_filters.CharFilter(method="filter_tags")

    class Meta:
        model = MediaAsset
        fields = ["uploaded_by"]

    def filter_media_type(self, queryset, name, value):
        media_types = [media_type.strip().lower().rstrip("s") for media_type in value.split(",") if media_type.strip()]
        return queryset.filter(media_type__in=media_types)

    def filter_source_type(self, queryset, name, value):
        source_types = [source_type.strip().upper() for source_type in value.split(",") if source_type.strip()]
        return queryset.filter(source_type__in=source_types)

    def filter_tags(self, queryset, name, value):
        tags = [tag.strip() for tag in value.split(",") if tag.strip()]
        condition = Q()
        for tag in tags:
            condition |= Q(tags__contains=[tag])
        return queryset.filter(condition) if tags else queryset


class MediaListCreateAPIView(generics.ListCreateAPIView):
    queryset = MediaAsset.objects.select_related("uploaded_by")
    serializer_class = MediaAssetSerializer
    permission_classes = [IsAdminUser]
    pagination_class = MediaPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = MediaAssetFilter
    search_fields = ["title", "alt_text", "caption", "description", "tags", "file_name"]
    ordering_fields = [("created_at", "created"), "title", "media_type", "source_type"]

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class MediaDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MediaAsset.objects.select_related("uploaded_by")
    serializer_class = MediaAssetSerializer
    permission_classes = [IsAdminUser]
