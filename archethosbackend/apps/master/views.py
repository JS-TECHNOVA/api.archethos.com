from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated, SAFE_METHODS

from drf_spectacular.utils import extend_schema

from apps.master.models import FAQ, Gallery, GalleryCategory, GalleryItem
from apps.master.serializers import (
    FAQSerializer, GalleryCategorySerializer, GalleryItemSerializer, GallerySerializer,
)


@extend_schema(tags=["FAQs"])
class FAQListCreateAPIView(generics.ListCreateAPIView):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
    filterset_fields = ["is_active"]


@extend_schema(tags=["FAQs"])
class FAQDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer


class GalleryPagination(PageNumberPagination):
    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 100


@extend_schema(tags=["Gallery"])
class GalleryAPIView(generics.RetrieveUpdateAPIView):
    queryset = Gallery.objects.all()
    serializer_class = GallerySerializer

    def get_permissions(self):
        return [AllowAny()] if self.request.method in SAFE_METHODS else [IsAuthenticated()]

    def get_object(self):
        gallery, _ = Gallery.objects.get_or_create(pk=Gallery.SINGLETON_PK)
        return gallery


@extend_schema(tags=["Gallery categories"])
class GalleryCategoryListCreateAPIView(generics.ListCreateAPIView):
    queryset = GalleryCategory.objects.all()
    serializer_class = GalleryCategorySerializer

    def get_permissions(self):
        return [AllowAny()] if self.request.method in SAFE_METHODS else [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(gallery_id=Gallery.SINGLETON_PK)


@extend_schema(tags=["Gallery categories"])
class GalleryCategoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GalleryCategorySerializer

    def get_queryset(self):
        return GalleryCategory.objects.filter(gallery_id=Gallery.SINGLETON_PK)


@extend_schema(tags=["Gallery items"])
class GalleryItemListCreateAPIView(generics.ListCreateAPIView):
    queryset = GalleryItem.objects.none()
    serializer_class = GalleryItemSerializer
    pagination_class = GalleryPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["category", "is_visible"]

    def get_permissions(self):
        return [AllowAny()] if self.request.method in SAFE_METHODS else [IsAuthenticated()]

    def get_queryset(self):
        queryset = GalleryItem.objects.select_related("category", "asset", "added_by")
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(is_visible=True)
        return queryset

    def perform_create(self, serializer):
        serializer.save(added_by=self.request.user)


@extend_schema(tags=["Gallery items"])
class GalleryItemDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GalleryItemSerializer

    def get_queryset(self):
        return GalleryItem.objects.select_related("category", "asset", "added_by")
